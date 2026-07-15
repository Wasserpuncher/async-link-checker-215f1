import unittest
import collections
import asyncio
import json
import os
import tempfile
from unittest.mock import MagicMock, patch
import httpx
from main import LinkChecker, load_config, resolve_settings, DEFAULT_SETTINGS

class TestLinkChecker(unittest.IsolatedAsyncioTestCase):
    """
    Unit-Tests für die LinkChecker-Klasse.

    Diese Tests verwenden `unittest.mock` und `unittest.IsolatedAsyncioTestCase`,
    um asynchrone Methoden zu testen und HTTP-Anfragen zu simulieren.
    """

    def setUp(self):
        """
        Einrichtungsmethode, die vor jedem Testfall ausgeführt wird.
        Initialisiert einen LinkChecker mit einer Basis-URL.
        """
        self.base_url = "http://test.com"
        self.checker = LinkChecker(self.base_url, max_depth=1, concurrency_limit=5, timeout=1)
        # Setzt visited_urls und queue zurück, um Isolation zwischen Tests zu gewährleisten
        self.checker.visited_urls = set()
        self.checker.queue = collections.deque([(self.base_url, 0)])

    @patch('httpx.AsyncClient.get')
    async def test_fetch_url_success(self, mock_get):
        """
        Testet den erfolgreichen Abruf einer URL.
        Simuliert eine erfolgreiche HTTP-Antwort (Status 200).
        """
        # Das Response-Objekt ist synchron (nur der Netzaufrufe client.get ist async),
        # daher MagicMock mit echten Attributwerten.
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = "<html><body>Hello</body></html>"
        mock_response.raise_for_status.return_value = None
        # Der Code ruft `response = await self.client.get(...)` direkt auf (kein async with),
        # also liefert der awaited Aufruf direkt das Response-Objekt.
        mock_get.return_value = mock_response

        status, content = await self.checker._fetch_url("http://test.com/page1")
        self.assertEqual(status, 200)
        self.assertEqual(content, "<html><body>Hello</body></html>")
        mock_get.assert_called_once_with("http://test.com/page1", follow_redirects=True, timeout=1)

    @patch('httpx.AsyncClient.get')
    async def test_fetch_url_http_error(self, mock_get):
        """
        Testet den Abruf einer URL, die einen HTTP-Fehler zurückgibt (z.B. 404).
        Simuliert eine HTTPStatusError-Ausnahme.
        """
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=httpx.Request("GET", "http://test.com/404"), response=mock_response
        )
        mock_get.return_value = mock_response

        status, content = await self.checker._fetch_url("http://test.com/404")
        self.assertEqual(status, 404)
        self.assertIsNone(content)

    @patch('httpx.AsyncClient.get')
    async def test_fetch_url_request_error(self, mock_get):
        """
        Testet den Abruf einer URL, die einen allgemeinen Anfragenfehler verursacht (z.B. Netzwerkproblem).
        Simuliert eine RequestError-Ausnahme.
        """
        # Der awaited client.get-Aufruf selbst wirft den RequestError.
        mock_get.side_effect = httpx.RequestError(
            "Connection error", request=httpx.Request("GET", "http://bad.com")
        )

        status, content = await self.checker._fetch_url("http://bad.com")
        self.assertIsNone(status)
        self.assertIsNone(content)

    def test_parse_links(self):
        """
        Testet das Parsen von Links aus HTML-Inhalt.
        Überprüft, ob sowohl absolute als auch relative Links korrekt extrahiert und aufgelöst werden.
        """
        html_content = """
        <html>
            <body>
                <a href="/internal/page1">Internal Link 1</a>
                <a href="https://external.com/page2">External Link</a>
                <a href="page3.html">Relative Link</a>
                <a href="#anchor">Anchor Link</a>
                <a href="mailto:test@example.com">Mail Link</a>
            </body>
        </html>
        """
        links = self.checker._parse_links(html_content, "http://test.com")
        expected_links = [
            "http://test.com/internal/page1",
            "https://external.com/page2",
            "http://test.com/page3.html"
        ]
        self.assertCountEqual(links, expected_links) # Vergleicht die Listen ohne Berücksichtigung der Reihenfolge

    def test_is_same_domain(self):
        """
        Testet die Logik zur Überprüfung der Domain-Zugehörigkeit.
        """
        self.assertTrue(self.checker._is_same_domain("http://test.com/path"))
        self.assertTrue(self.checker._is_same_domain("https://test.com/path"))
        self.assertFalse(self.checker._is_same_domain("http://other.com"))
        self.assertFalse(self.checker._is_same_domain("ftp://test.com")) # Nicht-HTTP-Schema sollte False ergeben

    def test_normalize_url(self):
        """
        Testet die URL-Normalisierungsfunktion.
        Stellt sicher, dass URL-Fragmente entfernt werden.
        """
        self.assertEqual(self.checker._normalize_url("http://test.com/path#anchor"), "http://test.com/path")
        self.assertEqual(self.checker._normalize_url("http://test.com/path"), "http://test.com/path")

    @patch('httpx.AsyncClient.get')
    async def test_process_url_internal_link_adds_to_queue(self, mock_get):
        """
        Testet die Verarbeitung einer URL, die einen internen Link enthält.
        Stellt sicher, dass der interne Link zur Warteschlange hinzugefügt wird.
        """
        html_content = "<html><body><a href=\"/new-page\"></a></body></html>"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html_content
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        # Leert die Warteschlange und visited_urls, um den Test zu isolieren
        self.checker.queue.clear()
        self.checker.visited_urls.clear()
        self.checker.queue.append(("http://test.com", 0))

        await self.checker._process_url("http://test.com", 0)

        self.assertIn("http://test.com", self.checker.visited_urls)
        self.assertIn("http://test.com/new-page", self.checker.internal_links)
        self.assertIn(("http://test.com/new-page", 1), self.checker.queue)
        self.assertFalse(self.checker.broken_links)

    @patch('httpx.AsyncClient.get')
    async def test_process_url_broken_link(self, mock_get):
        """
        Testet die Verarbeitung einer URL, die defekt ist.
        Stellt sicher, dass der Link zu den defekten Links hinzugefügt wird.
        """
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=httpx.Request("GET", "http://test.com/broken"), response=mock_response
        )
        mock_get.return_value = mock_response

        self.checker.queue.clear()
        self.checker.visited_urls.clear()

        await self.checker._process_url("http://test.com/broken", 0)

        self.assertIn("http://test.com/broken", self.checker.visited_urls)
        self.assertIn("http://test.com/broken", self.checker.broken_links)
        self.assertEqual(self.checker.broken_links["http://test.com/broken"], 404)
        self.assertFalse(self.checker.queue)

    @patch('httpx.AsyncClient.get')
    async def test_run_basic_crawl(self, mock_get):
        """
        Testet einen grundlegenden Crawl-Durchlauf.
        Simuliert mehrere Seiten und Links, um den End-to-End-Fluss zu überprüfen.
        """
        # Mock-Antworten für die URLs
        def get_mock_response(url):
            mock_resp = MagicMock()
            mock_resp.raise_for_status.return_value = None
            if url == "http://test.com":
                mock_resp.status_code = 200
                mock_resp.text = '<html><body><a href="/page1">Page1</a><a href="http://external.com">External</a></body></html>'
            elif url == "http://test.com/page1":
                mock_resp.status_code = 200
                mock_resp.text = '<html><body><a href="/page2">Page2</a></body></html>'
            elif url == "http://test.com/page2":
                mock_resp.status_code = 200
                mock_resp.text = '<html><body>End</body></html>'
            elif url == "http://external.com":
                mock_resp.status_code = 200
                mock_resp.text = '<html><body>External Content</body></html>'
            elif url == "http://test.com/broken":
                mock_resp.status_code = 404
                mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                    "Not Found", request=httpx.Request("GET", url), response=mock_resp
                )
            else:
                mock_resp.status_code = 500
                mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                    "Server Error", request=httpx.Request("GET", url), response=mock_resp
                )
            return mock_resp

        # client.get(url, ...) wird direkt awaited; die URL kommt als erstes Positionsargument.
        mock_get.side_effect = lambda url, *args, **kwargs: get_mock_response(url)

        # Setzt max_depth auf 2, damit /page2 gecrawlt wird
        self.checker.max_depth = 2
        # Setzt die Start-URL zurück, um einen sauberen Crawl zu gewährleisten
        self.checker.queue = collections.deque([(self.base_url, 0)])
        self.checker.visited_urls.clear()
        self.checker.broken_links.clear()
        self.checker.internal_links.clear()
        self.checker.external_links.clear()

        await self.checker.run()

        results = self.checker.get_results()

        self.assertIn("http://test.com", self.checker.visited_urls)
        self.assertIn("http://test.com/page1", self.checker.visited_urls)
        self.assertIn("http://test.com/page2", self.checker.visited_urls)
        self.assertIn("http://external.com", self.checker.visited_urls)

        self.assertIn("http://test.com/page1", results["internal_links"])
        self.assertIn("http://test.com/page2", results["internal_links"])
        self.assertIn("http://external.com", results["external_links"])
        self.assertFalse(results["broken_links"])


    @patch('httpx.AsyncClient.get')
    async def test_run_with_broken_link(self, mock_get):
        """
        Testet einen Crawl-Durchlauf, der einen defekten Link entdeckt.
        """
        # Mock-Antworten für die URLs
        def get_mock_response(url):
            mock_resp = MagicMock()
            mock_resp.raise_for_status.return_value = None
            if url == "http://test.com":
                mock_resp.status_code = 200
                mock_resp.text = '<html><body><a href="/broken">Broken</a></body></html>'
            elif url == "http://test.com/broken":
                mock_resp.status_code = 404
                mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
                    "Not Found", request=httpx.Request("GET", url), response=mock_resp
                )
            else:
                mock_resp.status_code = 200
                mock_resp.text = '<html><body>Other</body></html>'
            return mock_resp

        # client.get(url, ...) wird direkt awaited; die URL kommt als erstes Positionsargument.
        mock_get.side_effect = lambda url, *args, **kwargs: get_mock_response(url)

        self.checker.max_depth = 1
        self.checker.queue = collections.deque([(self.base_url, 0)])
        self.checker.visited_urls.clear()
        self.checker.broken_links.clear()
        self.checker.internal_links.clear()
        self.checker.external_links.clear()

        await self.checker.run()

        results = self.checker.get_results()

        self.assertIn("http://test.com", self.checker.visited_urls)
        self.assertIn("http://test.com/broken", self.checker.visited_urls)
        self.assertIn("http://test.com/broken", results["broken_links"])
        self.assertEqual(results["broken_links"]["http://test.com/broken"], 404)
        self.assertIn("http://test.com/broken", results["internal_links"])
        self.assertFalse(results["external_links"])


class TestConfigFile(unittest.TestCase):
    """
    Tests für das Laden und Anwenden der JSON-Konfigurationsdatei.
    """

    def _write_config(self, data):
        """Schreibt ein dict als JSON in eine temporäre Datei und gibt den Pfad zurück."""
        fd, path = tempfile.mkstemp(suffix=".json")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(data, f)
        self.addCleanup(os.remove, path)
        return path

    def test_load_config_reads_known_keys(self):
        """load_config liest bekannte Schlüssel und filtert unbekannte heraus."""
        path = self._write_config({
            "base_url": "http://example.com",
            "max_depth": 4,
            "concurrency": 3,
            "timeout": 7,
            "ignore_patterns": ["*/logout"],
            "unknown_key": "should be dropped",
        })
        config = load_config(path)
        self.assertEqual(config["base_url"], "http://example.com")
        self.assertEqual(config["max_depth"], 4)
        self.assertEqual(config["concurrency"], 3)
        self.assertEqual(config["timeout"], 7)
        self.assertEqual(config["ignore_patterns"], ["*/logout"])
        self.assertNotIn("unknown_key", config)

    def test_load_config_rejects_non_object(self):
        """load_config lehnt JSON ab, das kein Objekt ist."""
        path = self._write_config([1, 2, 3])
        with self.assertRaises(ValueError):
            load_config(path)

    def test_load_config_missing_file(self):
        """load_config wirft FileNotFoundError für eine nicht existierende Datei."""
        with self.assertRaises(FileNotFoundError):
            load_config("/nonexistent/path/linkcheck.json")

    def test_resolve_settings_defaults_only(self):
        """Ohne Config und CLI bleiben die eingebauten Defaults erhalten."""
        settings = resolve_settings({}, {})
        self.assertEqual(settings, DEFAULT_SETTINGS)

    def test_resolve_settings_config_over_defaults(self):
        """Die Konfigurationsdatei überschreibt die eingebauten Defaults."""
        settings = resolve_settings({}, {"max_depth": 9, "timeout": 42})
        self.assertEqual(settings["max_depth"], 9)
        self.assertEqual(settings["timeout"], 42)
        self.assertEqual(settings["concurrency"], DEFAULT_SETTINGS["concurrency"])

    def test_resolve_settings_cli_over_config(self):
        """Explizite CLI-Werte haben Vorrang vor der Konfigurationsdatei."""
        cli = {"max_depth": 1, "timeout": None, "base_url": "http://cli.example"}
        config = {"max_depth": 9, "timeout": 42, "base_url": "http://config.example"}
        settings = resolve_settings(cli, config)
        # CLI setzt max_depth und base_url; timeout ist None (nicht gesetzt) -> Config greift.
        self.assertEqual(settings["max_depth"], 1)
        self.assertEqual(settings["base_url"], "http://cli.example")
        self.assertEqual(settings["timeout"], 42)

    def test_config_applied_to_checker(self):
        """Ein aus Config-Werten gebauter LinkChecker übernimmt diese Werte."""
        config = load_config(self._write_config({
            "base_url": "http://example.com",
            "max_depth": 5,
            "concurrency": 2,
            "timeout": 3,
            "ignore_patterns": ["*/admin/*"],
        }))
        settings = resolve_settings({}, config)
        checker = LinkChecker(
            base_url=settings["base_url"],
            max_depth=settings["max_depth"],
            concurrency_limit=settings["concurrency"],
            timeout=settings["timeout"],
            ignore_patterns=settings["ignore_patterns"],
        )
        self.assertEqual(checker.max_depth, 5)
        self.assertEqual(checker.concurrency_limit, 2)
        self.assertEqual(checker.timeout, 3)
        self.assertEqual(checker.ignore_patterns, ["*/admin/*"])

    def test_is_ignored_glob_and_substring(self):
        """_is_ignored trifft sowohl bei Glob-Mustern als auch bei Teilzeichenketten."""
        checker = LinkChecker("http://test.com", ignore_patterns=["*/private/*", "logout"])
        self.assertTrue(checker._is_ignored("http://test.com/private/secret"))
        self.assertTrue(checker._is_ignored("http://test.com/user/logout"))
        self.assertFalse(checker._is_ignored("http://test.com/public/page"))

    def test_default_no_ignore_patterns(self):
        """Ohne ignore_patterns wird nichts ignoriert (Rückwärtskompatibilität)."""
        checker = LinkChecker("http://test.com")
        self.assertEqual(checker.ignore_patterns, [])
        self.assertFalse(checker._is_ignored("http://test.com/anything"))


class TestIgnorePatternsBehavior(unittest.IsolatedAsyncioTestCase):
    """
    Verhaltenstest: Ignorier-Muster aus der Config verhindern das Crawlen/Erfassen
    passender Links tatsächlich.
    """

    @patch('httpx.AsyncClient.get')
    async def test_ignored_links_are_skipped(self, mock_get):
        """Links, die auf ein Ignorier-Muster passen, landen weder in der Warteschlange
        noch in den Ergebnismengen; nicht passende Links schon."""
        html = (
            '<html><body>'
            '<a href="/admin/dashboard">Admin</a>'
            '<a href="/about">About</a>'
            '</body></html>'
        )
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.text = html
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response

        checker = LinkChecker(
            "http://test.com", max_depth=2, concurrency_limit=5, timeout=1,
            ignore_patterns=["*/admin/*"]
        )
        checker.queue.clear()
        checker.visited_urls.clear()

        await checker._process_url("http://test.com", 0)

        # Der ignorierte Admin-Link darf nirgends auftauchen.
        self.assertNotIn("http://test.com/admin/dashboard", checker.internal_links)
        self.assertNotIn(
            ("http://test.com/admin/dashboard", 1),
            checker.queue
        )
        # Der reguläre Link muss weiterhin erfasst werden.
        self.assertIn("http://test.com/about", checker.internal_links)
        self.assertIn(("http://test.com/about", 1), checker.queue)


if __name__ == '__main__':
    unittest.main()

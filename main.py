import asyncio
import httpx
import argparse
from bs4 import BeautifulSoup
from urllib.parse import urlparse, urljoin, urldefrag
import collections
import logging
import sys

# Konfiguration des Loggers
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class LinkChecker:
    """
    Ein asynchroner Web-Crawler zur Erkennung defekter Links.

    Dieser Crawler durchsucht eine gegebene Start-URL rekursiv bis zu einer
    bestimmten Tiefe, um alle internen und externen Links zu finden und zu überprüfen.
    Er verwendet `asyncio` und `httpx` für effiziente, parallele HTTP-Anfragen.
    """

    def __init__(
        self, 
        base_url: str, 
        max_depth: int = 2,
        concurrency_limit: int = 10,
        timeout: int = 10
    ):
        """
        Initialisiert den LinkChecker.

        Args:
            base_url (str): Die Start-URL für den Crawl.
            max_depth (int): Die maximale Tiefe, bis zu der gecrawlt werden soll.
            concurrency_limit (int): Die maximale Anzahl gleichzeitiger HTTP-Anfragen.
            timeout (int): Das Timeout in Sekunden für HTTP-Anfragen.
        """
        self.base_url = self._normalize_url(base_url) # Normalisiert die Basis-URL für konsistente Vergleiche
        self.base_domain = urlparse(self.base_url).netloc # Extrahiert die Domain der Basis-URL
        self.max_depth = max_depth # Setzt die maximale Crawling-Tiefe
        self.concurrency_limit = concurrency_limit # Setzt das Limit für gleichzeitige Anfragen
        self.timeout = timeout # Setzt das Timeout für HTTP-Anfragen

        self.visited_urls = set() # Set zur Speicherung bereits besuchter URLs, um Redundanz zu vermeiden
        self.broken_links = {} # Dictionary zur Speicherung defekter Links und ihrer Statuscodes
        self.internal_links = set() # Set zur Speicherung gültiger interner Links
        self.external_links = set() # Set zur Speicherung gültiger externer Links
        self.queue = collections.deque([(self.base_url, 0)]) # Warteschlange für URLs, die noch gecrawlt werden müssen, zusammen mit ihrer Tiefe

        self.semaphore = asyncio.Semaphore(self.concurrency_limit) # Semaphor zur Begrenzung der Parallelität von HTTP-Anfragen
        self.client = httpx.AsyncClient(follow_redirects=True, timeout=self.timeout) # Asynchroner HTTP-Client mit Weiterleitungsfunktion und Timeout

    def _normalize_url(self, url: str) -> str:
        """
        Normalisiert eine URL, indem der Fragment-Teil entfernt wird.

        Args:
            url (str): Die zu normalisierende URL.

        Returns:
            str: Die normalisierte URL ohne Fragment.
        """
        return urldefrag(url).url # Entfernt den Fragment-Teil (#anchor) einer URL

    def _is_same_domain(self, url: str) -> bool:
        """
        Prüft, ob eine gegebene URL zur gleichen Domain wie die Basis-URL gehört.

        Args:
            url (str): Die zu prüfende URL.

        Returns:
            bool: True, wenn die URL zur gleichen Domain gehört, sonst False.
        """
        try:
            parsed_url = urlparse(url) # Parsen der URL, um Domain-Informationen zu erhalten
            return parsed_url.netloc == self.base_domain # Vergleicht die Domain der URL mit der Basis-Domain
        except ValueError:
            return False # Gibt False zurück, wenn die URL ungültig ist und nicht geparst werden kann

    async def _fetch_url(self, url: str) -> tuple[int | None, str | None]:
        """
        Führt eine asynchrone HTTP GET-Anfrage an die gegebene URL aus.

        Args:
            url (str): Die URL, die abgerufen werden soll.

        Returns:
            tuple[int | None, str | None]: Ein Tupel aus Statuscode und Inhalt, oder (None, None) bei Fehler.
        """
        async with self.semaphore: # Erwirbt einen Semaphor-Slot, um die Parallelität zu kontrollieren
            try:
                logger.debug(f"Fetching {url}") # Debug-Meldung für den Abruf einer URL
                response = await self.client.get(url, follow_redirects=True, timeout=self.timeout) # Führt die GET-Anfrage aus
                response.raise_for_status() # Löst eine Ausnahme für HTTP-Fehlerstatus (4xx oder 5xx) aus
                logger.info(f"Successfully fetched {url} with status {response.status_code}") # Erfolgsmeldung mit Statuscode
                return response.status_code, response.text # Gibt den Statuscode und den Inhalt zurück
            except httpx.HTTPStatusError as e:
                logger.warning(f"HTTP error fetching {url}: {e.response.status_code}") # Warnung bei HTTP-Statusfehler
                return e.response.status_code, None # Gibt den Fehlerstatuscode zurück
            except httpx.RequestError as e:
                logger.error(f"Request error fetching {url}: {e}") # Fehlermeldung bei anderen Anfragenfehlern (z.B. Netzwerk)
                return None, None # Gibt None zurück, wenn kein Statuscode verfügbar ist
            except Exception as e:
                logger.error(f"Unexpected error fetching {url}: {e}") # Fehlermeldung bei unerwarteten Fehlern
                return None, None

    def _parse_links(self, html_content: str, current_url: str) -> list[str]:
        """
        Parsen des HTML-Inhalts, um alle `href`-Attribute aus `<a>`-Tags zu extrahieren.

        Args:
            html_content (str): Der HTML-Inhalt zum Parsen.
            current_url (str): Die URL der Seite, von der der Inhalt stammt, für die Link-Auflösung.

        Returns:
            list[str]: Eine Liste von absoluten URLs, die im HTML gefunden wurden.
        """
        soup = BeautifulSoup(html_content, 'lxml') # Erstellt ein BeautifulSoup-Objekt zum Parsen von HTML mit 'lxml'
        found_links = [] # Liste zur Speicherung der gefundenen Links
        for a_tag in soup.find_all('a', href=True): # Findet alle 'a'-Tags mit einem 'href'-Attribut
            href = a_tag['href'] # Extrahiert den Wert des 'href'-Attributs
            resolved_url = urljoin(current_url, href) # Löst relative URLs in absolute URLs auf
            normalized_url = self._normalize_url(resolved_url) # Normalisiert die aufgelöste URL
            
            # Filtert unerwünschte Schemata wie mailto:, javascript: usw.
            if normalized_url.startswith(('http://', 'https://')):
                found_links.append(normalized_url) # Fügt die gültige HTTP/HTTPS-URL zur Liste hinzu
            else:
                logger.debug(f"Ignoring non-http/https link: {normalized_url}") # Debug-Meldung für ignorierte Links
        return found_links # Gibt die Liste der gefundenen Links zurück

    async def _process_url(self, url: str, depth: int):
        """
        Verarbeitet eine einzelne URL: Holt sie ab, parst Links und fügt neue Links zur Warteschlange hinzu.

        Args:
            url (str): Die zu verarbeitende URL.
            depth (int): Die aktuelle Crawling-Tiefe dieser URL.
        """
        if url in self.visited_urls: # Prüft, ob die URL bereits besucht wurde
            logger.debug(f"Skipping already visited URL: {url}") # Debug-Meldung für übersprungene URL
            return

        self.visited_urls.add(url) # Fügt die URL zu den besuchten URLs hinzu

        status_code, html_content = await self._fetch_url(url) # Holt den Inhalt der URL ab

        if status_code is None or status_code >= 400: # Prüft auf Fehler oder defekte Links (Statuscode 400 oder höher)
            self.broken_links[url] = status_code if status_code else "Unknown Error" # Speichert den defekten Link und seinen Status
            logger.warning(f"Detected broken link: {url} (Status: {status_code})") # Warnung für defekten Link
            return

        if html_content and depth < self.max_depth: # Verarbeitet den Inhalt nur, wenn vorhanden und die maximale Tiefe nicht erreicht ist
            links = self._parse_links(html_content, url) # Parsen der Links im HTML-Inhalt
            for link in links:
                if link not in self.visited_urls: # Fügt nur neue, unbesuchte Links zur Warteschlange hinzu
                    if self._is_same_domain(link): # Prüft, ob der Link zur gleichen Domain gehört
                        self.internal_links.add(link) # Fügt den Link zu den internen Links hinzu
                        self.queue.append((link, depth + 1)) # Fügt den internen Link zur Warteschlange für weiteres Crawling hinzu
                    else:
                        self.external_links.add(link) # Fügt den Link zu den externen Links hinzu

    async def run(self):
        """
        Startet den asynchronen Web-Crawl-Prozess.

        Dieser Methode koordiniert das Abrufen und Verarbeiten von URLs aus der Warteschlange,
        wobei die Parallelität durch ein Semaphor gesteuert wird.
        """
        logger.info(f"Starting crawl from {self.base_url} with max depth {self.max_depth} and concurrency {self.concurrency_limit}") # Startmeldung des Crawlers
        tasks = set() # Set zur Speicherung laufender Tasks

        while self.queue or tasks: # Solange noch URLs in der Warteschlange sind oder Tasks laufen
            while self.queue and len(tasks) < self.concurrency_limit: # Fügt neue Tasks hinzu, solange die Warteschlange nicht leer ist und das Parallelitätslimit nicht erreicht ist
                url, depth = self.queue.popleft() # Holt die nächste URL und Tiefe aus der Warteschlange
                if url not in self.visited_urls: # Prüft, ob die URL bereits besucht wurde (doppelte Prüfung, da async)
                    task = asyncio.create_task(self._process_url(url, depth)) # Erstellt einen neuen Task für die URL-Verarbeitung
                    tasks.add(task) # Fügt den Task zum Set der laufenden Tasks hinzu
                    task.add_done_callback(tasks.discard) # Entfernt den Task automatisch, wenn er beendet ist

            if not tasks and self.queue: # Wenn keine Tasks laufen, aber noch URLs in der Warteschlange sind (z.B. nach einer Pause)
                continue # Weiter zum nächsten Schleifendurchlauf

            if tasks: # Wenn Tasks laufen
                # Wartet auf den Abschluss des nächsten Tasks, um die Schleife nicht zu blockieren
                # und um neue Tasks hinzuzufügen, sobald ein Slot frei wird.
                done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED) # Wartet, bis der erste Task abgeschlossen ist
                for task in done:
                    try:
                        await task # Holt das Ergebnis des abgeschlossenen Tasks ab (oder fängt Ausnahmen)
                    except Exception as e:
                        logger.error(f"Task failed: {e}") # Fehlermeldung bei Task-Fehler

        await self.client.aclose() # Schließt den HTTPX-Client, um Ressourcen freizugeben
        logger.info("Crawl finished.") # Abschlussmeldung des Crawlers

    def get_results(self) -> dict:
        """
        Gibt die Ergebnisse des Crawls zurück.

        Returns:
            dict: Ein Dictionary mit defekten Links, internen und externen Links.
        """
        return {
            "broken_links": self.broken_links,
            "internal_links": sorted(list(self.internal_links)), # Sortiert die internen Links für konsistente Ausgabe
            "external_links": sorted(list(self.external_links)) # Sortiert die externen Links für konsistente Ausgabe
        }

async def main():
    """
    Hauptfunktion zum Parsen von Befehlszeilenargumenten und Starten des Crawlers.
    """
    parser = argparse.ArgumentParser(
        description="Asynchronous Web-Crawler for detecting broken links."
    ) # Erstellt einen Argument-Parser
    parser.add_argument(
        "url", 
        type=str, 
        help="The starting URL for the crawl."
    ) # Argument für die Start-URL
    parser.add_argument(
        "--depth", 
        type=int, 
        default=2, 
        help="Maximum depth to crawl. Default is 2."
    ) # Argument für die maximale Crawling-Tiefe
    parser.add_argument(
        "--concurrency", 
        type=int, 
        default=10, 
        help="Maximum concurrent HTTP requests. Default is 10."
    ) # Argument für die maximale Parallelität
    parser.add_argument(
        "--timeout", 
        type=int, 
        default=10, 
        help="Timeout for HTTP requests in seconds. Default is 10."
    ) # Argument für das HTTP-Anfragen-Timeout

    args = parser.parse_args() # Parsen der Befehlszeilenargumente

    checker = LinkChecker(
        base_url=args.url,
        max_depth=args.depth,
        concurrency_limit=args.concurrency,
        timeout=args.timeout
    ) # Erstellt eine Instanz des LinkCheckers

    await checker.run() # Startet den Crawling-Prozess
    results = checker.get_results() # Holt die Ergebnisse ab

    print("\n--- Crawl Results ---") # Ausgabe der Ergebnisse
    if results["broken_links"]:
        print("Broken Links:")
        for link, status in results["broken_links"].items():
            print(f"  - {link} (Status: {status})") # Ausgabe der defekten Links
    else:
        print("No broken links found.")

    print(f"\nTotal Internal Links Found: {len(results['internal_links'])}") # Gesamtzahl der internen Links
    print(f"Total External Links Found: {len(results['external_links'])}") # Gesamtzahl der externen Links

if __name__ == "__main__":
    try:
        asyncio.run(main()) # Startet die asynchrone Hauptfunktion
    except KeyboardInterrupt:
        logger.info("Crawl interrupted by user.") # Meldung bei Benutzerunterbrechung
        sys.exit(1)


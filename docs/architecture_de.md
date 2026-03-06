# Architektur des Asynchronen Link-Checkers

## 1. Überblick

Der Asynchrone Link-Checker ist als hochleistungsfähiger, asynchroner Web-Crawler konzipiert, der speziell für die Erkennung defekter Links entwickelt wurde. Seine Architektur priorisiert Effizienz, Skalierbarkeit und Wartbarkeit, indem sie Pythons `asyncio` für parallele Operationen und `httpx` für moderne HTTP-Anfragen nutzt. Die Kernidee besteht darin, mehrere URLs gleichzeitig und nicht-blockierend zu verarbeiten, was ein schnelles Scannen großer Websites ermöglicht.

## 2. Kernkomponenten

Das System ist primär um eine zentrale `LinkChecker`-Klasse herum strukturiert, die die gesamte Crawling-Logik kapselt. Diese Klasse orchestriert mehrere Schlüsseloperationen:

### 2.1. `LinkChecker`-Klasse

Dies ist der Haupteinstiegspunkt und Orchestrator des Crawling-Prozesses.

*   **Initialisierung (`__init__`)**: Richtet die Crawl-Parameter wie `base_url`, `max_depth`, `concurrency_limit` und `timeout` ein. Sie initialisiert auch interne Datenstrukturen wie `visited_urls` (ein `set` für schnelle Suchen), `broken_links` (ein `dict` zum Speichern von URLs und ihren Fehlercodes), `internal_links`, `external_links` (beides `sets`) und eine `asyncio.Queue` (oder `collections.deque`) für zu verarbeitende URLs. Ein `asyncio.Semaphore` wird hier erstellt, um die Anzahl gleichzeitiger HTTP-Anfragen zu steuern und eine Serverüberlastung zu verhindern sowie eine faire Ressourcennutzung zu gewährleisten. Ein `httpx.AsyncClient` wird ebenfalls für HTTP-Anfragen initialisiert.

*   **`_normalize_url(url: str) -> str`**: Eine Hilfsmethode, die URLs bereinigt, indem Fragmentbezeichner (z.B. `#section`) entfernt werden. Dies stellt sicher, dass `http://example.com/page#anchor` und `http://example.com/page` für Crawling-Zwecke als dieselbe URL behandelt werden.

*   **`_is_same_domain(url: str) -> bool`**: Bestimmt, ob eine gegebene URL zur gleichen Domain wie die `base_url` gehört. Dies ist entscheidend für die Kategorisierung von Links als intern oder extern und für die Durchsetzung von Crawl-Tiefenbeschränkungen speziell für interne Links.

*   **`_fetch_url(url: str) -> tuple[int | None, str | None]`**: Diese asynchrone Methode führt die eigentliche HTTP-GET-Anfrage mit `httpx` aus. Sie ist vom `asyncio.Semaphore` umhüllt, um die Parallelitätsgrenze einzuhalten. Sie behandelt verschiedene `httpx`-Ausnahmen (z.B. `HTTPStatusError` für 4xx/5xx-Antworten, `RequestError` für Netzwerkprobleme) und gibt den HTTP-Statuscode und den Seiteninhalt zurück (oder `None`, wenn ein Fehler aufgetreten ist).

*   **`_parse_links(html_content: str, current_url: str) -> list[str]`**: Verwendet `BeautifulSoup` (mit `lxml`-Parser für Leistung) zum Parsen des HTML-Inhalts und Extrahieren aller `href`-Attribute aus `<a>`-Tags. Es löst relative URLs relativ zur `current_url` auf und normalisiert sie, bevor eine Liste von absoluten, normalisierten URLs zurückgegeben wird.

*   **`_process_url(url: str, depth: int)`**: Dies ist die asynchrone Kernlogik zur Verarbeitung einer einzelnen URL. Zuerst wird geprüft, ob die URL bereits besucht wurde. Wenn nicht, wird sie als besucht markiert und ihr Inhalt mit `_fetch_url` abgerufen. Schlägt der Abruf fehl oder gibt einen Fehlerstatus (>= 400) zurück, wird die URL als `broken_link` erfasst. Bei Erfolg und innerhalb der `max_depth`-Grenze werden die HTML-Links mit `_parse_links` geparst. Jeder gefundene Link wird dann als intern oder extern kategorisiert und, falls intern und noch nicht besucht, mit inkrementierter Tiefe zur Verarbeitungs-Warteschlange hinzugefügt.

*   **`run()`**: Die öffentliche asynchrone Methode, die den gesamten Crawling-Prozess startet und verwaltet. Sie zieht kontinuierlich URLs aus der `queue`, erstellt `_process_url`-Tasks dafür und fügt diese Tasks einem `set` aktiver Tasks hinzu. Sie verwendet `asyncio.wait` mit `asyncio.FIRST_COMPLETED`, um effizient auf den Abschluss eines Tasks zu warten, sodass neue Tasks geplant werden können, sobald Parallelitäts-Slots verfügbar werden. Die Schleife läuft, bis die Warteschlange leer ist und alle aktiven Tasks abgeschlossen sind.

*   **`get_results() -> dict`**: Bietet eine Zusammenfassung des Crawls und gibt Dictionaries/Sets von `broken_links`, `internal_links` und `external_links` zurück.

### 2.2. `main`-Funktion

Diese Funktion fungiert als Befehlszeilenschnittstelle (CLI)-Handler. Sie verwendet `argparse`, um Befehlszeilenargumente (Start-URL, Tiefe, Parallelität, Timeout) zu verarbeiten, instanziiert den `LinkChecker` mit diesen Parametern, ruft dessen `run()`-Methode auf und gibt dann die aggregierten Ergebnisse aus. Sie beinhaltet auch eine grundlegende Fehlerbehandlung für `KeyboardInterrupt`.

## 3. Parallelitätsmodell

Das Projekt stützt sich stark auf Pythons `asyncio`-Bibliothek für sein Parallelitätsmodell:

*   **Event Loop**: `asyncio` bietet eine Event-Schleife, die Tasks verwaltet und verteilt, wodurch das Programm viele Operationen (wie Netzwerkanfragen) gleichzeitig verarbeiten kann, ohne traditionelle Threads zu verwenden (die ressourcenintensiv sein können).
*   **`async`/`await`**: Schlüsselwörter werden verwendet, um Coroutinen zu definieren und die Kontrolle explizit an die Event-Schleife zurückzugeben, wodurch andere Tasks ausgeführt werden können, während auf E/A-Operationen gewartet wird.
*   **`httpx.AsyncClient`**: Dieser HTTP-Client basiert auf `asyncio` und ist entscheidend für das Senden nicht-blockierender HTTP-Anfragen.
*   **`asyncio.Semaphore`**: Dies wird verwendet, um die Anzahl der gleichzeitig aktiven `_fetch_url`-Coroutinen zu begrenzen. Dies verhindert eine Überlastung des Ziel-Webservers mit zu vielen Anfragen gleichzeitig, was zu IP-Sperren oder einer verschlechterten Leistung führen könnte. Es fungiert als Türsteher, der sicherstellt, dass nur `concurrency_limit` Anfragen gleichzeitig laufen.
*   **`collections.deque` (als Warteschlange)**: Wird verwendet, um zu crawlende URLs zu speichern. Ihre effizienten `append`- und `popleft`-Operationen machen sie für eine Breitensuche (BFS) ähnliche Crawling-Strategie geeignet.
*   **`asyncio.create_task` und `asyncio.wait`**: Diese Funktionen werden verwendet, um den Lebenszyklus einzelner URL-Verarbeitungs-Tasks zu verwalten. `create_task` plant eine Coroutine zur Ausführung in der Event-Schleife, und `asyncio.wait` ermöglicht das Warten auf eine Sammlung von Tasks, was Flexibilität bei der Bearbeitung von Tasks bietet, sobald diese abgeschlossen sind.

## 4. Datenfluss

1.  **Initialisierung**: `main.py` parst Argumente, erstellt eine `LinkChecker`-Instanz.
2.  **Warteschlangenbefüllung**: `base_url` wird zur `LinkChecker.queue` hinzugefügt.
3.  **Crawl-Schleife (`run`)**: Die `run`-Methode führt kontinuierlich Folgendes aus:
    *   Zieht `(url, depth)` aus der `queue`.
    *   Wenn `url` nicht `visited`, erstellt einen `_process_url`-Task.
    *   `_process_url` erwirbt `semaphore`.
    *   `_fetch_url` sendet HTTP-Anfrage.
    *   Wenn `_fetch_url` erfolgreich ist, extrahiert `_parse_links` neue URLs.
    *   Neue interne URLs (unbesucht, innerhalb der Tiefe) werden zur `queue` hinzugefügt.
    *   Externe/interne URLs werden in `external_links`/`internal_links` kategorisiert.
    *   Defekte Links werden in `broken_links` gespeichert.
    *   `semaphore` wird freigegeben.
4.  **Beendigung**: Die Schleife endet, wenn die `queue` leer ist und alle aktiven Tasks abgeschlossen sind.
5.  **Ergebnisse**: `get_results()` gibt die gesammelten Daten zurück.

## 5. Fehlerbehandlung

Der `LinkChecker` implementiert eine robuste Fehlerbehandlung für Netzwerkoperationen:

*   **`httpx.HTTPStatusError`**: Fängt HTTP-Antworten mit 4xx- oder 5xx-Statuscodes ab und speichert sie als defekte Links.
*   **`httpx.RequestError`**: Behandelt Netzwerkprobleme auf niedrigerer Ebene wie Verbindungsfehler, DNS-Auflösungsfehler oder Timeouts.
*   **Allgemeine `Exception`**: Fängt alle anderen unerwarteten Fehler während des URL-Abrufs ab, um ein Abstürzen des Crawlers zu verhindern.
*   **`logging`**: Eine umfassende Protokollierung wird verwendet, um Einblicke in die Operationen des Crawlers zu geben, Warnungen für nicht-kritische Probleme (z.B. defekte Links) und Fehler für kritische Ausfälle zu protokollieren.

## 6. Erweiterbarkeit und zukünftige Verbesserungen

Die aktuelle Architektur ist auf Erweiterbarkeit ausgelegt:

*   **Pluggable Parser**: Die Methode `_parse_links` könnte erweitert werden, um verschiedene Inhaltstypen (z.B. XML-Sitemaps, PDFs) zu unterstützen oder andere Arten von Daten (z.B. Bilder, Skripte) zu extrahieren.
*   **Benutzerdefinierte Reporter**: Die Methode `get_results` kann erweitert werden, um sich in Reporting-Tools, Datenbanken oder Alarmsysteme zu integrieren.
*   **Konfigurationsdatei**: Die Implementierung einer Konfigurationsdatei (z.B. `config.json` oder `config.yaml`) würde komplexere Crawl-Regeln, Ignorier-Muster (Reguläre Ausdrücke für URLs) und Ausgabeformate ohne Codeänderung oder lange Kommandozeilenargumente ermöglichen.
*   **Proxy-Unterstützung**: Integration mit Proxy-Servern für großflächiges Crawling oder geo-spezifische Tests.
*   **Wiederholungsmechanismen**: Implementierung einer exponentiellen Rückzugs- und Wiederholungslogik für vorübergehende Netzwerkfehler.
*   **Ratenbegrenzung**: Fortgeschrittenere Ratenbegrenzungsstrategien pro Domain.

Dieser Architekturüberblick bietet eine Grundlage für das Verständnis des Designs des Asynchronen Link-Checkers und wie er seine Ziele der effizienten Erkennung defekter Links erreicht.

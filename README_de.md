# Asynchroner Link-Checker

[![Python CI/CD](https://github.com/your-username/async-link-checker/actions/workflows/python-app.yml/badge.svg)](https://github.com/your-username/async-link-checker/actions/workflows/python-app.yml)
[![Lizenz: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Ein unternehmenstauglicher, asynchroner Web-Crawler, der entwickelt wurde, um defekte Links innerhalb von Websites und über externe Ressourcen hinweg effizient zu erkennen. Er basiert auf Pythons `asyncio` und `httpx` und bietet hohe Parallelität und Leistung, wodurch er sich für große Webprojekte eignet.

## Inhaltsverzeichnis

- [Funktionen](#funktionen)
- [Installation](#installation)
- [Verwendung](#verwendung)
- [Architektur](#architektur)
- [Mitwirken](#mitwirken)
- [Lizenz](#lizenz)

## Funktionen

*   **Asynchrone Operationen**: Nutzt `asyncio` für nicht-blockierende E/A, was viele gleichzeitige HTTP-Anfragen ermöglicht.
*   **Erkennung defekter Links**: Identifiziert Links, die HTTP-Fehlercodes (4xx, 5xx) zurückgeben.
*   **Kategorisierung interner und externer Links**: Unterscheidet zwischen Links innerhalb derselben Domain und externen Links.
*   **Konfigurierbare Tiefe**: Steuert, wie tief der Crawler eine Website erkundet.
*   **Parallelitätskontrolle**: Begrenzt die Anzahl gleichzeitiger Anfragen, um eine Überlastung der Server zu vermeiden.
*   **URL-Normalisierung**: Behandelt URL-Fragmente und relative Pfade korrekt.
*   **Robuste Fehlerbehandlung**: Verwaltet Netzwerkprobleme und HTTP-Fehler elegant.

## Installation

1.  **Klonen Sie das Repository:**
    ```bash
    git clone https://github.com/your-username/async-link-checker.git
    cd async-link-checker
    ```

2.  **Erstellen und aktivieren Sie eine virtuelle Umgebung (empfohlen):**
    ```bash
    python -m venv .venv
    source .venv/bin/activate # Unter Windows: .venv\Scripts\activate
    ```

3.  **Installieren Sie die erforderlichen Abhängigkeiten:**
    ```bash
    pip install -r requirements.txt
    ```

## Verwendung

Um den Link-Checker auszuführen, führen Sie `main.py` von Ihrem Terminal aus. Sie müssen eine Start-URL angeben.

```bash
python main.py <START_URL> [OPTIONEN]
```

### Argumente

*   `<START_URL>`: Die Basis-URL, von der der Crawler starten wird.

### Optionen

*   `--depth <INT>`: Maximale Crawling-Tiefe. Standard ist `2`.
*   `--concurrency <INT>`: Maximale Anzahl gleichzeitiger HTTP-Anfragen. Standard ist `10`.
*   `--timeout <INT>`: Timeout für HTTP-Anfragen in Sekunden. Standard ist `10`.

### Beispiele

1.  **Grundlegender Crawl einer Website mit Standardeinstellungen:**
    ```bash
    python main.py https://example.com
    ```

2.  **Crawl mit größerer Tiefe und höherer Parallelität:**
    ```bash
    python main.py https://docs.python.org --depth 3 --concurrency 20
    ```

3.  **Crawl mit kürzerem Timeout für schnellere Fehlererkennung:**
    ```bash
    python main.py https://github.com --timeout 5
    ```

## Architektur

Für ein detailliertes Verständnis der Projektarchitektur, der Entwurfsprinzipien und der Kernkomponenten lesen Sie bitte die [Architektur-Dokumentation](docs/architecture_de.md).

## Mitwirken

Wir freuen uns über Beiträge! Bitte beachten Sie unsere Anleitung [CONTRIBUTING.md](CONTRIBUTING.md) für Details zum Einstieg, zum Melden von Fehlern, zum Vorschlagen von Funktionen und zum Einreichen von Pull-Requests.

## Lizenz

Dieses Projekt ist unter der MIT-Lizenz lizenziert – siehe die Datei [LICENSE](LICENSE) für Details.

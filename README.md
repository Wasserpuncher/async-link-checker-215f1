# Async Link Checker

[![Python CI/CD](https://github.com/Wasserpuncher/async-link-checker-215f1/actions/workflows/python-app.yml/badge.svg)](https://github.com/Wasserpuncher/async-link-checker-215f1/actions/workflows/python-app.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

An enterprise-ready, asynchronous web-crawler designed to efficiently detect broken links within websites and across external resources. Built with Python's `asyncio` and `httpx`, it offers high concurrency and performance, making it suitable for large-scale web projects.

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [Architecture](#architecture)
- [Contributing](#contributing)
- [License](#license)

## Features

*   **Asynchronous Operations**: Leverages `asyncio` for non-blocking I/O, allowing many concurrent HTTP requests.
*   **Broken Link Detection**: Identifies links returning HTTP error codes (4xx, 5xx).
*   **Internal & External Link Categorization**: Distinguishes between links within the same domain and external links.
*   **Configurable Depth**: Control how deep the crawler explores a website.
*   **Concurrency Control**: Limit the number of simultaneous requests to prevent overloading servers.
*   **URL Normalization**: Handles URL fragments and relative paths correctly.
*   **Robust Error Handling**: Gracefully manages network issues and HTTP errors.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Wasserpuncher/async-link-checker-215f1.git
    cd async-link-checker
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python -m venv .venv
    source .venv/bin/activate # On Windows: .venv\Scripts\activate
    ```

3.  **Install the required dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## Usage

To run the Link Checker, execute `main.py` from your terminal. You must provide a starting URL.

```bash
python main.py <START_URL> [OPTIONS]
```

### Arguments

*   `<START_URL>`: The base URL from which the crawler will start.

### Options

*   `--config <PATH>`: Path to a JSON configuration file (see below). Defaults to `linkcheck.json` in the current directory if present.
*   `--depth <INT>`: Maximum depth to crawl. Default is `2`.
*   `--concurrency <INT>`: Maximum concurrent HTTP requests. Default is `10`.
*   `--timeout <INT>`: Timeout for HTTP requests in seconds. Default is `10`.

### Configuration file

Instead of passing every parameter on the command line, you can store crawl settings in a JSON file (standard library only, no extra dependencies). By default the tool loads `linkcheck.json` from the current directory if it exists; use `--config` to point at a different file.

```json
{
  "base_url": "https://example.com",
  "max_depth": 3,
  "concurrency": 20,
  "timeout": 10,
  "ignore_patterns": ["*/logout", "*/admin/*", "mailto:"]
}
```

Supported keys:

*   `base_url`: Start URL for the crawl (used when no URL is given on the command line).
*   `max_depth`, `concurrency`, `timeout`: Same meaning as the corresponding options.
*   `ignore_patterns`: A list of glob patterns / substrings; any URL matching one of them is neither fetched nor reported.

Precedence is **built-in defaults < config file < command-line arguments**, so an explicit flag always wins over the config file. Unknown keys in the file are ignored.

```bash
# Use the default linkcheck.json in the current directory
python main.py

# Use an explicit config file, overriding its depth on the command line
python main.py --config configs/prod.json --depth 5
```

### Examples

1.  **Basic crawl of a website with default settings:**
    ```bash
    python main.py https://example.com
    ```

2.  **Crawl with a deeper depth and higher concurrency:**
    ```bash
    python main.py https://docs.python.org --depth 3 --concurrency 20
    ```

3.  **Crawl with a shorter timeout for faster failure detection:**
    ```bash
    python main.py https://github.com --timeout 5
    ```

## Architecture

For a detailed understanding of the project's architecture, design principles, and core components, please refer to the [Architecture Documentation](docs/architecture_en.md).

## Contributing

We welcome contributions! Please refer to our [CONTRIBUTING.md](CONTRIBUTING.md) guide for details on how to get started, report bugs, suggest features, and submit pull requests.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

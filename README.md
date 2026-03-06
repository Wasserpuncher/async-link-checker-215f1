# Async Link Checker

[![Python CI/CD](https://github.com/your-username/async-link-checker/actions/workflows/python-app.yml/badge.svg)](https://github.com/your-username/async-link-checker/actions/workflows/python-app.yml)
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
    git clone https://github.com/your-username/async-link-checker.git
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

*   `--depth <INT>`: Maximum depth to crawl. Default is `2`.
*   `--concurrency <INT>`: Maximum concurrent HTTP requests. Default is `10`.
*   `--timeout <INT>`: Timeout for HTTP requests in seconds. Default is `10`.

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

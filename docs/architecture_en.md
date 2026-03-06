# Architecture of Async Link Checker

## 1. Overview

The Async Link Checker is designed as a high-performance, asynchronous web-crawler specifically tailored for identifying broken links. Its architecture prioritizes efficiency, scalability, and maintainability, leveraging Python's `asyncio` for concurrent operations and `httpx` for modern HTTP requests. The core idea is to process multiple URLs simultaneously without blocking, enabling rapid scanning of large websites.

## 2. Core Components

The system is primarily structured around a central `LinkChecker` class, which encapsulates the entire crawling logic. This class orchestrates several key operations:

### 2.1. `LinkChecker` Class

This is the main entry point and orchestrator of the crawling process.

*   **Initialization (`__init__`)**: Sets up the crawl parameters such as `base_url`, `max_depth`, `concurrency_limit`, and `timeout`. It also initializes internal data structures like `visited_urls` (a `set` for quick lookups), `broken_links` (a `dict` to store URLs and their error codes), `internal_links`, `external_links` (both `sets`), and an `asyncio.Queue` (or `collections.deque`) for URLs to be processed. An `asyncio.Semaphore` is created here to control the number of simultaneous HTTP requests, preventing server overload and ensuring fair resource usage. An `httpx.AsyncClient` is also initialized for making HTTP requests.

*   **`_normalize_url(url: str) -> str`**: A utility method that cleans up URLs by removing fragment identifiers (e.g., `#section`). This ensures that `http://example.com/page#anchor` and `http://example.com/page` are treated as the same URL for crawling purposes.

*   **`_is_same_domain(url: str) -> bool`**: Determines if a given URL belongs to the same domain as the `base_url`. This is crucial for categorizing links as internal or external and for enforcing crawl depth limits specifically on internal links.

*   **`_fetch_url(url: str) -> tuple[int | None, str | None]`**: This asynchronous method performs the actual HTTP GET request using `httpx`. It's wrapped by the `asyncio.Semaphore` to respect the concurrency limit. It handles various `httpx` exceptions (e.g., `HTTPStatusError` for 4xx/5xx responses, `RequestError` for network issues) and returns the HTTP status code and page content (or `None` if an error occurred).

*   **`_parse_links(html_content: str, current_url: str) -> list[str]`**: Uses `BeautifulSoup` (with `lxml` parser for performance) to parse the HTML content and extract all `href` attributes from `<a>` tags. It resolves relative URLs against the `current_url` and normalizes them before returning a list of absolute, normalized URLs.

*   **`_process_url(url: str, depth: int)`**: This is the core asynchronous logic for processing a single URL. It first checks if the URL has already been visited. If not, it marks it as visited, fetches its content using `_fetch_url`. If the fetch fails or returns an error status (>= 400), the URL is recorded as a `broken_link`. If successful and within the `max_depth` limit, it parses the HTML for new links using `_parse_links`. Each found link is then categorized as internal or external and, if internal and not yet visited, added to the processing queue with an incremented depth.

*   **`run()`**: The public asynchronous method that starts and manages the entire crawling process. It continuously pulls URLs from the `queue`, creates `_process_url` tasks for them, and adds these tasks to a `set` of active tasks. It uses `asyncio.wait` with `asyncio.FIRST_COMPLETED` to efficiently wait for any task to finish, allowing new tasks to be scheduled as soon as concurrency slots become available. The loop continues until the queue is empty and all active tasks are completed.

*   **`get_results() -> dict`**: Provides a summary of the crawl, returning dictionaries/sets of `broken_links`, `internal_links`, and `external_links` found.

### 2.2. `main` Function

This function acts as the command-line interface (CLI) handler. It uses `argparse` to process command-line arguments (start URL, depth, concurrency, timeout), instantiates the `LinkChecker` with these parameters, calls its `run()` method, and then prints the aggregated results. It also includes basic error handling for `KeyboardInterrupt`.

## 3. Concurrency Model

The project heavily relies on Python's `asyncio` library for its concurrency model:

*   **Event Loop**: `asyncio` provides an event loop that manages and distributes tasks, allowing the program to handle many operations (like network requests) concurrently without using traditional threads (which can be resource-intensive).
*   **`async`/`await`**: Keywords are used to define coroutines and explicitly yield control back to the event loop, enabling other tasks to run while waiting for I/O operations.
*   **`httpx.AsyncClient`**: This HTTP client is built on `asyncio` and is crucial for making non-blocking HTTP requests.
*   **`asyncio.Semaphore`**: This is used to limit the number of active `_fetch_url` coroutines at any given time. This prevents overwhelming the target web server with too many requests simultaneously, which could lead to IP bans or degraded performance. It acts as a gatekeeper, ensuring that only `concurrency_limit` requests are in flight concurrently.
*   **`collections.deque` (as a queue)**: Used to store URLs to be crawled. Its efficient `append` and `popleft` operations make it suitable for a breadth-first search (BFS) like crawling strategy.
*   **`asyncio.create_task` and `asyncio.wait`**: These functions are used to manage the lifecycle of individual URL processing tasks. `create_task` schedules a coroutine to run in the event loop, and `asyncio.wait` allows waiting for a collection of tasks, providing flexibility to handle tasks as they complete.

## 4. Data Flow

1.  **Initialization**: `main.py` parses arguments, creates `LinkChecker` instance.
2.  **Queue Population**: `base_url` is added to `LinkChecker.queue`.
3.  **Crawl Loop (`run`)**: The `run` method continuously:
    *   Pulls `(url, depth)` from `queue`.
    *   If `url` not `visited`, creates an `_process_url` task.
    *   `_process_url` acquires `semaphore`.
    *   `_fetch_url` makes HTTP request.
    *   If `_fetch_url` succeeds, `_parse_links` extracts new URLs.
    *   New internal URLs (not visited, within depth) are added to `queue`.
    *   External/internal URLs are categorized into `external_links`/`internal_links`.
    *   Broken links are stored in `broken_links`.
    *   `semaphore` is released.
4.  **Termination**: Loop ends when `queue` is empty and all active tasks are complete.
5.  **Results**: `get_results()` returns the collected data.

## 5. Error Handling

The `LinkChecker` implements robust error handling for network operations:

*   **`httpx.HTTPStatusError`**: Catches HTTP responses with 4xx or 5xx status codes, recording them as broken links.
*   **`httpx.RequestError`**: Handles lower-level network issues like connection errors, DNS resolution failures, or timeouts.
*   **General `Exception`**: Catches any other unexpected errors during URL fetching to prevent the crawler from crashing.
*   **`logging`**: Comprehensive logging is used to provide visibility into the crawler's operations, warnings for non-critical issues (e.g., broken links), and errors for critical failures.

## 6. Extensibility and Future Enhancements

The current architecture is designed with extensibility in mind:

*   **Pluggable Parsers**: The `_parse_links` method could be extended to support different content types (e.g., XML sitemaps, PDFs) or to extract other types of data (e.g., images, scripts).
*   **Custom Reporters**: The `get_results` method can be expanded to integrate with reporting tools, databases, or alert systems.
*   **Configuration File**: Implementing a configuration file (e.g., `config.json` or `config.yaml`) would allow more complex crawl rules, ignore patterns (regex for URLs), and output formats without modifying code or using lengthy command-line arguments.
*   **Proxy Support**: Integration with proxy servers for large-scale crawling or geo-specific testing.
*   **Retry Mechanisms**: Implementing exponential backoff and retry logic for transient network errors.
*   **Rate Limiting**: More advanced rate-limiting strategies per domain.

This architectural overview provides a foundation for understanding the Async Link Checker's design and how it achieves its goals of efficient broken link detection.
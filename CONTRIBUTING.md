# Contributing to Async Link Checker

We welcome contributions to the Async Link Checker project! Whether it's reporting bugs, suggesting new features, improving documentation, or submitting code, your help is valuable.

Please take a moment to review this document to understand our contribution guidelines.

## Code of Conduct

We adhere to a [Code of Conduct](CODE_OF_CONDUCT.md) to ensure a welcoming and inclusive environment for everyone. Please read it before participating.

## How to Contribute

### 1. Report Bugs

If you find a bug, please open an issue on our [GitHub Issues page](https://github.com/your-username/async-link-checker/issues). When reporting a bug, please include:

*   A clear and concise description of the bug.
*   Steps to reproduce the behavior.
*   Expected behavior.
*   Actual behavior.
*   Screenshots or error messages, if applicable.
*   Your operating system and Python version.

### 2. Suggest Enhancements

We're always looking for ways to improve Async Link Checker. If you have an idea for a new feature or an enhancement, please open an issue on our [GitHub Issues page](https://github.com/your-username/async-link-checker/issues).

When suggesting an enhancement, please include:

*   A clear and concise description of the proposed feature.
*   Why you think it would be valuable to the project.
*   Any potential challenges or alternative solutions.

### 3. Improve Documentation

Good documentation is crucial for any open-source project. If you find errors, omissions, or areas that could be explained more clearly in our `README.md`, `README_de.md`, or `docs/` files, please feel free to open a pull request with your suggested changes.

### 4. Submit Code Changes (Pull Requests)

We welcome code contributions! To submit code changes, please follow these steps:

1.  **Fork the repository:** Click the "Fork" button at the top right of the repository page.
2.  **Clone your forked repository:**
    ```bash
    git clone https://github.com/YOUR_USERNAME/async-link-checker.git
    cd async-link-checker
    ```
3.  **Create a new branch:** Choose a descriptive branch name (e.g., `feature/add-config-file`, `bugfix/fix-parser-issue`).
    ```bash
    git checkout -b feature/your-feature-name
    ```
4.  **Set up your development environment:**
    ```bash
    python -m venv .venv
    source .venv/bin/activate # On Windows: .venv\Scripts\activate
    pip install -r requirements.txt
    pip install pytest flake8
    ```
5.  **Make your changes:** Implement your feature or bug fix.
    *   **Code Style:** Adhere to [PEP 8](https://www.python.org/dev/peps/pep-0008/) and existing code style. We use `flake8` for linting.
    *   **Type Hints:** Use Python [type hints](https://docs.python.org/3/library/typing.html) for function arguments and return values.
    *   **Docstrings:** Provide clear and concise [docstrings](https://www.python.org/dev/peps/pep-0257/) for all new classes, methods, and functions.
    *   **Comments:** Use German inline comments to explain complex logic or non-obvious parts of the code.
    *   **Tests:** Write unit tests for your changes in `test_main.py` to ensure correctness and prevent regressions.
6.  **Run tests and linting:** Before committing, ensure all tests pass and your code is lint-free.
    ```bash
    pytest
    flake8 .
    ```
7.  **Commit your changes:** Write clear and concise commit messages.
    ```bash
    git add .
    git commit -m "feat: Add support for X" # or "fix: Resolve Y issue"
    ```
8.  **Push your branch:**
    ```bash
    git push origin feature/your-feature-name
    ```
9.  **Open a Pull Request:** Go to the original `async-link-checker` repository on GitHub and you'll see a prompt to open a pull request from your new branch. Provide a detailed description of your changes.

## Code Review Process

All pull requests will be reviewed by maintainers. We may provide feedback and ask for revisions. Please be responsive to comments and be prepared to iterate on your changes.

## License

By contributing to Async Link Checker, you agree that your contributions will be licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

Thank you for contributing to Async Link Checker!

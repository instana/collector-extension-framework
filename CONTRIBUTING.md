# Contributing to Custom Collector Framework

Thank you for your interest in contributing to Instana's Python Custom
Collector Framework! This document provides guidelines and instructions for
contributing to this project.

## Table of Contents

- [Contributing to Custom Collector Framework](#contributing-to-custom-collector-framework)
  - [Table of Contents](#table-of-contents)
  - [Getting Started](#getting-started)
  - [Development Setup](#development-setup)
  - [Coding Standards](#coding-standards)
    - [Python Style Guide](#python-style-guide)
    - [Code Quality](#code-quality)
    - [Documentation](#documentation)
    - [Copyright](#copyright)
  - [Submitting Changes](#submitting-changes)
    - [Pull Request Guidelines](#pull-request-guidelines)
    - [Commit Message Format](#commit-message-format)
  - [Questions?](#questions)
  - [License](#license)

## Getting Started

Before you begin:
- Make sure you have Python 3.12 or higher installed.
- Familiarize yourself with the project by reading the [README.md](README.md)
  documentation.

## Development Setup

1. **Clone the repository**

```shell
git clone https://github.com/instana/collector-extension-framework.git
cd collector-extension-framework
```

2. **Install dependencies**

This project uses `uv` for dependency management.
[Install](https://docs.astral.sh/uv/getting-started/installation/) it if you
haven't already.

Then install project dependencies:

```shell
uv sync --all-extras
```

3. **Set up pre-commit hooks**

Pre-commit hooks help maintain code quality by running checks before each
commit:

```shell
uv run pre-commit install
```

The pre-commit configuration includes:
- YAML, JSON, and TOML validation
- End-of-file fixer
- Trailing whitespace removal

## Coding Standards

### Python Style Guide

- Follow [PEP 8](https://pep8.org/) style guidelines
- Use meaningful variable and function names
- Write docstrings for all public modules, functions, classes, and methods
- Keep functions focused and concise
- Use type hints where appropriate

### Code Quality

- Ensure all pre-commit hooks pass before committing
- Write clean, readable, and maintainable code
- Add comments for complex logic
- Remove unused imports and variables
- Keep line length reasonable (recommended: 79 characters)

### Documentation

- Update documentation when adding or changing features
- Include docstrings with parameter descriptions and return values
- Add inline comments for complex algorithms
- Update README.md if your changes affect usage

### Copyright

Each source file must include a Copyright header to IBM.

```
# (c) Copyright IBM Corp. <YEAR>

```

<!-- ## Testing

### Running Tests

```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_specific.py

# Run with coverage
uv run pytest --cov=collector_extension_framework
```

### Writing Tests

- Write tests for all new features and bug fixes
- Aim for high test coverage
- Use descriptive test names that explain what is being tested
- Follow the Arrange-Act-Assert pattern
- Mock external dependencies appropriately -->

## Submitting Changes

### Pull Request Guidelines

When submitting a pull request:

1. **Title**: Use a clear, descriptive title. Add the Jira issue number at the end.
   - Good: "Add support for custom metric collectors [INSTA-12345]"
   - Bad: "Update code"

2. **Description**: Include:
   - What changes were made and why
   - Related issue numbers (if applicable)
   - Any breaking changes
   - Screenshots (for UI changes)
   - Testing performed

### Commit Message Format

Use clear and descriptive commit messages. We value for the use of
[Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/)
messages and the
[Developer Certificate of Origin](https://developercertificate.org/) (DCO).

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]

[DCO]
```

**Types:**

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks
- `revert`: Reverting a previous change

**Optional Footer(s)**

Jira issue or GitHub issues reference(s) that this commit fixes or closes.

**Developer Certificate of Origin**

We value for the
[Developer Certificate of Origin 1.1](https://developercertificate.org/)
(DCO) which is a legally binding statement asserting that you are the creator
of the work being contributed.

The tags in common use are:

- `Signed-off-by`: this is a developer’s certification that he or she is the
main author of the patch. It MUST include the signer’s name and email address.
- `Co-authored-by`: states that the patch was co-created by several
developers; it is a used to give attribution to co-authors (in addition to the
author attributed by the `Signed-off-by` tag) when multiple people work on a
single patch. It MUST include the signer’s name and email address.

AI agents MUST NOT add `Signed-off-by` tags. Only humans can legally certify
the DCO. The human submitter is responsible for:

- Reviewing all AI-generated code
- Ensuring compliance with licensing requirements
- Adding their own Signed-off-by tag to certify the DCO
- Taking full responsibility for the contribution

When AI tools are used, proper attribution helps track the evolving role of AI
in the development process. Contributions should include an `Assisted-by` tag
in the following format:

```
Assisted-by: AGENT_NAME[:MODEL_VERSION]
```

**Example:**
```
feat: Add multi-endpoint runtime handling

Implement support for managing multiple collection endpoints
within a single runtime instance. This allows better resource
utilization and simplified deployment.

Closes [INSTA-12345]

Signed-off-by: John Doe <john.doe@ibm.com>
Co-authored-by: Jane Doe <jane.doe@ibm.com>
Assisted-by: IBM Bob
```

## Questions?

If you have questions about contributing:

- Check existing documentation
- Search through existing issues
- Open a new issue with the "question" label

## License

By contributing to this project, you agree that your contributions will be licensed under the same license as the project (see [LICENSE](LICENSE)).

---

Thank you for contributing to the Custom Collector Framework! Your efforts help make this project better for everyone.

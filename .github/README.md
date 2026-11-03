# GitHub Automation & CI

This directory contains the GitHub Actions workflows, automation configurations, issue and pull request templates, and repository governance settings used to maintain **obliq-OCR**.

Our automation strategy prioritizes reliability, maintainability, security, and contribution consistency without introducing unnecessary CI complexity.

We maintain a focused set of six CI quality gates alongside automated PR labeling to ensure that every contribution meets the repository's engineering standards.

## CI Quality Gates

The CI pipeline consists of six independent checks, each responsible for validating a specific aspect of the codebase.

| # | Workflow / Check | Purpose | Tooling |
|---|---|---|---|
| 1 | Code Quality & Typing | Enforces linting, formatting, and static type safety. | Ruff, Mypy |
| 2 | Test Matrix & Coverage | Validates functionality across supported Python versions and measures test coverage. | Pytest, Pytest-Cov |
| 3 | Package Build & Integrity | Verifies source distribution, wheel generation, and package metadata. | Hatch-VCS, Build, Twine |
| 4 | Documentation Link Checker | Detects broken internal and external links across Markdown documentation. | Lychee |
| 5 | Secret & Credential Scanning | Identifies accidentally committed API keys, tokens, and sensitive credentials. | Gitleaks |
| 6 | PR Title Validation | Enforces Conventional Commit conventions for pull request titles. | Semantic Pull Request |
| 7 | Auto-Labeler | Automatically categorizes and applies labels to pull requests based on file paths and branch patterns. | GitHub Labeler |

### 1. Code Quality & Typing

**Objective:** Maintain consistent code quality, formatting, and static type safety.

This check validates the Python source code against the repository's linting and typing standards.

Responsibilities:
- Detect code quality issues and common programming errors.
- Enforce consistent formatting.
- Validate static type annotations.
- Maintain compatibility with the project's `py.typed` distribution.

Tools:
- **Ruff:** Linting and formatting.
- **Mypy:** Static type checking.

Validation includes:
- Ruff lint checks.
- Ruff formatting verification.
- Mypy checks against the `src/` directory.

### 2. Test Matrix & Coverage

**Objective:** Ensure application reliability across supported Python versions.

The test pipeline executes the project's automated test suite against Python 3.10, 3.11, and 3.12.

Responsibilities:
- Validate OCR functionality.
- Detect Python-version-specific regressions.
- Verify PDF processing and document extraction.
- Generate synthetic PDF fixtures for reproducible testing.
- Measure test coverage.

Tools:
- **Pytest:** Automated test execution.
- **Pytest-Cov:** Test coverage reporting.
- **Synthetic Fixture Generator:** Generates test PDFs through `tests/scripts/generate_fixtures.py`.

Each Python version is tested independently to identify compatibility issues without one failing matrix job preventing the others from completing.

### 3. Package Build & Integrity

**Objective:** Prevent broken or incomplete package distributions.

This check validates the project's packaging configuration and ensures that obliq-OCR can be built and distributed correctly.

Responsibilities:
- Validate `pyproject.toml` configuration.
- Verify PEP 517 build compatibility.
- Validate version generation through `hatch-vcs`.
- Generate source distributions and binary wheels.
- Check distribution metadata and package rendering.

Tools:
- **Hatch-VCS:** Git-based package versioning.
- **Python Build:** Distribution generation.
- **Twine:** Distribution metadata validation.

Both wheel (`.whl`) and source distribution (`.tar.gz`) artifacts are checked before the build verification passes.

### 4. Documentation Link Checker

**Objective:** Maintain reliable and accessible project documentation.

This check scans Markdown documentation for broken links and invalid file references.

Responsibilities:
- Validate internal Markdown links.
- Detect broken external URLs.
- Identify inaccessible documentation references.
- Prevent outdated links from accumulating.

Tool:
- **Lychee:** Automated Markdown link validation.

The check covers Markdown files throughout the repository, including README files and documentation guides.

### 5. Secret & Credential Scanning

**Objective:** Prevent accidental exposure of sensitive information.

This check scans repository changes for potentially exposed credentials and secrets.

Responsibilities:
- Detect API keys and access tokens.
- Identify accidentally committed credentials.
- Scan commit history for potential secret exposure.
- Reduce the risk of sensitive information entering the repository.

Tool:
- **Gitleaks:** Automated secret detection.

Full Git history is made available to the scanner to support commit-level inspection.

### 6. PR Title Validation

**Objective:** Maintain consistent pull request naming and release conventions.

This check validates incoming pull request titles against the Conventional Commits specification.

Responsibilities:
- Enforce standardized PR titles.
- Improve release note readability.
- Support consistent change categorization.
- Make future changelog and release automation easier.

Tool:
- **Semantic Pull Request:** Conventional Commit title validation.

Accepted title patterns include:

| Type | Example |
|---|---|
| Feature | `feat(engine): add OCR pipeline support` |
| Bug Fix | `fix(pdf): handle corrupted documents` |
| Documentation | `docs(readme): update installation guide` |
| Refactoring | `refactor(core): simplify text extraction` |
| Tests | `test(ocr): add image processing cases` |
| CI / Maintenance | `chore(ci): optimize workflow execution` |

Pull requests that do not follow the required naming convention must be updated before passing this check.

### 7. Auto-Labeler

**Objective:** Automate pull request classification and workflow organization.

This check evaluates modified paths and branch patterns to dynamically apply appropriate labels to incoming pull requests.

Responsibilities:

* Classify pull requests automatically based on changed files and scope.
* Maintain consistent labeling across bug fixes, features, documentation, and tooling updates.
* Streamline pull request triaging and reviewer routing.

Tools:

* **GitHub Labeler:** Automated label assignment action.

Validation includes:

* File path matching against `.github/labeler.yml` configuration rules.
* Pull request metadata evaluation on `pull_request_target` events.
---

## Directory Overview

```text
.github/
├── workflows/
│   ├── ci.yml
│   ├── autolabel.yml
│   └── ...
├── ISSUE_TEMPLATE/
│   └── ...
├── PULL_REQUEST_TEMPLATE.md
├── labeler.yml
└── README.md
```

*The directory structure above represents the intended organization; individual configuration files may vary as repository automation evolves.*

---

**Maintained as part of the obliq-OCR repository engineering and contribution standards.**

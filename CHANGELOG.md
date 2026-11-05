# Changelog

All notable changes to `obliq-OCR` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to Semantic Versioning.

---

## [Unreleased]

### Added
- Automated release note drafting via GitHub Actions and Release Drafter (#41).
- Automated CHANGELOG.md synchronization pipeline (#42).

---

## [0.1.0] - 2026-11-06

### Added
- Initial core high-performance page-aware OCR pipeline combining PyMuPDF text-layer extraction and RapidOCR ONNX inference engines.
- CLI interface and structured Python programmatic API (`parse_document`, `save_result`).
- Automated CI/CD release pipeline with TestPyPI staging, containerized post-publish smoke testing, OIDC trusted publishing, and PEP 740 build provenance attestations.
- Comprehensive CPU-only benchmarking test suites, regression accuracy checks, and performance documentation.

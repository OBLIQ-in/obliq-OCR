# Changelog

All notable changes to `obliq-OCR` will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to Semantic Versioning.

---

## [Unreleased]

## [v0.1.1] - 2026-11-06

## Changes
* ci(docs): update github pages deployment conditions for push events (#82) @abhirajadhikary06
* ci(release): fix detached head and tag_name prefix in changelog sync workflow (#81) @abhirajadhikary06
* ci(docs): enable automatic GitHub Pages deployment on push to main (#80) @abhirajadhikary06
* fix: stop rendering scanned pages twice (#72) @CodeWizard0909
* docs: rewrite README (overview, install, quickstart, badges) (#75) @CodeWizard0909
* docs: add model card with measured accuracy and limitations (#74) @CodeWizard0909
* docs(release): add yank/rollback, hotfix, versioning policy, and team… (#76) @abhirajadhikary06
* docs: document pipeline architecture and output schema (#70) @CodeWizard0909
* docs(release): add yank/rollback, hotfix, versioning policy, and team release guide (#73) @abhirajadhikary06
* ci(release): add missing release-drafter configuration file (#67) @abhirajadhikary06
* ci(release): add release-drafter configuration, workflow, and changelog sync (#65) @abhirajadhikary06
* feat: Add updated OCR benchmark report and charts (#63) @rahulkate173
* fix: relocate README.md to repository root for proper GitHub landing page display (#62) @abhirajadhikary06
* feat: admin guide (#61) @abhirajadhikary06
* ci(release): implement automated PyPI/TestPyPI release pipeline with OIDC authentication (#60) @abhirajadhikary06
* ci: fix OIDC token permissions for build provenance attestation (#59) @abhirajadhikary06
* ci: add token-based release pipeline workflow (#58) @abhirajadhikary06
* ci: add wheel installation smoke test to build-package job (#29) @abhirajadhikary06
* ci: optimize workflows with concurrency, path filtering, and pip caching (#27) @abhirajadhikary06
* ci: add semantic pull request title validation workflow (#24) @abhirajadhikary06
* ci: add dedicated Gitleaks secret and credential scanning workflow (#23) @abhirajadhikary06
* ci: add dedicated documentation link checker workflow via lychee (#22) @abhirajadhikary06
* ci: implement package build and distribution metadata validation (#21) @abhirajadhikary06
* ci: implement cross-python test matrix and coverage reporting (#20) @abhirajadhikary06
* ci: add lint and typecheck workflow  (#19) @abhirajadhikary06
* chore(github): add issue templates for features, architecture, ci, cli, and testing (#12) @abhirajadhikary06
* fix(ci): complete labeler.yml schema update for area:ocr and area:pdf… (#8) @abhirajadhikary06
* fix(ci): update labeler.yml schema for actions/labeler compatibility (#7) @abhirajadhikary06
* chore: set up repository foundation, templates, and autolabeler workflow (#4) @abhirajadhikary06
* Base Code for Obliq-ocr with tests  (#2) @rahulkate173

## 💥 Breaking Changes

* feat: release drafter setup (#69) @abhirajadhikary06
* fix: add release drafter config (#68) @abhirajadhikary06
* feat: test release drafter categorization (#66) @abhirajadhikary06

## 🚢 New Features & Enhancements

* feat: test release drafter categorization (#66) @abhirajadhikary06

## 📦 Packaging & Release
* chore: update project authors in pyproject.toml and remove setup guide (#83) @abhirajadhikary06
* ci: build API reference with mkdocs-material and deploy to GitHub Pages (#77) @CodeWizard0909
* test(ci): complete Phase 3 quality gates with accuracy regression and performance benchmarks (#31) @abhirajadhikary06
* chore(packaging): complete packaging, hatch-vcs versioning, and pre-commit setup (#10) @abhirajadhikary06


---



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

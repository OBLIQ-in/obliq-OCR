# Team Release Process Guide

This guide outlines the standard operating procedure for releasing a new version of `obliq-OCR` to PyPI and GitHub.

---

## 1. Pre-Release Checklist

1. Ensure all features and fixes for the milestone are merged into `main`.
2. Verify that the CI test suite passes successfully on GitHub Actions.
3. Check the auto-generated **Release Draft** in your repository's **Releases** tab to ensure all pull requests are properly categorized under breaking changes, features, or bug fixes.

---

## 2. Cutting a Release

1. Pull the latest changes on `main`:

   ```bash
   git checkout main
   git pull origin main
   ```

2. Create and push a semantic version tag:

   ```bash
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```

---

## 3. Post-Release Verification

1. Monitor the GitHub Actions **Release** workflow to ensure successful wheel building and PyPI publishing.
2. Verify the package is live and downloadable via pip:

   ```bash
   pip install obliq-ocr==X.Y.Z
   ```

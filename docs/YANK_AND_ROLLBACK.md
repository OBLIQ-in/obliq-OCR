# Yank and Rollback Runbook

This runbook outlines the emergency protocol for handling critical bugs, regressions, or corrupted releases published to PyPI or GitHub Releases for `obliq-OCR`.

---

## 1. Yanking a Release on PyPI (Non-Destructive)

If a published package version contains a critical bug that breaks downstream pipelines:

1. Log in to your [PyPI Management Console](https://pypi.org/).
2. Navigate to the `obliq-ocr` project settings and select the affected version.
3. Click **Manage** and select **Yank release**.
   - **Note:** A yanked release remains downloadable if a user explicitly pins that exact version (`==X.Y.Z`). `pip` automatically skips it during standard dependency resolution.

---

## 2. Removing Bad Git Tags & GitHub Releases

To remove a faulty release from GitHub:

1. Delete the local tag:

   ```bash
   git tag -d vX.Y.Z
   ```

2. Delete the remote tag from GitHub:

   ```bash
   git push origin --delete vX.Y.Z
   ```

3. Navigate to your repository's **Releases** page on GitHub, locate the bad release, and click **Delete release**.

---

## 3. Issuing a Hotfix Release

1. Merge the regression fix into `main`.
2. Bump the patch version (e.g., from `0.1.2` to `0.1.3`).
3. Tag and push the new release version to trigger a clean automated deployment via GitHub Actions.

### 📋 Admin Release Guide for `v0.1.0`

> **Note for Maintainer:** [PR #60](https://github.com/OBLIQ-in/obliq-OCR/pull/60) has configured the automated release CI/CD workflow (`release.yml`), TestPyPI staging, smoke testing, and the production PyPI review gate. Follow the steps below to cut the official `v0.1.0` release.

---

### Step 1: Set Up PyPI & TestPyPI Secrets

1. **TestPyPI API Token:**
   - Log into [TestPyPI](https://test.pypi.org/).
   - Go to **Account Settings** $\rightarrow$ **API tokens** $\rightarrow$ **Add API token**.
   - Create a token scoped to **Entire account** (or project-specific once registered) and copy the token string (`pypi-...`).
   - Go to your repository settings: [Repository Secrets Settings](https://github.com/OBLIQ-in/obliq-OCR/settings/secrets/actions).
   - Click **New repository secret** $\rightarrow$ Name: `TESTPYPI_API_TOKEN` $\rightarrow$ Paste your token $\rightarrow$ Click **Add secret**.

2. **PyPI API Token:**
   - Log into [PyPI](https://pypi.org/).
   - Go to **Account Settings** $\rightarrow$ **API tokens** $\rightarrow$ **Add API token**.
   - Create a token scoped to **Entire account** and copy the token string (`pypi-...`).
   - Return to [Repository Secrets Settings](https://github.com/OBLIQ-in/obliq-OCR/settings/secrets/actions).
   - Click **New repository secret** $\rightarrow$ Name: `PYPI_API_TOKEN` $\rightarrow$ Paste your token $\rightarrow$ Click **Add secret**.

---

### Step 2: Push Release Tag & Monitor Actions Workflow

1. Open your terminal on the `main` branch and run:
   ```bash
   git checkout main
   git pull origin main
   git tag v0.1.0
   git push origin v0.1.0
2. Go directly to the repository's Actions page to monitor execution:
   - [OBLIQ-in/obliq-OCR Actions Workflow](https://github.com/OBLIQ-in/obliq-OCR/actions)
3. Monitor the **Release Pipeline** workflow specifically. Watch it build the package, publish to TestPyPI, execute the containerized smoke test, and wait for manual approval at the `pypi` environment gate before publishing to production PyPI.

---

### Step 3: Add Project Collaborators on TestPyPI & PyPI

1. Once all steps in the **Release Pipeline** workflow turn green in GitHub Actions, the projects will be automatically created under your accounts:
   - Manage projects on TestPyPI: [TestPyPI Managed Projects](https://test.pypi.org/manage/projects/)
   - Manage projects on production PyPI: [PyPI Managed Projects](https://pypi.org/manage/projects/)
2. Click on the `obliq-ocr` project on each platform.
3. Go to **Collaborators** (or **Settings** $\rightarrow$ **Collaborators**).
4. Add the username `abhirajadhikary06` as an Maintainer.

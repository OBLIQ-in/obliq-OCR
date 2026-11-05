# Hotfix Process

When a critical production bug or breaking regression is reported on the latest stable version, follow this hotfix protocol:

---

## 1. Branching Strategy

1. Create a dedicated hotfix branch directly off the stable tag or `main`:

   ```bash
   git checkout -b hotfix/vX.Y.Z-patch main
   ```

---

## 2. Implementing the Fix

1. Keep code changes strictly minimal and focused on resolving the issue.
2. Run the fast test suite locally to verify stability:

   ```bash
   pytest tests/test_pipeline.py -k "Imports or Unit or Blank or Digital"
   ```

---

## 3. Version Bumping & Review

1. Update the version indicator if necessary, ensuring a patch increment (`X.Y.(Z+1)`).
2. Open a high-priority Pull Request into `main` with the `bug` or `fix` label so Release Drafter categorizes it correctly.
3. Once reviewed and merged, push the new version tag to trigger automated publishing.

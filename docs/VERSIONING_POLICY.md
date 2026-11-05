# Versioning and Deprecation Policy

`obliq-OCR` strictly follows **Semantic Versioning (SemVer 2.0.0)** (`MAJOR.MINOR.PATCH`).

---

## 1. Version Semantics
* **MAJOR Version:** Incremented for incompatible API or schema changes (e.g., breaking changes to `DocResult` output fields or dropping support for a Python version).
* **MINOR Version:** Incremented for backwards-compatible new features, performance enhancements, or added extraction methods.
* **PATCH Version:** Incremented for backwards-compatible bug fixes, dependency security updates, and documentation patches.

---

## 2. Deprecation Policy
When functions, CLI flags, or schema fields must be phased out:
1. **Warning Stage:** The legacy feature will emit a standard Python `DeprecationWarning` while continuing to function normally.
2. **Support Window:** Deprecations will be supported for a minimum of **one full MINOR release cycle** to give downstream consumers time to migrate.
3. **Removal:** Permanent removal will only occur in the next scheduled MAJOR release.

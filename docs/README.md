# docs

Source for the docs site, which is built with mkdocs (see `mkdocs.yml`) and
published to GitHub Pages when a release is published. To preview it locally
(Python 3.11+): `pip install --group docs`, then `mkdocs serve`.

- [`index.md`](index.md) – home page; it includes the repository README
- [`architecture.md`](architecture.md) – how each page is routed (text layer, OCR or blank), the output schema, and failure modes
- [`model-card.md`](model-card.md) – includes the repository `MODEL_CARD.md`
- [`api.md`](api.md) – API reference, generated from the docstrings in `src/obliq_ocr`
- [`RELEASE_GUIDE.md`](RELEASE_GUIDE.md), [`VERSIONING_POLICY.md`](VERSIONING_POLICY.md), [`HOTFIX_PROCESS.md`](HOTFIX_PROCESS.md), [`YANK_AND_ROLLBACK.md`](YANK_AND_ROLLBACK.md) – release process for maintainers
- [`BENCHMARK.md`](BENCHMARK.md) – benchmark report; the `benchmark-*.svg` charts in this folder belong to it

This file is the folder index on GitHub and is left out of the site.

# API reference

Generated from the docstrings in `src/obliq_ocr`. Everything here can be
imported from the top-level package, for example
`from obliq_ocr import parse_document`.

## Parsing

`parse_document` is the main entry point. In the code it is
`obliq_ocr.core.extract_document`, exported under this name.

::: obliq_ocr.core.extract_document
    options:
      heading: parse_document

::: obliq_ocr.core.save_result

## Results

What `parse_document` returns. The architecture page explains every field and
what `confidence` means.

::: obliq_ocr.core.DocResult

::: obliq_ocr.core.PageResult

## OCR engine

::: obliq_ocr.engine.detect_device

::: obliq_ocr.engine.build_ocr

## Schema types

These typed classes are exported, but `parse_document` doesn't return them
yet ([#71](https://github.com/OBLIQ-in/obliq-OCR/issues/71)).

::: obliq_ocr.schemas.DocumentOutput

::: obliq_ocr.schemas.PageOutput

::: obliq_ocr.schemas.TextElement

::: obliq_ocr.schemas.BoundingBox

# Model Card

## Model Overview

obliq-OCR is an Optical Character Recognition (OCR) project designed to extract text from document images.

The default RapidOCR engine uses the PP-OCRv4 detection and recognition
weights and the PP-OCR mobile orientation classifier. Their license and model
file details are recorded in [THIRD_PARTY_NOTICES](THIRD_PARTY_NOTICES).

## Intended Use

- Extract text from supported document images.
- Process scanned documents.
- Support document digitization workflows.

## Limitations

- Recognition accuracy depends on image quality and resolution.
- Blurry, distorted, or low-contrast images may affect extraction.
- Complex document layouts may impact extraction quality.

## Evaluation

Refer to [BENCHMARK.md](BENCHMARK.md) for performance benchmarks and evaluation details.

## Responsible Use

Extracted text should be reviewed for accuracy before being used in critical workflows.

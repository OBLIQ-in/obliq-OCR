
# =========================================================
# Stage 1: Builder (Full Python & Debian environment)
# =========================================================
FROM python:3.11-slim-bookworm AS builder

WORKDIR /app

# Install build tools, git, and native dependencies for OCR
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    libgl1 \
    libglib2.0-0 \
    libxcb1 \
    && rm -rf /var/lib/apt/lists/*

# Copy git metadata, configuration, and source files
COPY .git .git
COPY pyproject.toml README.md THIRD_PARTY_NOTICES ./
COPY src/ src/

# Build wheel and install package + dependencies
RUN pip install --no-cache-dir build && \
    python -m build --wheel

RUN pip install --no-cache-dir \
    --target=/app/site-packages dist/*.whl

# ---------------------------------------------------------
# Warm ONNX model cache
# ---------------------------------------------------------
RUN mkdir -p /app/cache

ENV HOME=/app
ENV XDG_CACHE_HOME=/app/cache

RUN PYTHONPATH=/app/site-packages python -c \
    "from obliq_ocr import parse_document; print('Warming model cache...')" || true

# ---------------------------------------------------------
# Collect native shared-library dependencies
# ---------------------------------------------------------
RUN mkdir -p /app/libs && \
    find /app/site-packages -type f -name '*.so*' | \
    while read -r sofile; do \
        ldd "$sofile" 2>/dev/null || true; \
    done | \
    awk '/=> \// {print $3} /^\// {print $1}' | \
    sort -u | \
    while read -r lib; do \
        case "$(basename "$lib")" in \
            libc.so.*|libm.so.*|libpthread.so.*|libdl.so.*|ld-linux*) \
                continue ;; \
        esac; \
        cp -L "$lib" /app/libs/ 2>/dev/null || true; \
    done

# =========================================================
# Stage 2: Distroless Production Runner
# =========================================================
FROM gcr.io/distroless/python3-debian12:nonroot AS runner

WORKDIR /app

# Copy installed Python packages
COPY --from=builder /app/site-packages /app/site-packages

# Copy ONNX model cache
COPY --from=builder /app/cache /home/nonroot/.cache

# Copy native shared libraries
COPY --from=builder /app/libs /app/libs

# ---------------------------------------------------------
# Runtime environment configuration
# ---------------------------------------------------------
ENV PYTHONPATH=/app/site-packages
ENV LD_LIBRARY_PATH=/app/libs
ENV HOME=/home/nonroot
ENV XDG_CACHE_HOME=/home/nonroot/.cache

# Run as non-root user
USER nonroot

# OCR CLI entrypoint
ENTRYPOINT ["python3", "-m", "obliq_ocr"]
CMD ["--help"]

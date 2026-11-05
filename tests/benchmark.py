"""
benchmark.py - CPU-only OCR benchmark: obliq-ocr vs EasyOCR, RapidOCR,
Tesseract, PaddleOCR, docTR and the raw PyMuPDF text layer.
"""

from __future__ import annotations

import os

# ---- Force CPU everywhere BEFORE any heavy import ---------------------------
os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
os.environ["OBLIQ_OCR_DEVICE"] = "cpu"
os.environ.setdefault("FLAGS_use_gpu", "false")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

import argparse
import csv
import gc
import importlib.util
import json
import math
import re
import statistics
import sys
import tempfile
import threading
import time
import traceback
import unicodedata
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

# ---- Paths ------------------------------------------------------------------
HERE = Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[1]  # tests/scripts/benchmark.py -> repo root
sys.path.insert(0, str(REPO_ROOT / "src"))  # use the local obliq_ocr package

FIXTURES = REPO_ROOT / "tests" / "fixtures"
GROUND_TRUTH_DIR = FIXTURES / "ground_truth"
RESULTS_DIR = HERE / "benchmark_results"

# =============================================================================
# >>> EDIT THESE TWO LISTS <<<
# =============================================================================
SCANNED_PDFS: List[Path] = [
    r"tests/fixtures\scanned.pdf",
    # FIXTURES / "scanned_invoice_2.pdf",
]

PROCESSED_PDFS: List[Path] = [  # digital / text-layer PDFs
    r"tests\fixtures\processed2.pdf",
    r"tests\fixtures\processed.pdf",
    # FIXTURES / "mixed.pdf",
]
# =============================================================================

DEFAULT_ITERATIONS = 3
DEFAULT_DPI = 200


# =============================================================================
# Text helpers & metrics
# =============================================================================
def norm(text: str) -> str:
    """Normalise for fair comparison (case, unicode, whitespace, '|' column gaps)."""
    text = unicodedata.normalize("NFKC", text or "")
    text = text.replace("|", " ").lower()
    return re.sub(r"\s+", " ", text).strip()


try:
    from rapidfuzz.distance import Levenshtein as _Lev

    def edit_distance(a: Sequence, b: Sequence) -> int:
        return _Lev.distance(a, b)

except ImportError:  # slow pure-python fallback

    def edit_distance(a: Sequence, b: Sequence) -> int:
        if len(a) < len(b):
            a, b = b, a
        prev = list(range(len(b) + 1))
        for i, ca in enumerate(a, 1):
            cur = [i]
            for j, cb in enumerate(b, 1):
                cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
            prev = cur
        return prev[-1]


def cer(ref: str, hyp: str) -> Optional[float]:
    return edit_distance(ref, hyp) / len(ref) if ref else None


def wer(ref: str, hyp: str) -> Optional[float]:
    r = ref.split()
    return edit_distance(r, hyp.split()) / len(r) if r else None


def token_f1(ref_tokens: List[str], hyp_tokens: List[str]) -> float:
    if not ref_tokens and not hyp_tokens:
        return 1.0
    if not ref_tokens or not hyp_tokens:
        return 0.0
    overlap = sum((Counter(ref_tokens) & Counter(hyp_tokens)).values())
    if overlap == 0:
        return 0.0
    p, r = overlap / len(hyp_tokens), overlap / len(ref_tokens)
    return 2 * p * r / (p + r)


_NUM_RE = re.compile(r"\d+(?:[.,/\-:]\d+)*")


def number_recall(ref: str, hyp: str) -> Optional[float]:
    ref_nums = _NUM_RE.findall(ref)
    if not ref_nums:
        return None
    overlap = sum((Counter(ref_nums) & Counter(_NUM_RE.findall(hyp))).values())
    return overlap / len(ref_nums)


_OK_PUNCT = set(".,:;-/\\()&%@#₹$€£'\"!?+=*_|[]{}<>~^`")


def garbage_ratio(text: str) -> Optional[float]:
    chars = [c for c in text if not c.isspace()]
    if not chars:
        return None
    bad = sum(1 for c in chars if c == "\ufffd" or not (c.isalnum() or c in _OK_PUNCT))
    return bad / len(chars)


def mean_ok(values: Sequence[Optional[float]]) -> Optional[float]:
    vals = [v for v in values if v is not None and not (isinstance(v, float) and math.isnan(v))]
    return sum(vals) / len(vals) if vals else None


def percentile(values: Sequence[float], q: float) -> Optional[float]:
    if not values:
        return None
    s = sorted(values)
    k = (len(s) - 1) * q
    lo, hi = int(math.floor(k)), int(math.ceil(k))
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


# =============================================================================
# Memory monitor (RSS growth while an engine runs)
# =============================================================================
try:
    import psutil
except ImportError:  # pragma: no cover
    psutil = None


class MemMonitor:
    def __init__(self, interval: float = 0.02):
        self.interval = interval
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self.peak = 0
        self.base = 0
        self._proc = psutil.Process() if psutil else None

    def _loop(self):
        while not self._stop.is_set():
            self.peak = max(self.peak, self._proc.memory_info().rss)
            time.sleep(self.interval)

    def start(self):
        if not self._proc:
            return
        self.base = self.peak = self._proc.memory_info().rss
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> Optional[float]:
        if not self._proc:
            return None
        self._stop.set()
        if self._thread:
            self._thread.join()
        self.peak = max(self.peak, self._proc.memory_info().rss)
        return max(self.peak - self.base, 0) / (1024 * 1024)


# =============================================================================
# PDF helpers
# =============================================================================
def _fitz():
    try:
        import fitz  # PyMuPDF
    except ImportError:
        import pymupdf as fitz  # type: ignore
    return fitz


def render_pages(pdf: Path, dpi: int):
    """Yield RGB numpy arrays, one per page."""
    import numpy as np

    fitz = _fitz()
    with fitz.open(str(pdf)) as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=dpi, colorspace=fitz.csRGB, alpha=False)
            yield (
                np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3).copy()
            )


def pdf_text_layer(pdf: Path) -> List[str]:
    fitz = _fitz()
    with fitz.open(str(pdf)) as doc:
        return [p.get_text("text") for p in doc]


def make_warmup_pdf(path: Path) -> Path:
    """A 1-page *scanned-style* PDF (text baked into an image) to trigger lazy model loading."""
    fitz = _fitz()
    src = fitz.open()
    page = src.new_page(width=400, height=200)
    page.insert_text((30, 80), "Invoice Number: 12345  Amount: 50,000", fontsize=16)
    pix = page.get_pixmap(dpi=150)
    out = fitz.open()
    p2 = out.new_page(width=400, height=200)
    p2.insert_image(p2.rect, pixmap=pix)
    out.save(str(path))
    return path


def boxes_to_text(items: List[Tuple[float, float, float, float, str]]) -> str:
    """Group (x0, y0, x1, y1, text) word/line boxes into reading-order lines."""
    if not items:
        return ""
    items = sorted(items, key=lambda t: (t[1] + t[3]) / 2)
    lines: List[Dict[str, Any]] = []
    for it in items:
        yc, h = (it[1] + it[3]) / 2, max(it[3] - it[1], 1.0)
        if lines and abs(yc - lines[-1]["yc"]) <= 0.5 * lines[-1]["h"]:
            lines[-1]["items"].append(it)
        else:
            lines.append({"yc": yc, "h": h, "items": [it]})
    return "\n".join(
        " ".join(t[4] for t in sorted(ln["items"], key=lambda t: t[0])) for ln in lines
    )


def poly_to_box(poly) -> Tuple[float, float, float, float]:
    xs = [float(p[0]) for p in poly]
    ys = [float(p[1]) for p in poly]
    return min(xs), min(ys), max(xs), max(ys)


# =============================================================================
# Engine adapters
#   run(pdf, dpi) -> (page_texts, confidences)   [end-to-end: PDF in, text out]
# =============================================================================
class Engine:
    key = "base"
    name = "base"
    module = ""  # importable module name for the availability check
    is_ocr = True

    def check(self) -> Optional[str]:
        if self.module and importlib.util.find_spec(self.module) is None:
            return f"module '{self.module}' not installed"
        return None

    def setup(self) -> None:
        pass

    def run(self, pdf: Path, dpi: int) -> Tuple[List[str], List[float]]:
        raise NotImplementedError


class ImageEngine(Engine):
    """Engines that OCR page images; PDF rendering time is included (end-to-end)."""

    def ocr_image(self, img) -> Tuple[str, List[float]]:
        raise NotImplementedError

    def run(self, pdf: Path, dpi: int):
        texts, confs = [], []
        for img in render_pages(pdf, dpi):
            t, c = self.ocr_image(img)
            texts.append(t)
            confs.extend(c)
        return texts, confs


class ObliqEngine(Engine):
    key, name, module = "obliq", "obliq-ocr", "obliq_ocr"

    def setup(self):
        import obliq_ocr

        fn = getattr(obliq_ocr, "parse_document", None)
        if fn is None:
            from obliq_ocr.core import extract_document as fn  # type: ignore
        self.fn = fn

    def run(self, pdf: Path, dpi: int):
        res = self.fn(str(pdf))
        d = res.to_dict() if hasattr(res, "to_dict") else res
        pages = d["pages"]
        texts = [p.get("text", "") or "" for p in pages]
        confs = [float(p["confidence"]) for p in pages if p.get("confidence") is not None]
        return texts, confs


class RapidOCREngine(ImageEngine):
    key, name, module = "rapidocr", "rapidocr-onnx", "rapidocr_onnxruntime"

    def setup(self):
        from rapidocr_onnxruntime import RapidOCR

        self.eng = RapidOCR()

    def ocr_image(self, img):
        result, _ = self.eng(img)
        items, confs = [], []
        for box, text, score in result or []:
            x0, y0, x1, y1 = poly_to_box(box)
            items.append((x0, y0, x1, y1, text))
            confs.append(float(score))
        return boxes_to_text(items), confs


class EasyOCREngine(ImageEngine):
    key, name, module = "easyocr", "easyocr", "easyocr"

    def setup(self):
        import easyocr

        self.reader = easyocr.Reader(["en"], gpu=False, verbose=False)

    def ocr_image(self, img):
        items, confs = [], []
        for box, text, conf in self.reader.readtext(img):
            x0, y0, x1, y1 = poly_to_box(box)
            items.append((x0, y0, x1, y1, text))
            confs.append(float(conf))
        return boxes_to_text(items), confs


class TesseractEngine(ImageEngine):
    key, name, module = "tesseract", "tesseract", "pytesseract"

    def setup(self):
        import pytesseract

        pytesseract.get_tesseract_version()  # raises if the binary is missing
        self.pt = pytesseract

    def ocr_image(self, img):
        d = self.pt.image_to_data(img, output_type=self.pt.Output.DICT)
        lines: Dict[Tuple, List[Tuple[int, str]]] = {}
        confs = []
        for i, txt in enumerate(d["text"]):
            if not txt.strip():
                continue
            c = float(d["conf"][i])
            if c >= 0:
                confs.append(c / 100.0)
            key = (d["block_num"][i], d["par_num"][i], d["line_num"][i])
            lines.setdefault(key, []).append((d["left"][i], txt))
        text = "\n".join(" ".join(w for _, w in sorted(ws)) for _, ws in sorted(lines.items()))
        return text, confs


class PaddleEngine(ImageEngine):
    key, name, module = "paddleocr", "paddleocr", "paddleocr"

    def setup(self):
        from paddleocr import PaddleOCR

        try:
            self.ocr = PaddleOCR(use_angle_cls=True, lang="en", use_gpu=False, show_log=False)
        except (TypeError, ValueError):  # PaddleOCR 3.x API
            self.ocr = PaddleOCR(lang="en", device="cpu")

    def ocr_image(self, img):
        try:
            res = self.ocr.ocr(img, cls=True)
        except TypeError:
            res = self.ocr.predict(img)
        items, confs = [], []
        if not res:
            return "", confs
        first = res[0]
        if first is None:
            return "", confs
        if hasattr(first, "get") and ("rec_texts" in first):  # 3.x result dict
            polys = first.get("rec_polys", first.get("dt_polys", []))
            for poly, t, s in zip(polys, first["rec_texts"], first["rec_scores"]):
                x0, y0, x1, y1 = poly_to_box(poly)
                items.append((x0, y0, x1, y1, t))
                confs.append(float(s))
        else:  # 2.x: [[box, (text, score)], ...]
            for box, (t, s) in first:
                x0, y0, x1, y1 = poly_to_box(box)
                items.append((x0, y0, x1, y1, t))
                confs.append(float(s))
        return boxes_to_text(items), confs


class DocTREngine(ImageEngine):
    key, name, module = "doctr", "doctr", "doctr"

    def setup(self):
        from doctr.models import ocr_predictor

        self.model = ocr_predictor(pretrained=True)

    def ocr_image(self, img):
        out = self.model([img]).export()
        lines, confs = [], []
        for page in out["pages"]:
            for block in page["blocks"]:
                for line in block["lines"]:
                    lines.append(" ".join(w["value"] for w in line["words"]))
                    confs.extend(float(w["confidence"]) for w in line["words"])
        return "\n".join(lines), confs


class PyMuPDFEngine(Engine):
    """Baseline: native text layer only. Instant on digital PDFs, blind on scans."""

    key, name, module = "pymupdf", "pymupdf-textlayer", "fitz"
    is_ocr = False

    def check(self):
        if importlib.util.find_spec("fitz") is None and importlib.util.find_spec("pymupdf") is None:
            return "PyMuPDF not installed"
        return None

    def run(self, pdf: Path, dpi: int):
        return pdf_text_layer(pdf), []


ALL_ENGINES: List[Engine] = [
    ObliqEngine(),
    EasyOCREngine(),
    RapidOCREngine(),
    TesseractEngine(),
    PaddleEngine(),
    DocTREngine(),
    PyMuPDFEngine(),
]


# =============================================================================
# Benchmark core
# =============================================================================
def time_run(engine: Engine, pdf: Path, dpi: int):
    gc.collect()
    mon = MemMonitor()
    mon.start()
    t0 = time.perf_counter()
    try:
        pages, confs = engine.run(pdf, dpi)
        err = None
    except Exception as e:  # noqa: BLE001
        pages, confs, err = [], [], f"{type(e).__name__}: {e}"
        traceback.print_exc(limit=2)
    dt = time.perf_counter() - t0
    mem = mon.stop()
    return pages, confs, dt, mem, err


def load_reference(pdf: Path, group: str) -> Tuple[Optional[str], str]:
    gt = GROUND_TRUTH_DIR / f"{pdf.stem}.txt"
    if gt.exists():
        return norm(gt.read_text(encoding="utf-8", errors="ignore")), "ground-truth"
    if group == "processed":
        try:
            txt = norm("\n".join(pdf_text_layer(pdf)))
            if len(txt) >= 50:
                return txt, "text-layer"
        except Exception:  # noqa: BLE001
            pass
    return None, "none"


def fmt(v: Optional[float], digits: int = 2, pct: bool = False) -> str:
    if v is None:
        return "n/a"
    return f"{v * 100:.{digits}f}%" if pct else f"{v:.{digits}f}"


def print_table(title: str, headers: List[str], rows: List[List[str]]):
    cols = list(zip(headers, *rows)) if rows else [(h,) for h in headers]
    widths = [max(len(str(x)) for x in col) for col in cols]
    sep = "+-" + "-+-".join("-" * w for w in widths) + "-+"
    print(f"\n{title}")
    print(sep)
    print("| " + " | ".join(h.ljust(w) for h, w in zip(headers, widths)) + " |")
    print(sep)
    for r in rows:
        print(
            "| "
            + " | ".join(
                str(c).ljust(w) if i == 0 else str(c).rjust(w)
                for i, (c, w) in enumerate(zip(r, widths))
            )
            + " |"
        )
    print(sep)


# key, label, formatter, better ("min"/"max"/None)
METRICS = [
    ("cold_start", "1. Cold start (s)", lambda v: fmt(v, 2), "min"),
    ("mean_latency", "2. Mean latency / doc (s)", lambda v: fmt(v, 2), "min"),
    ("p95_latency", "3. P95 latency (s)", lambda v: fmt(v, 2), "min"),
    ("jitter", "4. Latency jitter σ (s)", lambda v: fmt(v, 3), "min"),
    ("sec_per_page", "5. Seconds / page", lambda v: fmt(v, 3), "min"),
    ("pages_per_sec", "6. Throughput (pages/s)", lambda v: fmt(v, 2), "max"),
    ("peak_mem", "7. Peak memory (MB)", lambda v: fmt(v, 0), "min"),
    ("confidence", "8. Mean confidence (info)", lambda v: fmt(v, 3), None),
    ("cer", "9. CER (%)", lambda v: fmt(v, 2, True), "min"),
    ("wer", "10. WER (%)", lambda v: fmt(v, 2, True), "min"),
    ("f1", "11. Token F1 (%)", lambda v: fmt(v, 2, True), "max"),
    ("numrec", "12. Number recall (%)", lambda v: fmt(v, 2, True), "max"),
    ("consensus", "13. Consensus agreement (%)", lambda v: fmt(v, 2, True), "max"),
    ("garbage", "14. Garbage ratio (%)", lambda v: fmt(v, 2, True), "min"),
    ("stability", "15. Run-to-run stability (%)", lambda v: fmt(v, 2, True), "max"),
]


def summarise(docs: List[Dict[str, Any]], cold: Optional[float]) -> Dict[str, Optional[float]]:
    ok = [d for d in docs if not d.get("error") and d["times"]]
    if not ok:
        return {m[0]: None for m in METRICS} | {"cold_start": cold, "n_ok": 0}
    all_times = [t for d in ok for t in d["times"]]
    total_time = sum(statistics.mean(d["times"]) for d in ok)
    total_pages = sum(d["pages"] for d in ok)
    mems = [d["peak_mem"] for d in ok if d["peak_mem"] is not None]
    return {
        "cold_start": cold,
        "mean_latency": statistics.mean(statistics.mean(d["times"]) for d in ok),
        "p95_latency": percentile(all_times, 0.95),
        "jitter": mean_ok(
            [statistics.pstdev(d["times"]) if len(d["times"]) > 1 else 0.0 for d in ok]
        ),
        "sec_per_page": total_time / total_pages if total_pages else None,
        "pages_per_sec": total_pages / total_time if total_time else None,
        "peak_mem": max(mems) if mems else None,
        "confidence": mean_ok([d["confidence"] for d in ok]),
        "cer": mean_ok([d["cer"] for d in ok]),
        "wer": mean_ok([d["wer"] for d in ok]),
        "f1": mean_ok([d["f1"] for d in ok]),
        "numrec": mean_ok([d["numrec"] for d in ok]),
        "consensus": mean_ok([d["consensus"] for d in ok]),
        "garbage": mean_ok([d["garbage"] for d in ok]),
        "stability": mean_ok([d["stability"] for d in ok]),
        "n_ok": len(ok),
    }


def print_summary(title: str, per_engine: Dict[str, Dict[str, Any]], n_docs: int):
    names = list(per_engine)
    if not names:
        return
    best: Dict[str, Optional[str]] = {}
    for key, _, _, better in METRICS:
        vals = {n: per_engine[n][key] for n in names if per_engine[n].get(key) is not None}
        best[key] = (
            (min(vals, key=vals.get) if better == "min" else max(vals, key=vals.get))
            if vals and better
            else None
        )

    rows = []
    for key, label, f, _ in METRICS:
        row = [label]
        for n in names:
            s = f(per_engine[n].get(key))
            row.append(s + (" *" if best[key] == n and s != "n/a" else ""))
        rows.append(row)
    rows.append(["Docs completed"] + [f"{per_engine[n].get('n_ok', 0)}/{n_docs}" for n in names])

    # mean rank across ranked metrics -> overall ordering
    ranks: Dict[str, List[int]] = {n: [] for n in names}
    for key, _, _, better in METRICS:
        if not better:
            continue
        vals = {n: per_engine[n][key] for n in names if per_engine[n].get(key) is not None}
        for pos, n in enumerate(sorted(vals, key=vals.get, reverse=(better == "max")), 1):
            ranks[n].append(pos)
    rows.append(
        ["Mean rank (lower = better)"]
        + [f"{statistics.mean(ranks[n]):.2f}" if ranks[n] else "n/a" for n in names]
    )
    print_table(title + "   (* = best)", ["Metric"] + names, rows)


def main():
    ap = argparse.ArgumentParser(description="CPU-only OCR benchmark for obliq-ocr")
    ap.add_argument(
        "--iterations", type=int, default=DEFAULT_ITERATIONS, help="timed runs per PDF per engine"
    )
    ap.add_argument(
        "--dpi", type=int, default=DEFAULT_DPI, help="render DPI for image-based engines"
    )
    ap.add_argument(
        "--engines", nargs="*", choices=[e.key for e in ALL_ENGINES], help="subset of engines"
    )
    ap.add_argument("--group", choices=["scanned", "processed", "both"], default="both")
    ap.add_argument("--no-save", action="store_true", help="do not write JSON/CSV results")
    args = ap.parse_args()

    print("=" * 78)
    print(" OCR BENCHMARK  |  CPU only")
    print(
        f" python {sys.version.split()[0]}  |  cpus: {os.cpu_count()}  | "
        f"iterations: {args.iterations}  |  dpi: {args.dpi}"
    )
    print(f" repo: {REPO_ROOT}")
    print("=" * 78)

    groups = {"scanned": SCANNED_PDFS, "processed": PROCESSED_PDFS}
    if args.group != "both":
        groups = {args.group: groups[args.group]}
    groups = {g: [Path(p) for p in pdfs if Path(p).exists()] for g, pdfs in groups.items()}
    for g, orig in (("scanned", SCANNED_PDFS), ("processed", PROCESSED_PDFS)):
        for p in orig:
            if g in groups and not Path(p).exists():
                print(f"[warn] missing {g} PDF, skipping: {p}")
    if not any(groups.values()):
        sys.exit(
            "No PDFs found. Add files to tests/fixtures/ and edit SCANNED_PDFS / PROCESSED_PDFS."
        )

    # ---- engine setup + cold start -----------------------------------------
    tmp = tempfile.TemporaryDirectory()
    warm_pdf = make_warmup_pdf(Path(tmp.name) / "warmup.pdf")
    active: List[Engine] = []
    cold: Dict[str, float] = {}
    for eng in ALL_ENGINES:
        if args.engines and eng.key not in args.engines:
            continue
        reason = eng.check()
        if reason:
            print(f"[skip] {eng.name}: {reason}")
            continue
        try:
            t0 = time.perf_counter()
            eng.setup()
            eng.run(warm_pdf, args.dpi)  # warm-up: triggers lazy model loading
            cold[eng.name] = time.perf_counter() - t0
            active.append(eng)
            print(f"[ready] {eng.name:<20} cold start {cold[eng.name]:.2f}s")
        except Exception as e:  # noqa: BLE001
            print(f"[skip] {eng.name}: setup failed ({type(e).__name__}: {e})")
    if not active:
        sys.exit("No engines available.")
    ocr_engines = [e for e in active if e.is_ocr]

    # ---- run ---------------------------------------------------------------
    all_docs: Dict[str, Dict[str, List[Dict[str, Any]]]] = {
        g: {e.name: [] for e in active} for g in groups
    }
    iteration_log: List[Dict[str, Any]] = []

    for group, pdfs in groups.items():
        for pdf in pdfs:
            ref, ref_src = load_reference(pdf, group)
            print("\n" + "-" * 78)
            print(f"[{group.upper()}] {pdf.name}   reference: {ref_src}")
            print("-" * 78)
            texts_by_engine: Dict[str, str] = {}
            docs_this_pdf: Dict[str, Dict[str, Any]] = {}

            for eng in active:
                doc: Dict[str, Any] = {
                    "pdf": pdf.name,
                    "engine": eng.name,
                    "times": [],
                    "texts": [],
                    "pages": 0,
                    "peak_mem": None,
                    "error": None,
                    "confidence": None,
                }
                mems, last_confs = [], []
                for it in range(1, args.iterations + 1):
                    pages, confs, dt, mem, err = time_run(eng, pdf, args.dpi)
                    if err:
                        doc["error"] = err
                        print(f"  {eng.name:<20} iter {it}/{args.iterations}  ERROR {err}")
                        break
                    full = norm("\n".join(pages))
                    doc["times"].append(dt)
                    doc["texts"].append(full)
                    doc["pages"] = len(pages)
                    last_confs = confs
                    if mem is not None:
                        mems.append(mem)
                    mean_conf = mean_ok(confs)
                    iteration_log.append(
                        {
                            "group": group,
                            "pdf": pdf.name,
                            "engine": eng.name,
                            "iteration": it,
                            "seconds": dt,
                            "pages": len(pages),
                            "chars": len(full),
                            "confidence": mean_conf,
                            "peak_mem_mb": mem,
                        }
                    )
                    print(
                        f"  {eng.name:<20} iter {it}/{args.iterations}  "
                        f"{dt:8.2f}s  {len(pages):>3} pages  "
                        f"{dt / max(len(pages), 1):6.2f} s/pg  {len(full):>7,} chars  "
                        f"conf {fmt(mean_conf, 3):>5}  mem +{fmt(mem, 0):>5} MB"
                    )
                if doc["times"]:
                    doc["peak_mem"] = max(mems) if mems else None
                    doc["confidence"] = mean_ok(last_confs)
                    final = doc["texts"][-1]
                    texts_by_engine[eng.name] = final
                    hyp_tok = final.split()
                    doc["garbage"] = garbage_ratio(final)
                    if ref is not None:
                        doc["cer"], doc["wer"] = cer(ref, final), wer(ref, final)
                        doc["f1"] = token_f1(ref.split(), hyp_tok)
                        doc["numrec"] = number_recall(ref, final)
                    else:
                        doc["cer"] = doc["wer"] = doc["f1"] = doc["numrec"] = None
                    doc["stability"] = (
                        mean_ok(
                            [token_f1(doc["texts"][0].split(), t.split()) for t in doc["texts"][1:]]
                        )
                        if len(doc["texts"]) > 1
                        else None
                    )
                docs_this_pdf[eng.name] = doc

            # consensus agreement vs. the *other OCR engines* (needs >= 2 of them)
            peers = {n: t for n, t in texts_by_engine.items() if n in {e.name for e in ocr_engines}}
            for name, doc in docs_this_pdf.items():
                others = [t.split() for n, t in peers.items() if n != name]
                doc["consensus"] = (
                    mean_ok([token_f1(o, texts_by_engine[name].split()) for o in others])
                    if name in texts_by_engine and others
                    else None
                )
                doc.pop("texts", None)
                all_docs[group][name].append(doc)

    # ---- per-iteration table ----------------------------------------------
    rows = [
        [
            r["group"],
            r["pdf"],
            r["engine"],
            str(r["iteration"]),
            f"{r['seconds']:.2f}",
            str(r["pages"]),
            f"{r['seconds'] / max(r['pages'], 1):.3f}",
            f"{r['chars']:,}",
            fmt(r["confidence"], 3),
            fmt(r["peak_mem_mb"], 0),
        ]
        for r in iteration_log
    ]
    print_table(
        "ALL ITERATIONS",
        ["group", "pdf", "engine", "iter", "sec", "pages", "s/page", "chars", "conf", "+MB"],
        rows,
    )

    # ---- summaries ----------------------------------------------------------
    summaries: Dict[str, Dict[str, Dict[str, Any]]] = {}
    for group in groups:
        n_docs = len(groups[group])
        summaries[group] = {n: summarise(docs, cold.get(n)) for n, docs in all_docs[group].items()}
        print_summary(f"SUMMARY - {group.upper()} ({n_docs} PDF(s))", summaries[group], n_docs)
    if len(groups) > 1:
        combined = {
            n: summarise([d for g in groups for d in all_docs[g][n]], cold.get(n)) for n in cold
        }
        summaries["overall"] = combined
        print_summary("SUMMARY - OVERALL", combined, sum(len(v) for v in groups.values()))

    print(
        "\nNotes: latency is end-to-end (PDF in -> text out; image engines include rendering). "
        "Confidence scales differ per engine and are informational only. "
        "Number of iterations ≥ 2 is needed for jitter and stability."
    )

    # ---- save ---------------------------------------------------------------
    if not args.no_save:
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        jp = RESULTS_DIR / f"benchmark_{stamp}.json"
        jp.write_text(
            json.dumps(
                {
                    "iterations": iteration_log,
                    "per_document": all_docs,
                    "summary": summaries,
                    "cold_start": cold,
                },
                indent=2,
                default=str,
            )
        )
        cp = RESULTS_DIR / f"benchmark_{stamp}_iterations.csv"
        with cp.open("w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(iteration_log[0].keys()))
            w.writeheader()
            w.writerows(iteration_log)
        print(f"\nSaved: {jp}\nSaved: {cp}")
    tmp.cleanup()


if __name__ == "__main__":
    main()

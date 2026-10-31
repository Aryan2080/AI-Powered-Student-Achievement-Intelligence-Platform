"""
src/nlp/document_ingestion.py
=============================
Evidence Document Ingestion, PDF Text Extraction & OCR Subsystem
AI-Powered Student Achievement Intelligence Platform — Member 1

Provides an auditable document ingestion and text extraction pipeline for
achievement evidence documents (certificates, competition awards, publications,
project briefs, letters).

Supported Formats:
    - PDF (.pdf): Native text extraction first via pypdf; automatic OCR fallback
      for scanned or image-based pages.
    - PNG (.png): Visual certificate / badge / receipt OCR ingestion.
    - JPEG / JPG (.jpg, .jpeg): Visual certificate / scanned document OCR ingestion.
    - Unsupported formats (.docx, .zip, .exe, etc.): Explicit, structured rejection.

Key Design Principles:
    1. Provenance Preservation: Full raw text, normalized text, page numbers,
       extraction methods, and timestamps are captured per page and per document.
    2. Graceful Degradation: Missing OCR engines, corrupted documents, and empty
       files return informative status codes rather than unhandled exceptions.
    3. Pluggable OCR Engine: Supports system Tesseract via pytesseract, with fallback
       detection and support for custom OCR callable injection for testing/evaluation.
    4. Deterministic Normalization: Uses unicode normalization and whitespace
       standardization aligned with the platform NLP preprocessing pipeline.
"""

from __future__ import annotations

import io
import os
import shutil
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple, Union

from PIL import Image

try:
    import pypdf
    from pypdf.errors import PdfReadError, PdfStreamError
    _PYPDF_AVAILABLE = True
except ImportError:  # pragma: no cover
    pypdf = None
    PdfReadError = Exception
    PdfStreamError = Exception
    _PYPDF_AVAILABLE = False

try:
    import pytesseract
    _PYTESSERACT_AVAILABLE = True
except ImportError:  # pragma: no cover
    pytesseract = None
    _PYTESSERACT_AVAILABLE = False

from .text_preprocessing import normalize_unicode, normalize_whitespace


# ==============================================================================
# ENUMS & CONSTANTS
# ==============================================================================

class DocumentFormat(str, Enum):
    """Supported document formats for evidence ingestion."""
    PDF = "PDF"
    PNG = "PNG"
    JPEG = "JPEG"
    UNSUPPORTED = "UNSUPPORTED"


class ExtractionMethod(str, Enum):
    """Method used to extract text from a page or document."""
    NATIVE_PDF = "NATIVE_PDF"
    OCR = "OCR"
    HYBRID = "HYBRID"
    NONE = "NONE"


class ExtractionStatus(str, Enum):
    """Status of the extraction operation."""
    SUCCESS = "SUCCESS"
    PARTIAL_SUCCESS = "PARTIAL_SUCCESS"
    EMPTY_DOCUMENT = "EMPTY_DOCUMENT"
    OCR_FALLBACK_APPLIED = "OCR_FALLBACK_APPLIED"
    OCR_UNAVAILABLE = "OCR_UNAVAILABLE"
    UNSUPPORTED_FORMAT = "UNSUPPORTED_FORMAT"
    CORRUPTED_FILE = "CORRUPTED_FILE"
    FILE_NOT_FOUND = "FILE_NOT_FOUND"


# Magic byte signatures for file type detection
_MAGIC_PDF = b"%PDF-"
_MAGIC_PNG = b"\x89PNG\r\n\x1a\n"
_MAGIC_JPEG = b"\xff\xd8\xff"

# Extension mapping
_EXTENSION_FORMAT_MAP = {
    ".pdf": DocumentFormat.PDF,
    ".png": DocumentFormat.PNG,
    ".jpg": DocumentFormat.JPEG,
    ".jpeg": DocumentFormat.JPEG,
}


# ==============================================================================
# DATA CLASSES
# ==============================================================================

@dataclass
class PageExtractionResult:
    """Provenance-preserving extraction result for a single document page."""
    page_number: int  # 1-indexed
    raw_text: str
    normalized_text: str
    extraction_method: ExtractionMethod
    status: ExtractionStatus
    char_count: int
    word_count: int
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert page result to JSON-serializable dictionary."""
        data = asdict(self)
        data["extraction_method"] = self.extraction_method.value
        data["status"] = self.status.value
        return data


@dataclass
class DocumentExtractionResult:
    """Provenance-preserving extraction result for an entire document."""
    document_id: str
    filename: str
    file_type: DocumentFormat
    total_pages: int
    pages: List[PageExtractionResult]
    full_raw_text: str
    full_normalized_text: str
    primary_extraction_method: ExtractionMethod
    overall_status: ExtractionStatus
    is_scanned: bool
    metadata: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert document result to JSON-serializable dictionary."""
        data = asdict(self)
        data["file_type"] = self.file_type.value
        data["primary_extraction_method"] = self.primary_extraction_method.value
        data["overall_status"] = self.overall_status.value
        data["pages"] = [p.to_dict() for p in self.pages]
        return data


# ==============================================================================
# FORMAT DETECTION & ENVIRONMENT CHECKS
# ==============================================================================

def detect_document_format(
    source: Union[str, Path, bytes, io.BytesIO],
    filename: Optional[str] = None,
) -> DocumentFormat:
    """
    Detect document format using magic bytes first, falling back to file extension.

    Parameters
    ----------
    source : Union[str, Path, bytes, io.BytesIO]
        File path, raw bytes, or BytesIO stream.
    filename : Optional[str]
        Optional filename hint when source is raw bytes.

    Returns
    -------
    DocumentFormat
        Detected format enum (PDF, PNG, JPEG, or UNSUPPORTED).
    """
    header = b""

    if isinstance(source, (str, Path)):
        p = Path(source)
        if p.is_file() and p.stat().st_size >= 4:
            try:
                with open(p, "rb") as f:
                    header = f.read(16)
            except OSError:
                pass
        if not filename:
            filename = p.name

    elif isinstance(source, bytes):
        header = source[:16]

    elif isinstance(source, io.BytesIO):
        pos = source.tell()
        header = source.read(16)
        source.seek(pos)

    # Magic byte matching
    if header.startswith(_MAGIC_PDF):
        return DocumentFormat.PDF
    if header.startswith(_MAGIC_PNG):
        return DocumentFormat.PNG
    if header.startswith(_MAGIC_JPEG):
        return DocumentFormat.JPEG

    # Fallback to extension
    if filename:
        ext = Path(filename).suffix.lower()
        if ext in _EXTENSION_FORMAT_MAP:
            return _EXTENSION_FORMAT_MAP[ext]

    return DocumentFormat.UNSUPPORTED


def is_ocr_available() -> bool:
    """
    Check whether an OCR engine (Tesseract) is available in the environment.

    Returns
    -------
    bool
        True if pytesseract is installed and tesseract executable is found.
    """
    if not _PYTESSERACT_AVAILABLE:
        return False

    # Check custom tesseract_cmd if configured
    try:
        custom_cmd = getattr(pytesseract.pytesseract, "tesseract_cmd", "tesseract")
        if custom_cmd and custom_cmd != "tesseract" and os.path.isfile(custom_cmd):
            return True
    except Exception:
        pass

    # Check PATH
    return shutil.which("tesseract") is not None


def get_ocr_engine_info() -> Dict[str, Any]:
    """
    Return telemetry and configuration details for the active OCR engine.

    Returns
    -------
    Dict[str, Any]
        Dictionary with OCR availability, engine name, version, and path.
    """
    available = is_ocr_available()
    tesseract_path = None
    version = None

    if available:
        try:
            tesseract_path = getattr(
                pytesseract.pytesseract, "tesseract_cmd", shutil.which("tesseract")
            )
            version = str(pytesseract.get_tesseract_version())
        except Exception:
            pass

    return {
        "pytesseract_installed": _PYTESSERACT_AVAILABLE,
        "ocr_available": available,
        "engine": "tesseract" if available else None,
        "executable_path": tesseract_path,
        "engine_version": version,
    }


# ==============================================================================
# TEXT NORMALIZATION FOR EXTRACTED TEXT
# ==============================================================================

def normalize_extracted_text(text: str) -> str:
    """
    Clean and standardize extracted document text.

    Applies Unicode NFKC normalization, strips non-printable control characters,
    standardizes whitespace, and strips outer whitespace while preserving word
    boundaries.
    """
    if not text:
        return ""
    text_uni = normalize_unicode(text)
    # Filter out control characters except newlines and tabs
    clean_chars = [
        c for c in text_uni if c == "\n" or c == "\t" or (ord(c) >= 32 and ord(c) != 127)
    ]
    cleaned = "".join(clean_chars)
    return normalize_whitespace(cleaned)


# ==============================================================================
# METRICS & EVALUATION HELPERS
# ==============================================================================

def compute_levenshtein_distance(seq1: Sequence[Any], seq2: Sequence[Any]) -> int:
    """
    Compute exact Levenshtein edit distance between two sequences (characters or words).
    """
    m, n = len(seq1), len(seq2)
    if m == 0:
        return n
    if n == 0:
        return m

    # Use single row DP for memory efficiency
    prev = list(range(n + 1))
    current = [0] * (n + 1)

    for i in range(1, m + 1):
        current[0] = i
        for j in range(1, n + 1):
            cost = 0 if seq1[i - 1] == seq2[j - 1] else 1
            current[j] = min(
                prev[j] + 1,        # deletion
                current[j - 1] + 1,  # insertion
                prev[j - 1] + cost   # substitution
            )
        prev = list(current)

    return current[n]


def compute_ocr_metrics(ground_truth: str, hypothesis: str) -> Dict[str, float]:
    """
    Compute Character Error Rate (CER), Word Error Rate (WER), and word token F1.

    Parameters
    ----------
    ground_truth : str
        The true expected reference text.
    hypothesis : str
        The text produced by extraction/OCR.

    Returns
    -------
    Dict[str, float]
        Dictionary with 'cer', 'wer', 'word_precision', 'word_recall', 'word_f1'.
    """
    gt_norm = normalize_extracted_text(ground_truth)
    hyp_norm = normalize_extracted_text(hypothesis)

    # Character Error Rate
    gt_chars = list(gt_norm)
    hyp_chars = list(hyp_norm)
    char_dist = compute_levenshtein_distance(gt_chars, hyp_chars)
    cer = char_dist / max(len(gt_chars), 1)

    # Word Error Rate
    gt_words = gt_norm.split()
    hyp_words = hyp_norm.split()
    word_dist = compute_levenshtein_distance(gt_words, hyp_words)
    wer = word_dist / max(len(gt_words), 1)

    # Token overlap F1
    gt_set = set(gt_words)
    hyp_set = set(hyp_words)
    intersection = len(gt_set.intersection(hyp_set))

    precision = intersection / max(len(hyp_set), 1)
    recall = intersection / max(len(gt_set), 1)
    f1 = (2 * precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return {
        "cer": round(cer, 4),
        "wer": round(wer, 4),
        "word_precision": round(precision, 4),
        "word_recall": round(recall, 4),
        "word_f1": round(f1, 4),
    }


# ==============================================================================
# PDF EXTRACTION
# ==============================================================================

def extract_text_from_pdf(
    source: Union[str, Path, bytes, io.BytesIO],
    document_id: Optional[str] = None,
    filename: Optional[str] = None,
    ocr_fallback: bool = True,
    min_char_threshold: int = 20,
    ocr_callable: Optional[Callable[[Image.Image], str]] = None,
) -> DocumentExtractionResult:
    """
    Extract text and provenance from a PDF document.

    Follows a two-stage extraction strategy:
    1. Native PDF text extraction per page via pypdf.
    2. If a page yields fewer than `min_char_threshold` characters and contains
       embedded images, it triggers OCR fallback (if available or provided).

    Parameters
    ----------
    source : Union[str, Path, bytes, io.BytesIO]
        File path, raw bytes, or stream.
    document_id : Optional[str]
        Auditable document ID. Auto-generated if omitted.
    filename : Optional[str]
        Original filename. Inferred from path if omitted.
    ocr_fallback : bool
        Whether to attempt OCR fallback when native text is sparse or missing.
    min_char_threshold : int
        Minimum characters required to accept native text without OCR fallback.
    ocr_callable : Optional[Callable[[Image.Image], str]]
        Optional injected OCR callable (e.g., for mock/evaluation testing).

    Returns
    -------
    DocumentExtractionResult
        Comprehensive extraction result with page-level provenance.
    """
    if document_id is None:
        document_id = f"DOC-{uuid.uuid4().hex[:8].upper()}"

    # Determine filename
    if filename is None:
        if isinstance(source, (str, Path)):
            filename = Path(source).name
        else:
            filename = f"{document_id}.pdf"

    # Prepare stream
    file_bytes: Optional[bytes] = None
    stream: io.BytesIO

    if isinstance(source, (str, Path)):
        p = Path(source)
        if not p.exists():
            return DocumentExtractionResult(
                document_id=document_id,
                filename=filename,
                file_type=DocumentFormat.PDF,
                total_pages=0,
                pages=[],
                full_raw_text="",
                full_normalized_text="",
                primary_extraction_method=ExtractionMethod.NONE,
                overall_status=ExtractionStatus.FILE_NOT_FOUND,
                is_scanned=False,
                warnings=[f"File not found: {p}"],
            )
        try:
            file_bytes = p.read_bytes()
        except OSError as e:
            return DocumentExtractionResult(
                document_id=document_id,
                filename=filename,
                file_type=DocumentFormat.PDF,
                total_pages=0,
                pages=[],
                full_raw_text="",
                full_normalized_text="",
                primary_extraction_method=ExtractionMethod.NONE,
                overall_status=ExtractionStatus.CORRUPTED_FILE,
                is_scanned=False,
                warnings=[f"Failed to read file: {e}"],
            )
    elif isinstance(source, bytes):
        file_bytes = source
    elif isinstance(source, io.BytesIO):
        pos = source.tell()
        file_bytes = source.read()
        source.seek(pos)

    # Empty document check
    if not file_bytes or len(file_bytes) == 0:
        return DocumentExtractionResult(
            document_id=document_id,
            filename=filename,
            file_type=DocumentFormat.PDF,
            total_pages=0,
            pages=[],
            full_raw_text="",
            full_normalized_text="",
            primary_extraction_method=ExtractionMethod.NONE,
            overall_status=ExtractionStatus.EMPTY_DOCUMENT,
            is_scanned=False,
            warnings=["Document is empty (0 bytes)."],
        )

    # Header sanity check
    if not file_bytes.startswith(b"%PDF-"):
        return DocumentExtractionResult(
            document_id=document_id,
            filename=filename,
            file_type=DocumentFormat.PDF,
            total_pages=0,
            pages=[],
            full_raw_text="",
            full_normalized_text="",
            primary_extraction_method=ExtractionMethod.NONE,
            overall_status=ExtractionStatus.CORRUPTED_FILE,
            is_scanned=False,
            warnings=["Missing or corrupted '%PDF-' header magic bytes."],
        )

    if not _PYPDF_AVAILABLE:  # pragma: no cover
        return DocumentExtractionResult(
            document_id=document_id,
            filename=filename,
            file_type=DocumentFormat.PDF,
            total_pages=0,
            pages=[],
            full_raw_text="",
            full_normalized_text="",
            primary_extraction_method=ExtractionMethod.NONE,
            overall_status=ExtractionStatus.CORRUPTED_FILE,
            is_scanned=False,
            warnings=["pypdf library is not installed."],
        )

    # Read PDF
    try:
        reader = pypdf.PdfReader(io.BytesIO(file_bytes))
        total_pages = len(reader.pages)
    except Exception as e:
        return DocumentExtractionResult(
            document_id=document_id,
            filename=filename,
            file_type=DocumentFormat.PDF,
            total_pages=0,
            pages=[],
            full_raw_text="",
            full_normalized_text="",
            primary_extraction_method=ExtractionMethod.NONE,
            overall_status=ExtractionStatus.CORRUPTED_FILE,
            is_scanned=False,
            warnings=[f"pypdf encountered parsing error: {e}"],
        )

    # Metadata extraction
    doc_metadata: Dict[str, Any] = {
        "file_size_bytes": len(file_bytes),
        "total_pages": total_pages,
    }
    if reader.metadata:
        try:
            for k, v in reader.metadata.items():
                clean_k = str(k).lstrip("/").lower()
                doc_metadata[clean_k] = str(v) if v is not None else None
        except Exception:
            pass

    # Extract pages
    page_results: List[PageExtractionResult] = []
    doc_warnings: List[str] = []
    any_scanned = False
    used_methods: set[ExtractionMethod] = set()

    ocr_available = is_ocr_available() or (ocr_callable is not None)

    for idx, page in enumerate(reader.pages):
        page_num = idx + 1
        page_warnings: List[str] = []
        page_meta: Dict[str, Any] = {}

        # 1. Native text extraction
        native_text = ""
        try:
            extracted = page.extract_text()
            if extracted:
                native_text = extracted
        except Exception as e:
            page_warnings.append(f"Native extraction error: {e}")

        clean_native = native_text.strip()
        num_native_chars = len(clean_native)

        # Inspect embedded images
        num_images = 0
        try:
            num_images = len(page.images)
        except Exception:
            pass
        page_meta["embedded_images_count"] = num_images

        # Check if native text is sufficient
        if num_native_chars >= min_char_threshold:
            norm_text = normalize_extracted_text(native_text)
            page_results.append(
                PageExtractionResult(
                    page_number=page_num,
                    raw_text=native_text,
                    normalized_text=norm_text,
                    extraction_method=ExtractionMethod.NATIVE_PDF,
                    status=ExtractionStatus.SUCCESS,
                    char_count=len(norm_text),
                    word_count=len(norm_text.split()),
                    warnings=page_warnings,
                    metadata=page_meta,
                )
            )
            used_methods.add(ExtractionMethod.NATIVE_PDF)
            continue

        # Text is sparse or empty; check for OCR fallback
        is_page_scanned = num_images > 0
        if is_page_scanned:
            any_scanned = True

        if ocr_fallback and is_page_scanned:
            if not ocr_available:
                # OCR requested but engine missing
                warn = "OCR fallback requested for scanned page, but OCR engine is unavailable."
                page_warnings.append(warn)
                doc_warnings.append(f"Page {page_num}: {warn}")
                norm_text = normalize_extracted_text(native_text)
                page_results.append(
                    PageExtractionResult(
                        page_number=page_num,
                        raw_text=native_text,
                        normalized_text=norm_text,
                        extraction_method=ExtractionMethod.NONE,
                        status=ExtractionStatus.OCR_UNAVAILABLE,
                        char_count=len(norm_text),
                        word_count=len(norm_text.split()),
                        warnings=page_warnings,
                        metadata=page_meta,
                    )
                )
                used_methods.add(ExtractionMethod.NONE)
                continue

            # Run OCR on embedded images
            ocr_text_parts: List[str] = []
            try:
                for img_idx, img_obj in enumerate(page.images):
                    pil_img = Image.open(io.BytesIO(img_obj.data))
                    if ocr_callable is not None:
                        img_text = ocr_callable(pil_img)
                    else:
                        img_text = pytesseract.image_to_string(pil_img)
                    if img_text:
                        ocr_text_parts.append(img_text)
            except Exception as e:
                page_warnings.append(f"OCR execution failed on page {page_num}: {e}")

            ocr_raw_text = "\n".join(ocr_text_parts).strip()
            if ocr_raw_text:
                norm_ocr = normalize_extracted_text(ocr_raw_text)
                page_results.append(
                    PageExtractionResult(
                        page_number=page_num,
                        raw_text=ocr_raw_text,
                        normalized_text=norm_ocr,
                        extraction_method=ExtractionMethod.OCR,
                        status=ExtractionStatus.OCR_FALLBACK_APPLIED,
                        char_count=len(norm_ocr),
                        word_count=len(norm_ocr.split()),
                        warnings=page_warnings,
                        metadata=page_meta,
                    )
                )
                used_methods.add(ExtractionMethod.OCR)
            else:
                # Scanned image with no readable text
                norm_text = normalize_extracted_text(native_text)
                page_results.append(
                    PageExtractionResult(
                        page_number=page_num,
                        raw_text=native_text,
                        normalized_text=norm_text,
                        extraction_method=ExtractionMethod.OCR,
                        status=ExtractionStatus.EMPTY_DOCUMENT,
                        char_count=len(norm_text),
                        word_count=len(norm_text.split()),
                        warnings=page_warnings + ["OCR found no legible text in page images."],
                        metadata=page_meta,
                    )
                )
                used_methods.add(ExtractionMethod.OCR)

        else:
            # Native text was below threshold and either not scanned or ocr_fallback is False
            status = ExtractionStatus.SUCCESS if num_native_chars > 0 else ExtractionStatus.EMPTY_DOCUMENT
            norm_text = normalize_extracted_text(native_text)
            page_results.append(
                PageExtractionResult(
                    page_number=page_num,
                    raw_text=native_text,
                    normalized_text=norm_text,
                    extraction_method=ExtractionMethod.NATIVE_PDF if num_native_chars > 0 else ExtractionMethod.NONE,
                    status=status,
                    char_count=len(norm_text),
                    word_count=len(norm_text.split()),
                    warnings=page_warnings,
                    metadata=page_meta,
                )
            )
            used_methods.add(ExtractionMethod.NATIVE_PDF if num_native_chars > 0 else ExtractionMethod.NONE)

    # Determine full document texts
    full_raw_parts = [p.raw_text for p in page_results if p.raw_text]
    full_norm_parts = [p.normalized_text for p in page_results if p.normalized_text]

    full_raw = "\n\n".join(full_raw_parts)
    full_norm = "\n\n".join(full_norm_parts)

    # Determine primary extraction method
    active_methods = {p.extraction_method for p in page_results if p.extraction_method != ExtractionMethod.NONE}
    if len(active_methods) > 1:
        primary_method = ExtractionMethod.HYBRID
    elif len(active_methods) == 1:
        primary_method = next(iter(active_methods))
    else:
        primary_method = ExtractionMethod.NONE

    # Determine overall status
    page_statuses = [p.status for p in page_results]
    if not page_statuses or all(s == ExtractionStatus.EMPTY_DOCUMENT for s in page_statuses):
        overall_status = ExtractionStatus.EMPTY_DOCUMENT
    elif all(s == ExtractionStatus.SUCCESS for s in page_statuses):
        overall_status = ExtractionStatus.SUCCESS
    elif all(s in (ExtractionStatus.SUCCESS, ExtractionStatus.OCR_FALLBACK_APPLIED) for s in page_statuses):
        if any(s == ExtractionStatus.OCR_FALLBACK_APPLIED for s in page_statuses):
            overall_status = ExtractionStatus.OCR_FALLBACK_APPLIED
        else:
            overall_status = ExtractionStatus.SUCCESS
    elif any(s == ExtractionStatus.OCR_UNAVAILABLE for s in page_statuses):
        overall_status = ExtractionStatus.OCR_UNAVAILABLE
    elif any(s in (ExtractionStatus.SUCCESS, ExtractionStatus.OCR_FALLBACK_APPLIED) for s in page_statuses):
        overall_status = ExtractionStatus.PARTIAL_SUCCESS
    else:
        overall_status = ExtractionStatus.EMPTY_DOCUMENT

    return DocumentExtractionResult(
        document_id=document_id,
        filename=filename,
        file_type=DocumentFormat.PDF,
        total_pages=total_pages,
        pages=page_results,
        full_raw_text=full_raw,
        full_normalized_text=full_norm,
        primary_extraction_method=primary_method,
        overall_status=overall_status,
        is_scanned=any_scanned,
        metadata=doc_metadata,
        warnings=doc_warnings,
    )


# ==============================================================================
# IMAGE EXTRACTION (PNG / JPEG)
# ==============================================================================

def extract_text_from_image(
    source: Union[str, Path, bytes, io.BytesIO],
    document_id: Optional[str] = None,
    filename: Optional[str] = None,
    ocr_callable: Optional[Callable[[Image.Image], str]] = None,
) -> DocumentExtractionResult:
    """
    Extract text and provenance from a visual certificate image (PNG or JPEG).

    Parameters
    ----------
    source : Union[str, Path, bytes, io.BytesIO]
        File path, raw bytes, or stream.
    document_id : Optional[str]
        Auditable document ID. Auto-generated if omitted.
    filename : Optional[str]
        Original filename. Inferred from path if omitted.
    ocr_callable : Optional[Callable[[Image.Image], str]]
        Optional injected OCR callable (e.g., for mock/evaluation testing).

    Returns
    -------
    DocumentExtractionResult
        Extraction result with image dimensions and OCR provenance.
    """
    if document_id is None:
        document_id = f"DOC-{uuid.uuid4().hex[:8].upper()}"

    # Determine filename and path
    if filename is None:
        if isinstance(source, (str, Path)):
            filename = Path(source).name
        else:
            filename = f"{document_id}.img"

    # Read bytes
    file_bytes: Optional[bytes] = None
    if isinstance(source, (str, Path)):
        p = Path(source)
        if not p.exists():
            return DocumentExtractionResult(
                document_id=document_id,
                filename=filename,
                file_type=DocumentFormat.UNSUPPORTED,
                total_pages=0,
                pages=[],
                full_raw_text="",
                full_normalized_text="",
                primary_extraction_method=ExtractionMethod.NONE,
                overall_status=ExtractionStatus.FILE_NOT_FOUND,
                is_scanned=True,
                warnings=[f"File not found: {p}"],
            )
        try:
            file_bytes = p.read_bytes()
        except OSError as e:
            return DocumentExtractionResult(
                document_id=document_id,
                filename=filename,
                file_type=DocumentFormat.UNSUPPORTED,
                total_pages=0,
                pages=[],
                full_raw_text="",
                full_normalized_text="",
                primary_extraction_method=ExtractionMethod.NONE,
                overall_status=ExtractionStatus.CORRUPTED_FILE,
                is_scanned=True,
                warnings=[f"Failed to read image file: {e}"],
            )
    elif isinstance(source, bytes):
        file_bytes = source
    elif isinstance(source, io.BytesIO):
        pos = source.tell()
        file_bytes = source.read()
        source.seek(pos)

    # Empty file check
    if not file_bytes or len(file_bytes) == 0:
        return DocumentExtractionResult(
            document_id=document_id,
            filename=filename,
            file_type=DocumentFormat.UNSUPPORTED,
            total_pages=0,
            pages=[],
            full_raw_text="",
            full_normalized_text="",
            primary_extraction_method=ExtractionMethod.NONE,
            overall_status=ExtractionStatus.EMPTY_DOCUMENT,
            is_scanned=True,
            warnings=["Image file is empty (0 bytes)."],
        )

    # Open image via PIL
    try:
        pil_img = Image.open(io.BytesIO(file_bytes))
        pil_img.load()
    except Exception as e:
        return DocumentExtractionResult(
            document_id=document_id,
            filename=filename,
            file_type=DocumentFormat.UNSUPPORTED,
            total_pages=0,
            pages=[],
            full_raw_text="",
            full_normalized_text="",
            primary_extraction_method=ExtractionMethod.NONE,
            overall_status=ExtractionStatus.CORRUPTED_FILE,
            is_scanned=True,
            warnings=[f"Image decode failed: {e}"],
        )

    # Classify format
    img_fmt = (pil_img.format or "").upper()
    if img_fmt == "PNG":
        doc_format = DocumentFormat.PNG
    elif img_fmt in ("JPEG", "JPG"):
        doc_format = DocumentFormat.JPEG
    else:
        doc_format = DocumentFormat.UNSUPPORTED

    img_metadata = {
        "width": pil_img.width,
        "height": pil_img.height,
        "mode": pil_img.mode,
        "format": img_fmt,
        "file_size_bytes": len(file_bytes),
    }

    # Check OCR availability
    ocr_available = is_ocr_available() or (ocr_callable is not None)
    if not ocr_available:
        warning_msg = "OCR engine is unavailable on this environment. Image cannot be transcribed."
        page_res = PageExtractionResult(
            page_number=1,
            raw_text="",
            normalized_text="",
            extraction_method=ExtractionMethod.NONE,
            status=ExtractionStatus.OCR_UNAVAILABLE,
            char_count=0,
            word_count=0,
            warnings=[warning_msg],
            metadata=img_metadata,
        )
        return DocumentExtractionResult(
            document_id=document_id,
            filename=filename,
            file_type=doc_format,
            total_pages=1,
            pages=[page_res],
            full_raw_text="",
            full_normalized_text="",
            primary_extraction_method=ExtractionMethod.NONE,
            overall_status=ExtractionStatus.OCR_UNAVAILABLE,
            is_scanned=True,
            metadata=img_metadata,
            warnings=[warning_msg],
        )

    # Run OCR
    raw_ocr = ""
    warnings: List[str] = []
    try:
        if ocr_callable is not None:
            raw_ocr = ocr_callable(pil_img) or ""
        else:
            raw_ocr = pytesseract.image_to_string(pil_img) or ""
    except Exception as e:
        warnings.append(f"OCR execution failed: {e}")

    raw_ocr = raw_ocr.strip()
    norm_ocr = normalize_extracted_text(raw_ocr)

    status = ExtractionStatus.SUCCESS if raw_ocr else ExtractionStatus.EMPTY_DOCUMENT
    method = ExtractionMethod.OCR if raw_ocr else ExtractionMethod.NONE

    page_res = PageExtractionResult(
        page_number=1,
        raw_text=raw_ocr,
        normalized_text=norm_ocr,
        extraction_method=method,
        status=status,
        char_count=len(norm_ocr),
        word_count=len(norm_ocr.split()),
        warnings=warnings,
        metadata=img_metadata,
    )

    return DocumentExtractionResult(
        document_id=document_id,
        filename=filename,
        file_type=doc_format,
        total_pages=1,
        pages=[page_res],
        full_raw_text=raw_ocr,
        full_normalized_text=norm_ocr,
        primary_extraction_method=method,
        overall_status=status,
        is_scanned=True,
        metadata=img_metadata,
        warnings=warnings,
    )


# ==============================================================================
# UNIFIED INGESTION INTERFACE
# ==============================================================================

def ingest_document(
    file_path: Union[str, Path],
    document_id: Optional[str] = None,
    ocr_fallback: bool = True,
    ocr_callable: Optional[Callable[[Image.Image], str]] = None,
) -> DocumentExtractionResult:
    """
    Ingest and transcribe an evidence document (PDF, PNG, or JPEG).

    Validates file existence, determines format, dispatches to the appropriate
    extractor, and returns an auditable DocumentExtractionResult.

    Parameters
    ----------
    file_path : Union[str, Path]
        Path to the evidence document.
    document_id : Optional[str]
        Auditable document ID. Auto-generated if omitted.
    ocr_fallback : bool
        Whether to attempt OCR fallback for scanned PDF pages.
    ocr_callable : Optional[Callable[[Image.Image], str]]
        Optional injected OCR callable (e.g., for mock/evaluation testing).

    Returns
    -------
    DocumentExtractionResult
        Standardized extraction result.
    """
    if file_path is None:
        raise ValueError("file_path cannot be None")

    p = Path(file_path)
    if document_id is None:
        document_id = f"DOC-{uuid.uuid4().hex[:8].upper()}"

    if not p.exists():
        return DocumentExtractionResult(
            document_id=document_id,
            filename=p.name,
            file_type=DocumentFormat.UNSUPPORTED,
            total_pages=0,
            pages=[],
            full_raw_text="",
            full_normalized_text="",
            primary_extraction_method=ExtractionMethod.NONE,
            overall_status=ExtractionStatus.FILE_NOT_FOUND,
            is_scanned=False,
            warnings=[f"File does not exist: {p}"],
        )

    # Check 0-byte file
    try:
        size = p.stat().st_size
    except OSError as e:
        return DocumentExtractionResult(
            document_id=document_id,
            filename=p.name,
            file_type=DocumentFormat.UNSUPPORTED,
            total_pages=0,
            pages=[],
            full_raw_text="",
            full_normalized_text="",
            primary_extraction_method=ExtractionMethod.NONE,
            overall_status=ExtractionStatus.CORRUPTED_FILE,
            is_scanned=False,
            warnings=[f"Failed to access file metadata: {e}"],
        )

    if size == 0:
        return DocumentExtractionResult(
            document_id=document_id,
            filename=p.name,
            file_type=DocumentFormat.UNSUPPORTED,
            total_pages=0,
            pages=[],
            full_raw_text="",
            full_normalized_text="",
            primary_extraction_method=ExtractionMethod.NONE,
            overall_status=ExtractionStatus.EMPTY_DOCUMENT,
            is_scanned=False,
            warnings=["File is empty (0 bytes)."],
        )

    fmt = detect_document_format(p)

    if fmt == DocumentFormat.PDF:
        return extract_text_from_pdf(
            source=p,
            document_id=document_id,
            filename=p.name,
            ocr_fallback=ocr_fallback,
            ocr_callable=ocr_callable,
        )

    if fmt in (DocumentFormat.PNG, DocumentFormat.JPEG):
        return extract_text_from_image(
            source=p,
            document_id=document_id,
            filename=p.name,
            ocr_callable=ocr_callable,
        )

    # Unsupported format (.docx, .zip, .txt, etc.)
    return DocumentExtractionResult(
        document_id=document_id,
        filename=p.name,
        file_type=DocumentFormat.UNSUPPORTED,
        total_pages=0,
        pages=[],
        full_raw_text="",
        full_normalized_text="",
        primary_extraction_method=ExtractionMethod.NONE,
        overall_status=ExtractionStatus.UNSUPPORTED_FORMAT,
        is_scanned=False,
        metadata={"file_size_bytes": size, "extension": p.suffix.lower()},
        warnings=[f"Unsupported evidence document format '{p.suffix}'. Supported: .pdf, .png, .jpg, .jpeg"],
    )


def batch_ingest_documents(
    file_paths: Sequence[Union[str, Path]],
    ocr_fallback: bool = True,
    ocr_callable: Optional[Callable[[Image.Image], str]] = None,
) -> List[DocumentExtractionResult]:
    """
    Batch ingest multiple evidence documents.

    Parameters
    ----------
    file_paths : Sequence[Union[str, Path]]
        Collection of file paths.
    ocr_fallback : bool
        Whether to attempt OCR fallback for scanned pages.
    ocr_callable : Optional[Callable[[Image.Image], str]]
        Optional injected OCR callable.

    Returns
    -------
    List[DocumentExtractionResult]
        Ordered list of document extraction results.
    """
    results: List[DocumentExtractionResult] = []
    for fp in file_paths:
        res = ingest_document(
            file_path=fp,
            ocr_fallback=ocr_fallback,
            ocr_callable=ocr_callable,
        )
        results.append(res)
    return results

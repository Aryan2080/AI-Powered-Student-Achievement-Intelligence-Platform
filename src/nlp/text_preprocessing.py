"""
text_preprocessing.py
=====================
Production-Grade Task-Specific Text Preprocessing Pipeline
AI-Powered Student Achievement Intelligence Platform — Member 1

This module provides dedicated, decoupled preprocessing architectures for:
  1. Achievement Classification (Unicode + Whitespace + Lowercase + Tokenization)
  2. Skill Extraction (Strict Original Text & Character Offset Preservation)
  3. Sentence Transformer Embeddings (Natural Syntax, Proper Casing & Punctuation)
  4. Duplicate Detection (Identity & Entity Preservation: dates, ranks, organizations)

Guarantees:
  - Original text fields are NEVER mutated in-place.
  - Deterministic and reproducible across all platforms.
  - Full type safety, input validation, and informative diagnostics.
"""
from __future__ import annotations

import re
import unicodedata
from typing import Any, Literal

import pandas as pd

# Standard regex for whitespace collapsing: handles spaces, tabs, newlines, carriage returns,
# non-breaking spaces (\u00A0), and zero-width spaces (\u200B).
_WHITESPACE_RE = re.compile(r"[\s\u00A0\u200B\u200E\u200F\uFEFF]+", re.UNICODE)

# Basic word tokenization pattern preserving hyphenated technical compounds and acronyms
_TOKEN_PATTERN = re.compile(r"(?u)\b\w+(?:[-/]\w+)*\b")

# Standard English stop words curated for achievement text (preserves negation words like 'not', 'without')
STANDARD_STOPWORDS = frozenset({
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and",
    "any", "are", "as", "at", "be", "because", "been", "before", "being", "below",
    "between", "both", "by", "could", "did", "do", "does", "doing", "down", "during",
    "each", "few", "for", "from", "further", "had", "has", "have", "having", "he",
    "her", "here", "hers", "herself", "him", "himself", "his", "how", "i", "if",
    "in", "into", "is", "it", "its", "itself", "me", "more", "most", "my", "myself",
    "no", "nor", "of", "off", "on", "once", "only", "or", "other", "ought", "our",
    "ours", "ourselves", "out", "over", "own", "same", "she", "should", "so", "some",
    "such", "than", "that", "the", "their", "theirs", "them", "themselves", "then",
    "there", "these", "they", "this", "those", "through", "to", "too", "under", "until",
    "up", "very", "was", "we", "were", "what", "when", "where", "which", "while",
    "who", "whom", "why", "with", "would", "you", "your", "yours", "yourself", "yourselves"
})


def normalize_unicode(text: str, form: Literal["NFC", "NFD", "NFKC", "NFKD"] = "NFC") -> str:
    """Normalize Unicode characters to a standard form.

    Args:
        text: Input string to normalize.
        form: Canonical normalization form ('NFC', 'NFD', 'NFKC', 'NFKD'). Default is 'NFC'.

    Returns:
        Unicode-normalized string.

    Raises:
        TypeError: If text is not a string.
        ValueError: If form is not a valid Unicode normalization form.
    """
    if not isinstance(text, str):
        raise TypeError(f"Expected str for 'text', received {type(text).__name__}")
    if form not in ("NFC", "NFD", "NFKC", "NFKD"):
        raise ValueError(f"Invalid Unicode normalization form '{form}'. Expected one of ('NFC', 'NFD', 'NFKC', 'NFKD').")
    return unicodedata.normalize(form, text)


def normalize_whitespace(text: str) -> str:
    """Collapse consecutive whitespace, tabs, and newlines into a single space and strip boundaries.

    Args:
        text: Input string to normalize.

    Returns:
        Stripped string with normalized interior single spaces.

    Raises:
        TypeError: If text is not a string.
    """
    if not isinstance(text, str):
        raise TypeError(f"Expected str for 'text', received {type(text).__name__}")
    return _WHITESPACE_RE.sub(" ", text).strip()


def normalize_text_for_classification(
    text: str,
    lowercase: bool = True,
    remove_punctuation: bool = False,
    unicode_form: Literal["NFC", "NFKC"] = "NFC"
) -> str:
    """Task A: Preprocess text specifically for supervised achievement classification.

    Applies Unicode normalization, whitespace collapsing, and optional casing/punctuation filtering.
    Preserves numerical entities, ranks, dates, and technical abbreviations.

    Args:
        text: Raw achievement text.
        lowercase: Whether to convert text to lowercase (standard for TF-IDF/Linear baselines).
        remove_punctuation: Whether to strip non-alphanumeric punctuation characters.
        unicode_form: Unicode normalization form to apply (default 'NFC').

    Returns:
        Preprocessed text ready for feature extraction.
    """
    if not isinstance(text, str):
        raise TypeError(f"Expected str for 'text', received {type(text).__name__}")
    
    # 1. Unicode Normalization
    norm = normalize_unicode(text, form=unicode_form)
    
    # 2. Whitespace Collapsing
    norm = normalize_whitespace(norm)
    
    # 3. Optional Punctuation Removal
    if remove_punctuation:
        # Keep alphanumeric characters, spaces, and hyphens
        norm = re.sub(r"[^\w\s-]", " ", norm)
        norm = normalize_whitespace(norm)
        
    # 4. Optional Lowercase
    if lowercase:
        norm = norm.lower()
        
    return norm


def prepare_text_for_skill_extraction(text: str) -> str:
    """Task B: Prepare text for skill extraction and named entity span verification.

    CRITICAL ARCHITECTURAL CONTRACT:
      Skill annotations rely on exact character offsets: text[start_offset:end_offset] == mention.
      This function validates input and returns the verbatim text representation,
      guaranteeing that character offsets are NEVER shifted or corrupted.

    Args:
        text: Original achievement text.

    Returns:
        Verbatim text string with verified integrity.

    Raises:
        TypeError: If text is not a string.
        ValueError: If text is empty or whitespace-only.
    """
    if not isinstance(text, str):
        raise TypeError(f"Expected str for 'text', received {type(text).__name__}")
    if not text.strip():
        raise ValueError("Skill extraction text cannot be empty or whitespace-only.")
    # Must preserve exact original character stream to guarantee span validity
    return text


def prepare_text_for_sentence_transformer(text: str) -> str:
    """Task C: Prepare text for Sentence Transformer bi-encoders.

    Pre-trained neural language models (e.g. all-MiniLM-L6-v2) rely on:
      - Natural grammatical syntax (periods, commas, sentence delimiters).
      - Original capitalization (distinguishes acronyms like 'AWS', 'IEEE' from common words).
      - Unicode consistency (NFC).

    This pipeline collapses irregular whitespace and normalizes Unicode while strictly
    preserving natural sentence structure and casing.

    Args:
        text: Raw achievement text.

    Returns:
        Model-compatible natural language string.
    """
    if not isinstance(text, str):
        raise TypeError(f"Expected str for 'text', received {type(text).__name__}")
    
    clean = normalize_unicode(text, form="NFC")
    clean = normalize_whitespace(clean)
    if not clean:
        raise ValueError("Sentence Transformer input text cannot be empty.")
    return clean


def prepare_text_for_duplicate_detection(
    text: str,
    preserve_numbers: bool = True
) -> str:
    """Task D: Preprocess text for duplicate detection and record matching.

    Normalizes Unicode and whitespace, and applies case folding.
    CRITICAL: Preserves numbers, ordinal suffixes (1st, 2nd), years, and event names
    so that distinct achievements differing only by edition or rank are NOT collapsed
    into false duplicates.

    Args:
        text: Raw achievement text.
        preserve_numbers: Whether to keep digits and numerical indicators intact (default True).

    Returns:
        Normalized text for duplicate pair evaluation.
    """
    if not isinstance(text, str):
        raise TypeError(f"Expected str for 'text', received {type(text).__name__}")
    
    # NFKC normalizes compatibility digits (e.g. full-width numerals) into ASCII digits
    norm = normalize_unicode(text, form="NFKC")
    norm = normalize_whitespace(norm)
    norm = norm.lower()
    
    if not preserve_numbers:
        # Replaces numbers with neutral placeholder token if requested
        norm = re.sub(r"\b\d+\b", "#NUM", norm)
        norm = normalize_whitespace(norm)
        
    return norm


def tokenize_words(
    text: str,
    lowercase: bool = False,
    remove_stopwords: bool = False,
    custom_stopwords: set[str] | frozenset[str] | None = None
) -> list[str]:
    """Tokenize text into words with optional casing and stopword filtering.

    Args:
        text: Input string.
        lowercase: Whether to convert tokens to lowercase.
        remove_stopwords: Whether to filter out stop words.
        custom_stopwords: Custom stop word set (defaults to STANDARD_STOPWORDS if None).

    Returns:
        List of extracted token strings.
    """
    if not isinstance(text, str):
        raise TypeError(f"Expected str for 'text', received {type(text).__name__}")
    
    tokens = _TOKEN_PATTERN.findall(text)
    if lowercase:
        tokens = [t.lower() for t in tokens]
        
    if remove_stopwords:
        sw = custom_stopwords if custom_stopwords is not None else STANDARD_STOPWORDS
        tokens = [t for t in tokens if t.lower() not in sw]
        
    return tokens


def preprocess_dataframe(
    df: pd.DataFrame,
    text_column: str = "achievement_text",
    task: Literal["classification", "skill_extraction", "sentence_transformer", "duplicate_detection"] = "classification",
    output_column: str | None = None
) -> pd.DataFrame:
    """Apply a task-specific preprocessing pipeline to a pandas DataFrame without mutating the original.

    Args:
        df: Input pandas DataFrame.
        text_column: Name of the column containing raw text. Default is 'achievement_text'.
        task: Target downstream task ('classification', 'skill_extraction', 'sentence_transformer', 'duplicate_detection').
        output_column: Column name to store processed text. Defaults to f"processed_{task}_text".

    Returns:
        A new DataFrame copy containing the processed text column.

    Raises:
        TypeError: If df is not a pandas DataFrame.
        KeyError: If text_column does not exist in df.
        ValueError: If task is not recognized.
    """
    if not isinstance(df, pd.DataFrame):
        raise TypeError(f"Expected pd.DataFrame, received {type(df).__name__}")
    if text_column not in df.columns:
        raise KeyError(f"Column '{text_column}' not found in DataFrame. Available columns: {list(df.columns)}")
        
    out_col = output_column or f"processed_{task}_text"
    result_df = df.copy()
    
    if task == "classification":
        result_df[out_col] = result_df[text_column].apply(normalize_text_for_classification)
    elif task == "skill_extraction":
        result_df[out_col] = result_df[text_column].apply(prepare_text_for_skill_extraction)
    elif task == "sentence_transformer":
        result_df[out_col] = result_df[text_column].apply(prepare_text_for_sentence_transformer)
    elif task == "duplicate_detection":
        result_df[out_col] = result_df[text_column].apply(prepare_text_for_duplicate_detection)
    else:
        raise ValueError(f"Unknown preprocessing task '{task}'. Expected one of ('classification', 'skill_extraction', 'sentence_transformer', 'duplicate_detection').")
        
    return result_df


def compare_preprocessing_outputs(original_text: str, processed_text: str) -> dict[str, Any]:
    """Perform side-by-side diagnostic comparison between original and processed text.

    Args:
        original_text: Raw text before preprocessing.
        processed_text: Text after preprocessing.

    Returns:
        Dictionary containing comparative length, word count, case, and change metrics.
    """
    if not isinstance(original_text, str) or not isinstance(processed_text, str):
        raise TypeError("Both 'original_text' and 'processed_text' must be str.")
        
    orig_len = len(original_text)
    proc_len = len(processed_text)
    
    orig_words = len(_TOKEN_PATTERN.findall(original_text))
    proc_words = len(_TOKEN_PATTERN.findall(processed_text))
    
    case_changed = (original_text.strip().lower() == processed_text.strip().lower()) and (original_text.strip() != processed_text.strip())
    whitespace_collapsed = (re.sub(r"\s+", " ", original_text).strip() != original_text) and (re.sub(r"\s+", " ", processed_text).strip() == processed_text)
    identical = (original_text == processed_text)
    
    return {
        "original_length": orig_len,
        "processed_length": proc_len,
        "length_difference": proc_len - orig_len,
        "original_words": orig_words,
        "processed_words": proc_words,
        "words_difference": proc_words - orig_words,
        "case_changed": case_changed,
        "whitespace_collapsed": whitespace_collapsed,
        "is_identical": identical,
    }

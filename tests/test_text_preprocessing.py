"""
test_text_preprocessing.py
==========================
Unit & Regression Tests for NLP Text Preprocessing Subsystem
AI-Powered Student Achievement Intelligence Platform — Member 1
"""
from __future__ import annotations

import pandas as pd
import pytest

from nlp.text_preprocessing import (
    compare_preprocessing_outputs,
    normalize_text_for_classification,
    normalize_unicode,
    normalize_whitespace,
    prepare_text_for_duplicate_detection,
    prepare_text_for_sentence_transformer,
    prepare_text_for_skill_extraction,
    preprocess_dataframe,
    tokenize_words,
)


class TestUnicodeNormalization:
    def test_unicode_ascii_passthrough(self):
        text = "Published a machine learning paper in IEEE."
        assert normalize_unicode(text, form="NFC") == text

    def test_unicode_accented_characters(self):
        # Combined vs decomposed
        decomposed = "cafe\u0301"
        composed = "caf\u00e9"
        assert normalize_unicode(decomposed, form="NFC") == composed

    def test_unicode_invalid_type_raises_typeerror(self):
        with pytest.raises(TypeError, match="Expected str"):
            normalize_unicode(12345)  # type: ignore

    def test_unicode_invalid_form_raises_valueerror(self):
        with pytest.raises(ValueError, match="Invalid Unicode normalization form"):
            normalize_unicode("hello", form="INVALID")  # type: ignore


class TestWhitespaceNormalization:
    def test_whitespace_collapsing(self):
        text = "  Led   a  3-person \t\t team\n\n across \r campus.  "
        expected = "Led a 3-person team across campus."
        assert normalize_whitespace(text) == expected

    def test_whitespace_unicode_spaces(self):
        # Non-breaking space \u00A0 and zero-width space \u200B
        text = "Smart\u00A0India\u200BHackathon  2024"
        assert normalize_whitespace(text) == "Smart India Hackathon 2024"

    def test_whitespace_invalid_type_raises_typeerror(self):
        with pytest.raises(TypeError):
            normalize_whitespace(None)  # type: ignore


class TestClassificationNormalization:
    def test_classification_lowercase_and_clean(self):
        raw = "  Won 1st Place in Smart India Hackathon (SIH 2023)!  "
        expected = "won 1st place in smart india hackathon (sih 2023)!"
        assert normalize_text_for_classification(raw, lowercase=True) == expected

    def test_classification_punctuation_removal_option(self):
        raw = "Secured 1st place at SIH-2023: developed ROS-2 robot!"
        cleaned = normalize_text_for_classification(raw, lowercase=True, remove_punctuation=True)
        assert ":" not in cleaned
        assert "!" not in cleaned
        assert "sih-2023" in cleaned or "sih 2023" in cleaned

    def test_classification_preserves_numbers_and_years(self):
        raw = "Completed 120 hours of community service in 2022."
        res = normalize_text_for_classification(raw)
        assert "120" in res
        assert "2022" in res


class TestSkillExtractionPreparation:
    def test_skill_extraction_verbatim_preservation(self):
        raw = "Engineered automated telemetry with Kubernetes and Apache Spark."
        prepared = prepare_text_for_skill_extraction(raw)
        assert prepared == raw
        # Test character offset span invariance
        mention = "Kubernetes"
        start = raw.index(mention)
        end = start + len(mention)
        assert prepared[start:end] == mention

    def test_skill_extraction_empty_raises_valueerror(self):
        with pytest.raises(ValueError, match="cannot be empty"):
            prepare_text_for_skill_extraction("   \n\t  ")

    def test_skill_extraction_invalid_type_raises_typeerror(self):
        with pytest.raises(TypeError):
            prepare_text_for_skill_extraction(None)  # type: ignore


class TestSentenceTransformerPreparation:
    def test_sentence_transformer_preserves_casing_and_punctuation(self):
        raw = "  Co-inventor on patent application #20241098 filed with EPO: 'Adaptive Impedance-Matching'.  "
        prepared = prepare_text_for_sentence_transformer(raw)
        assert prepared.startswith("Co-inventor")
        assert "EPO" in prepared  # Must keep acronym casing
        assert "Adaptive Impedance-Matching" in prepared
        assert prepared.endswith("'.")

    def test_sentence_transformer_empty_raises_valueerror(self):
        with pytest.raises(ValueError):
            prepare_text_for_sentence_transformer("   ")


class TestDuplicateDetectionPreparation:
    def test_duplicate_detection_preserves_distinct_numbers(self):
        text1 = "Won 1st place in the 2024 Robotics Challenge."
        text2 = "Won 2nd place in the 2025 Robotics Challenge."
        p1 = prepare_text_for_duplicate_detection(text1, preserve_numbers=True)
        p2 = prepare_text_for_duplicate_detection(text2, preserve_numbers=True)
        assert p1 != p2
        assert "1st" in p1 and "2nd" in p2
        assert "2024" in p1 and "2025" in p2


class TestTokenization:
    def test_word_tokenization_with_stopwords(self):
        text = "Spearheaded the design of an offline triage application."
        tokens = tokenize_words(text, lowercase=True, remove_stopwords=True)
        assert "the" not in tokens
        assert "of" not in tokens
        assert "an" not in tokens
        assert "spearheaded" in tokens
        assert "offline" in tokens
        assert "triage" in tokens


class TestDataframePreprocessing:
    def test_preprocess_dataframe_no_mutation(self):
        data = {
            "achievement_id": ["ACH000001", "ACH000002"],
            "achievement_text": ["  Won 1st Place!  ", "  Published paper in IEEE.  "]
        }
        df = pd.DataFrame(data)
        original_copy = df.copy()
        
        result_df = preprocess_dataframe(df, text_column="achievement_text", task="classification")
        
        # Verify original dataframe is unmodified
        pd.testing.assert_frame_equal(df, original_copy)
        assert "processed_classification_text" in result_df.columns
        assert result_df["processed_classification_text"].iloc[0] == "won 1st place!"

    def test_preprocess_dataframe_invalid_task_raises_valueerror(self):
        df = pd.DataFrame({"achievement_text": ["Sample text"]})
        with pytest.raises(ValueError, match="Unknown preprocessing task"):
            preprocess_dataframe(df, task="unsupported_task")  # type: ignore


class TestCompareOutputs:
    def test_compare_outputs_diagnostics(self):
        raw = "  Team Lead for SIH 2023!  "
        clean = "team lead for sih 2023!"
        diag = compare_preprocessing_outputs(raw, clean)
        assert diag["case_changed"] is True
        assert diag["whitespace_collapsed"] is True
        assert diag["is_identical"] is False
        assert diag["original_words"] == diag["processed_words"]

"""Tests for the Chunk 7.18 arXiv governance module.

Covers all four Mohan-revision requirements:
  Revision 1 — endpoint whitelist + /abs/ scraping prohibition
  Revision 2 — metadata-only record + forbidden content types
  Revision 3 — preprint status, withdrawals, student-attribution gates
  Revision 4 — acknowledgment, canonical links, email redaction
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from nlp_semantic.ingestion.arxiv_governance import (
    ARXIV_ACKNOWLEDGMENT,
    ARXIV_SOURCE_ID,
    CC0_LICENSE_URI,
    OFFICIAL_METADATA_ENDPOINTS,
    AbsScrapingProhibitedError,
    ArxivMetadataRecord,
    EndpointNotAllowedError,
    ForbiddenContentTypeError,
    MissingStudentVerificationError,
    PeerReviewStatus,
    StudentVerificationEvidence,
    assess_peer_review_status,
    authorize_student_link,
    canonical_abs_link,
    is_withdrawn,
    redact_contact_emails,
    reject_forbidden_content_type,
    validate_metadata_endpoint,
)


# ---- Revision 1 — endpoint validation ---------------------------------------


class TestEndpointValidation:
    def test_official_endpoints_whitelist_has_exact_two(self):
        assert set(OFFICIAL_METADATA_ENDPOINTS.keys()) == {
            "query_api", "oai_pmh",
        }
        assert OFFICIAL_METADATA_ENDPOINTS["query_api"] == (
            "https://export.arxiv.org/api/query"
        )
        assert OFFICIAL_METADATA_ENDPOINTS["oai_pmh"] == (
            "https://oaipmh.arxiv.org/oai"
        )

    def test_query_api_endpoint_accepted(self):
        v = validate_metadata_endpoint(
            "https://export.arxiv.org/api/query"
        )
        assert v == "https://export.arxiv.org/api/query"

    def test_query_api_endpoint_accepted_with_trailing_slash(self):
        v = validate_metadata_endpoint(
            "https://export.arxiv.org/api/query/"
        )
        assert "export.arxiv.org/api/query" in v

    def test_oai_pmh_endpoint_accepted(self):
        v = validate_metadata_endpoint("https://oaipmh.arxiv.org/oai")
        assert v == "https://oaipmh.arxiv.org/oai"

    def test_abs_path_rejected_on_arxiv_host(self):
        with pytest.raises(AbsScrapingProhibitedError):
            validate_metadata_endpoint(
                "https://arxiv.org/abs/2403.12345"
            )

    def test_abs_path_rejected_on_export_arxiv_host(self):
        with pytest.raises(AbsScrapingProhibitedError):
            validate_metadata_endpoint(
                "https://export.arxiv.org/abs/2403.12345"
            )

    def test_pdf_path_rejected(self):
        with pytest.raises(AbsScrapingProhibitedError):
            validate_metadata_endpoint(
                "https://arxiv.org/pdf/2403.12345.pdf"
            )

    def test_src_path_rejected(self):
        with pytest.raises(AbsScrapingProhibitedError):
            validate_metadata_endpoint(
                "https://arxiv.org/src/2403.12345"
            )

    def test_html_path_rejected(self):
        with pytest.raises(AbsScrapingProhibitedError):
            validate_metadata_endpoint(
                "https://arxiv.org/html/2403.12345"
            )

    def test_format_path_rejected(self):
        with pytest.raises(AbsScrapingProhibitedError):
            validate_metadata_endpoint(
                "https://arxiv.org/format/2403.12345"
            )

    def test_non_whitelist_arxiv_host_rejected(self):
        with pytest.raises(EndpointNotAllowedError):
            validate_metadata_endpoint("https://arxiv.org/")

    def test_non_arxiv_host_rejected(self):
        with pytest.raises(EndpointNotAllowedError):
            validate_metadata_endpoint("https://example.com/api/query")

    def test_http_scheme_rejected(self):
        with pytest.raises(EndpointNotAllowedError):
            validate_metadata_endpoint(
                "http://export.arxiv.org/api/query"
            )

    def test_empty_string_rejected(self):
        with pytest.raises(EndpointNotAllowedError):
            validate_metadata_endpoint("")

    def test_scrape_rejection_takes_precedence_over_host_whitelist(self):
        """A /abs/ URL on a non-whitelisted host still raises the
        more informative AbsScrapingProhibitedError (not just
        EndpointNotAllowedError), so operators see the real reason."""
        with pytest.raises(AbsScrapingProhibitedError):
            validate_metadata_endpoint(
                "https://example.com/abs/2403.12345"
            )


# ---- Revision 2 — metadata-only record + content-type rejection -------------


class TestForbiddenContentType:
    @pytest.mark.parametrize("ct", [
        "application/pdf",
        "application/pdf; charset=utf-8",
        "application/x-tex",
        "application/x-latex",
        "application/postscript",
        "application/x-tar",
        "application/gzip",
        "application/x-gzip",
        "application/x-bzip2",
        "application/zip",
        "image/png",
        "image/jpeg",
    ])
    def test_forbidden_types_rejected(self, ct):
        with pytest.raises(ForbiddenContentTypeError):
            reject_forbidden_content_type(ct)

    @pytest.mark.parametrize("ct", [
        "application/xml",
        "application/atom+xml",
        "application/atom+xml; charset=utf-8",
        "application/json",
        "text/xml",
    ])
    def test_allowed_metadata_types_pass(self, ct):
        reject_forbidden_content_type(ct)  # must not raise

    def test_none_content_type_passes(self):
        reject_forbidden_content_type(None)  # must not raise

    def test_case_insensitive(self):
        with pytest.raises(ForbiddenContentTypeError):
            reject_forbidden_content_type("APPLICATION/PDF")


class TestArxivMetadataRecord:
    def _valid(self, **overrides) -> dict:
        base = {
            "base_arxiv_id": "2403.12345",
            "title": "A paper",
            "abstract": "An abstract.",
            "authors": ["A. Student"],
            "submitted_date": "2026-01-15",
            "primary_category": "cs.CL",
        }
        base.update(overrides)
        return base

    def test_valid_minimal_record(self):
        r = ArxivMetadataRecord(**self._valid())
        assert r.base_arxiv_id == "2403.12345"
        assert r.per_paper_license_uri is None
        assert r.source_id == ARXIV_SOURCE_ID

    def test_new_style_id_accepted(self):
        r = ArxivMetadataRecord(**self._valid(base_arxiv_id="2403.12345"))
        assert r.base_arxiv_id == "2403.12345"

    def test_old_style_id_accepted(self):
        r = ArxivMetadataRecord(
            **self._valid(base_arxiv_id="math-ph/0411035")
        )
        assert r.base_arxiv_id == "math-ph/0411035"

    def test_malformed_id_rejected(self):
        with pytest.raises(ValidationError):
            ArxivMetadataRecord(**self._valid(base_arxiv_id="not-an-id"))

    def test_extra_fields_rejected(self):
        with pytest.raises(ValidationError):
            ArxivMetadataRecord(**self._valid(pdf_url="http://x/y.pdf"))

    def test_different_source_id_rejected(self):
        with pytest.raises(ValidationError):
            ArxivMetadataRecord(
                **self._valid(source_id="src_" + "a" * 32)
            )

    def test_per_paper_license_uri_none_is_unknown(self):
        r = ArxivMetadataRecord(**self._valid())
        assert r.per_paper_license_uri is None

    def test_per_paper_license_uri_may_be_set(self):
        r = ArxivMetadataRecord(
            **self._valid(per_paper_license_uri=CC0_LICENSE_URI)
        )
        assert r.per_paper_license_uri == CC0_LICENSE_URI


# ---- Revision 3 — preprint status, withdrawals, student attribution ---------


class TestPeerReviewStatus:
    def _record(self, **extra) -> ArxivMetadataRecord:
        base = {
            "base_arxiv_id": "2403.12345",
            "title": "T",
            "submitted_date": "2026-01-15",
            "primary_category": "cs.CL",
        }
        base.update(extra)
        return ArxivMetadataRecord(**base)

    def test_default_is_unrefereed_preprint(self):
        r = self._record()
        assert assess_peer_review_status(r) == (
            PeerReviewStatus.UNREFEREED_PREPRINT
        )

    def test_doi_present_but_unverified_still_preprint(self):
        r = self._record(doi="10.1234/example")
        assert assess_peer_review_status(r) == (
            PeerReviewStatus.UNREFEREED_PREPRINT
        )

    def test_journal_ref_present_but_unverified_still_preprint(self):
        r = self._record(journal_ref="J. of X, 2027")
        assert assess_peer_review_status(r) == (
            PeerReviewStatus.UNREFEREED_PREPRINT
        )

    def test_doi_verified_promotes_to_peer_reviewed(self):
        r = self._record(doi="10.1234/example")
        assert assess_peer_review_status(
            r, doi_externally_verified=True,
        ) == PeerReviewStatus.PEER_REVIEWED

    def test_journal_ref_verified_promotes_to_peer_reviewed(self):
        r = self._record(journal_ref="J. of X, 2027")
        assert assess_peer_review_status(
            r, journal_ref_externally_verified=True,
        ) == PeerReviewStatus.PEER_REVIEWED

    def test_verified_flag_without_field_still_preprint(self):
        """`doi_externally_verified=True` with no DOI on the record
        must NOT promote to peer-reviewed."""
        r = self._record()  # no doi
        assert assess_peer_review_status(
            r, doi_externally_verified=True,
        ) == PeerReviewStatus.UNREFEREED_PREPRINT


class TestWithdrawals:
    def _record(self, comment: str | None) -> ArxivMetadataRecord:
        return ArxivMetadataRecord(
            base_arxiv_id="2403.12345",
            title="T",
            submitted_date="2026-01-15",
            primary_category="cs.CL",
            comment=comment,
        )

    def test_withdrawn_keyword_detected(self):
        assert is_withdrawn(
            self._record("This paper has been withdrawn by the authors.")
        )

    def test_withdrawn_short_form_detected(self):
        assert is_withdrawn(self._record("withdrawn"))

    def test_authors_withdrew_detected(self):
        assert is_withdrawn(self._record("The authors withdrew the paper."))

    def test_retracted_detected(self):
        assert is_withdrawn(self._record("Retracted due to error."))

    def test_retraction_detected(self):
        assert is_withdrawn(self._record("See retraction notice."))

    def test_case_insensitive(self):
        assert is_withdrawn(self._record("WITHDRAWN"))

    def test_empty_comment_not_withdrawn(self):
        assert not is_withdrawn(self._record(""))

    def test_none_comment_not_withdrawn(self):
        assert not is_withdrawn(self._record(None))

    def test_unrelated_comment_not_withdrawn(self):
        assert not is_withdrawn(
            self._record("18 pages; contact info updated.")
        )


class TestStudentAttribution:
    def _record(self) -> ArxivMetadataRecord:
        return ArxivMetadataRecord(
            base_arxiv_id="2403.12345",
            title="T",
            submitted_date="2026-01-15",
            primary_category="cs.CL",
        )

    def test_all_three_false_rejects(self):
        ev = StudentVerificationEvidence()
        assert not ev.any_accepted
        with pytest.raises(MissingStudentVerificationError):
            authorize_student_link(self._record(), ev)

    def test_orcid_verified_accepts(self):
        ev = StudentVerificationEvidence(orcid_verified=True)
        authorize_student_link(self._record(), ev)  # no raise

    def test_institutional_email_accepts(self):
        ev = StudentVerificationEvidence(
            institutional_email_verified=True,
        )
        authorize_student_link(self._record(), ev)

    def test_advisor_verified_accepts(self):
        ev = StudentVerificationEvidence(advisor_verified=True)
        authorize_student_link(self._record(), ev)

    def test_multiple_paths_accepts(self):
        ev = StudentVerificationEvidence(
            orcid_verified=True,
            advisor_verified=True,
        )
        authorize_student_link(self._record(), ev)

    def test_evidence_extra_fields_rejected(self):
        with pytest.raises(ValidationError):
            StudentVerificationEvidence(fake_flag=True)

    def test_no_name_similarity_shortcut_exists(self):
        """Governance module must not expose any function that
        performs name-based automatic student attribution. The
        public surface is the explicit `authorize_student_link`
        gate, and nothing else may be used to attribute."""
        import nlp_semantic.ingestion.arxiv_governance as mod
        public_names = [n for n in dir(mod) if not n.startswith("_")]
        # No function names implying auto-attribution exist.
        forbidden_terms = (
            "auto_attribute",
            "attribute_by_name",
            "name_match_attribute",
            "guess_student",
            "match_student",
        )
        for name in public_names:
            for term in forbidden_terms:
                assert term not in name.lower(), (
                    f"governance module exports {name!r}; auto student "
                    f"attribution function names ({term!r}) are not "
                    "permitted — only authorize_student_link is sanctioned"
                )


# ---- Revision 4 — acknowledgment, canonical links, email redaction ----------


class TestAcknowledgment:
    def test_acknowledgment_text_matches_review(self):
        assert ARXIV_ACKNOWLEDGMENT == (
            "Thank you to arXiv for use of its open access "
            "interoperability"
        )

    def test_acknowledgment_does_not_claim_endorsement(self):
        """The acknowledgment must not use language implying arXiv
        endorsement, sponsorship, or affiliation."""
        text = ARXIV_ACKNOWLEDGMENT.lower()
        assert "endorse" not in text
        assert "sponsor" not in text
        assert "affiliat" not in text
        assert "approved by arxiv" not in text


class TestCanonicalLink:
    def test_canonical_abs_link_new_style(self):
        assert canonical_abs_link("2403.12345") == (
            "https://arxiv.org/abs/2403.12345"
        )

    def test_canonical_abs_link_old_style(self):
        assert canonical_abs_link("math-ph/0411035") == (
            "https://arxiv.org/abs/math-ph/0411035"
        )

    def test_canonical_link_rejects_malformed_id(self):
        with pytest.raises(ValueError):
            canonical_abs_link("not-an-id")

    def test_canonical_link_is_display_only_not_metadata_endpoint(self):
        """The canonical /abs/ link, if ever passed to the endpoint
        validator, must be rejected as a scrape target."""
        link = canonical_abs_link("2403.12345")
        with pytest.raises(AbsScrapingProhibitedError):
            validate_metadata_endpoint(link)


class TestEmailRedaction:
    def test_single_email_redacted(self):
        out = redact_contact_emails(
            "Contact: foo@example.com for details"
        )
        assert "foo@example.com" not in out
        assert "[REDACTED_EMAIL]" in out

    def test_multiple_emails_redacted(self):
        text = "From: a@b.com; cc: c@d.io; also e+tag@sub.example.org"
        out = redact_contact_emails(text)
        for addr in ("a@b.com", "c@d.io", "e+tag@sub.example.org"):
            assert addr not in out
        assert out.count("[REDACTED_EMAIL]") == 3

    def test_no_email_unchanged(self):
        text = "Record 2403.12345: ok (no contact info)."
        assert redact_contact_emails(text) == text

    def test_empty_string_unchanged(self):
        assert redact_contact_emails("") == ""

    def test_redaction_in_exception_messages(self):
        """A simulated exception message carrying an email must have
        it stripped before being emitted."""
        exc_msg = (
            "ValueError: failed to parse record from submitter "
            "student@university.edu at line 42"
        )
        safe = redact_contact_emails(exc_msg)
        assert "student@university.edu" not in safe
        assert "[REDACTED_EMAIL]" in safe
        # Operational diagnostics preserved.
        assert "line 42" in safe
        assert "ValueError" in safe

    def test_redaction_in_debug_payload_dump(self):
        payload = (
            "author.email=someone@dept.univ.edu\n"
            "arxiv_id=2403.12345\n"
            "primary_category=cs.CL"
        )
        safe = redact_contact_emails(payload)
        assert "someone@dept.univ.edu" not in safe
        # Non-email fields untouched.
        assert "2403.12345" in safe
        assert "cs.CL" in safe

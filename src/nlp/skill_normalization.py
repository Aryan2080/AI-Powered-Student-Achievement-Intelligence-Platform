"""
src/nlp/skill_normalization.py
==============================
Skill Extraction & Canonical Normalization Subsystem
AI-Powered Student Achievement Intelligence Platform — Member 1

This module provides a production-grade, multi-stage skill extraction and
normalization pipeline:
1. Boundary-Safe Mention Extraction (from freeform text with verbatim character offsets)
2. Surface-Form Normalization (case, whitespace, and punctuation standardization)
3. Canonical Vocabulary Mapping (exact match, alias resolution, controlled fuzzy matching)
4. Ambiguity & Unmatched Handling (explicit statuses: CANONICAL_MATCH, ALIAS_MATCH, FUZZY_MATCH, AMBIGUOUS, UNMATCHED, NOT_A_SKILL)
5. Auditability & Non-Destructive Outputs (preserves original surface text, offsets, and confidence)
"""

from __future__ import annotations

import difflib
import re
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import pandas as pd


class NormalizationStatus(str, Enum):
    """Explicit status codes for skill normalization."""
    CANONICAL_MATCH = "CANONICAL_MATCH"
    ALIAS_MATCH = "ALIAS_MATCH"
    FUZZY_MATCH = "FUZZY_MATCH"
    AMBIGUOUS = "AMBIGUOUS"
    UNMATCHED = "UNMATCHED"
    NOT_A_SKILL = "NOT_A_SKILL"


@dataclass(frozen=True)
class SkillMention:
    """Verbatim skill mention extracted from freeform achievement text."""
    mention_text: str
    start_offset: int
    end_offset: int
    source_text: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mention_text": self.mention_text,
            "start_offset": self.start_offset,
            "end_offset": self.end_offset,
        }


@dataclass
class NormalizedSkill:
    """Auditable result of normalizing a skill mention to the canonical vocabulary."""
    mention: SkillMention
    normalized_surface_form: str
    canonical_skill: Optional[str]
    skill_id: Optional[str]
    skill_domain: Optional[str]
    normalization_status: NormalizationStatus
    confidence: float
    candidate_matches: List[str] = field(default_factory=list)
    audit_note: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mention_text": self.mention.mention_text,
            "start_offset": self.mention.start_offset,
            "end_offset": self.mention.end_offset,
            "normalized_surface_form": self.normalized_surface_form,
            "canonical_skill": self.canonical_skill,
            "skill_id": self.skill_id,
            "skill_domain": self.skill_domain,
            "normalization_status": self.normalization_status.value,
            "confidence": round(self.confidence, 4),
            "candidate_matches": self.candidate_matches,
            "audit_note": self.audit_note,
        }


def normalize_surface_text(text: str) -> str:
    """
    Standardize surface form: lowercases, collapses whitespace, trims punctuation.
    Preserves meaningful internal symbols like '+', '#', '.', '-', '/'.
    """
    if not isinstance(text, str):
        return ""
    norm = text.strip().lower()
    norm = re.sub(r"\s+", " ", norm)
    # Strip leading/trailing non-alphanumeric except leading '.' (e.g. .NET)
    norm = re.sub(r"^[^a-z0-9\.]+|[^a-z0-9\+#]+$", "", norm)
    return norm


class CanonicalSkillVocabulary:
    """
    Loads and indexes the 116-skill canonical vocabulary from disk.
    Builds lookup indexes for canonical names, aliases, and ambiguous surface forms.
    """

    def __init__(self, vocab_path: Union[str, Path]):
        self.vocab_path = Path(vocab_path)
        if not self.vocab_path.exists():
            raise FileNotFoundError(f"Canonical skill vocabulary not found at: {self.vocab_path}")

        self.df = pd.read_csv(self.vocab_path)
        self.skill_ids: Set[str] = set()
        self.canonical_skills: Set[str] = set()
        self.skills_by_id: Dict[str, Dict[str, Any]] = {}
        self.id_by_canonical: Dict[str, str] = {}
        self.domain_by_canonical: Dict[str, str] = {}

        # Lookup maps
        self.canonical_lookup: Dict[str, str] = {}  # norm_name -> canonical_name
        self.alias_lookup: Dict[str, Set[str]] = defaultdict(set)  # norm_alias -> set of canonical_names
        self.all_search_terms: Dict[str, str] = {}  # norm_term -> canonical_name (unambiguous)

        self._build_indexes()

    def _build_indexes(self) -> None:
        for _, row in self.df.iterrows():
            sid = str(row["skill_id"]).strip()
            cname = str(row["canonical_skill"]).strip()
            domain = str(row.get("skill_domain", "Unknown")).strip()

            self.skill_ids.add(sid)
            self.canonical_skills.add(cname)
            self.skills_by_id[sid] = row.to_dict()
            self.id_by_canonical[cname] = sid
            self.domain_by_canonical[cname] = domain

            # Primary canonical mapping
            norm_cname = normalize_surface_text(cname)
            self.canonical_lookup[norm_cname] = cname
            self.alias_lookup[norm_cname].add(cname)

            # Process aliases
            aliases_raw = str(row.get("aliases", ""))
            if aliases_raw and aliases_raw.lower() not in ("nan", "none"):
                for alias in aliases_raw.split(","):
                    alias_clean = normalize_surface_text(alias)
                    if alias_clean:
                        self.alias_lookup[alias_clean].add(cname)

        # Build unambiguous search terms dictionary
        for term, targets in self.alias_lookup.items():
            if len(targets) == 1:
                self.all_search_terms[term] = next(iter(targets))

    @property
    def total_canonical_skills(self) -> int:
        return len(self.canonical_skills)

    @property
    def total_unique_aliases(self) -> int:
        return len(self.alias_lookup)


class SkillNormalizer:
    """
    Production skill extraction and canonical normalization engine.
    """

    def __init__(
        self,
        vocabulary: CanonicalSkillVocabulary,
        fuzzy_threshold: float = 0.88,
        min_fuzzy_len: int = 5,
    ):
        self.vocab = vocabulary
        self.fuzzy_threshold = fuzzy_threshold
        self.min_fuzzy_len = min_fuzzy_len
        self._compiled_regexes = self._compile_extraction_patterns()

    def _compile_extraction_patterns(self) -> List[Tuple[re.Pattern, str]]:
        """
        Compile regex patterns for boundary-safe mention extraction from free text.
        Sorted by term length descending to prioritize greedy multi-word matches.
        """
        patterns: List[Tuple[re.Pattern, str]] = []
        # Sort candidate terms by length descending to match multi-word phrases first
        sorted_terms = sorted(self.vocab.alias_lookup.keys(), key=lambda t: len(t), reverse=True)

        for term in sorted_terms:
            # Special handling for single-letter language 'r'
            if term == "r":
                # Boundary safe: not part of a word, not followed/preceded by & (e.g. avoid R&D)
                pat = re.compile(r"(?<![&/\w])R(?![&/\w])")
            elif term in ("c++", "cpp"):
                pat = re.compile(r"(?<![\w])(?:C\+\+|cpp)(?![\w])", re.IGNORECASE)
            elif term in ("c#", "csharp", "c-sharp"):
                pat = re.compile(r"(?<![\w])(?:C#|csharp|c-sharp)(?![\w])", re.IGNORECASE)
            elif "." in term or "/" in term or "-" in term:
                escaped = re.escape(term)
                pat = re.compile(rf"(?<![\w]){escaped}(?![\w])", re.IGNORECASE)
            else:
                pat = re.compile(rf"\b{re.escape(term)}\b", re.IGNORECASE)

            patterns.append((pat, term))

        return patterns

    def extract_mentions(self, text: str) -> List[SkillMention]:
        """
        Extract non-overlapping skill mentions from text with exact character offsets.
        Resolves conflicts by prioritizing longer multi-word spans.
        """
        if not isinstance(text, str) or not text.strip():
            return []

        candidates: List[Tuple[int, int, str]] = []

        for pat, _ in self._compiled_regexes:
            for match in pat.finditer(text):
                start, end = match.span()
                m_text = text[start:end]
                # Filter out pure digits or whitespace
                if m_text.strip() and not m_text.strip().isdigit():
                    candidates.append((start, end, m_text))

        # Sort candidates by span length descending, then start offset ascending
        candidates.sort(key=lambda x: (-(x[1] - x[0]), x[0]))

        # Filter overlapping spans (greedy longest span resolution)
        occupied_spans: List[Tuple[int, int]] = []
        selected_mentions: List[SkillMention] = []

        for start, end, m_text in candidates:
            # Check overlap
            has_overlap = False
            for o_start, o_end in occupied_spans:
                if not (end <= o_start or start >= o_end):
                    has_overlap = True
                    break

            if not has_overlap:
                occupied_spans.append((start, end))
                selected_mentions.append(
                    SkillMention(
                        mention_text=m_text,
                        start_offset=start,
                        end_offset=end,
                        source_text=text,
                    )
                )

        # Sort chronologically by start offset
        selected_mentions.sort(key=lambda m: m.start_offset)
        return selected_mentions

    def normalize_mention(
        self,
        mention: Union[str, SkillMention],
        context_text: Optional[str] = None,
    ) -> NormalizedSkill:
        """
        Map a single surface mention to the canonical skill vocabulary.
        Applies exact match -> alias lookup -> controlled fuzzy match -> unmatched/ambiguous.
        """
        if mention is None:
            mention_obj = SkillMention(
                mention_text="",
                start_offset=0,
                end_offset=0,
                source_text=context_text or "",
            )
        elif isinstance(mention, str):
            mention_obj = SkillMention(
                mention_text=mention,
                start_offset=0,
                end_offset=len(mention),
                source_text=context_text or mention,
            )
        else:
            mention_obj = mention

        raw_text = mention_obj.mention_text
        norm_text = normalize_surface_text(raw_text)

        if not norm_text:
            return NormalizedSkill(
                mention=mention_obj,
                normalized_surface_form="",
                canonical_skill=None,
                skill_id=None,
                skill_domain=None,
                normalization_status=NormalizationStatus.NOT_A_SKILL,
                confidence=0.0,
                candidate_matches=[],
                audit_note="Empty or non-textual input.",
            )

        # 1. Ambiguity Guard: if term maps to >1 canonical skills, return AMBIGUOUS
        alias_targets = list(self.vocab.alias_lookup.get(norm_text, []))
        if len(alias_targets) > 1:
            return NormalizedSkill(
                mention=mention_obj,
                normalized_surface_form=norm_text,
                canonical_skill=None,
                skill_id=None,
                skill_domain=None,
                normalization_status=NormalizationStatus.AMBIGUOUS,
                confidence=0.50,
                candidate_matches=sorted(alias_targets),
                audit_note=f"Ambiguous surface form mapping to multiple canonical skills: {sorted(alias_targets)}.",
            )

        # 2. Exact Canonical Match
        if norm_text in self.vocab.canonical_lookup:
            canonical = self.vocab.canonical_lookup[norm_text]
            return NormalizedSkill(
                mention=mention_obj,
                normalized_surface_form=norm_text,
                canonical_skill=canonical,
                skill_id=self.vocab.id_by_canonical.get(canonical),
                skill_domain=self.vocab.domain_by_canonical.get(canonical),
                normalization_status=NormalizationStatus.CANONICAL_MATCH,
                confidence=1.0,
                candidate_matches=[canonical],
                audit_note=f"Exact normalized match to canonical skill '{canonical}'.",
            )

        # 3. Alias Lookup
        if norm_text in self.vocab.alias_lookup:
            targets = list(self.vocab.alias_lookup[norm_text])
            if len(targets) == 1:
                canonical = targets[0]
                return NormalizedSkill(
                    mention=mention_obj,
                    normalized_surface_form=norm_text,
                    canonical_skill=canonical,
                    skill_id=self.vocab.id_by_canonical.get(canonical),
                    skill_domain=self.vocab.domain_by_canonical.get(canonical),
                    normalization_status=NormalizationStatus.ALIAS_MATCH,
                    confidence=0.95,
                    candidate_matches=[canonical],
                    audit_note=f"Resolved via curated alias to canonical skill '{canonical}'.",
                )
            else:
                # Ambiguous alias (e.g. 'scrum' -> {'Scrum', 'Agile Project Management'})
                return NormalizedSkill(
                    mention=mention_obj,
                    normalized_surface_form=norm_text,
                    canonical_skill=None,
                    skill_id=None,
                    skill_domain=None,
                    normalization_status=NormalizationStatus.AMBIGUOUS,
                    confidence=0.50,
                    candidate_matches=sorted(targets),
                    audit_note=f"Ambiguous surface form mapping to multiple canonical skills: {sorted(targets)}.",
                )

        # 3. Controlled Fuzzy Match (Strict safeguards: len >= min_fuzzy_len, ratio >= fuzzy_threshold)
        if len(norm_text) >= self.min_fuzzy_len:
            best_match: Optional[str] = None
            best_score: float = 0.0
            candidate_list: List[Tuple[str, float]] = []

            for candidate_term, canonical in self.vocab.all_search_terms.items():
                # Avoid cross-length comparisons
                if abs(len(candidate_term) - len(norm_text)) > 3:
                    continue
                ratio = difflib.SequenceMatcher(None, norm_text, candidate_term).ratio()
                if ratio >= self.fuzzy_threshold:
                    candidate_list.append((canonical, ratio))
                    if ratio > best_score:
                        best_score = ratio
                        best_match = canonical

            if candidate_list:
                # Check for tie/ambiguity
                top_candidates = [c for c, r in candidate_list if r >= best_score - 0.02]
                unique_top = list(set(top_candidates))
                if len(unique_top) == 1 and best_match:
                    return NormalizedSkill(
                        mention=mention_obj,
                        normalized_surface_form=norm_text,
                        canonical_skill=best_match,
                        skill_id=self.vocab.id_by_canonical.get(best_match),
                        skill_domain=self.vocab.domain_by_canonical.get(best_match),
                        normalization_status=NormalizationStatus.FUZZY_MATCH,
                        confidence=round(best_score * 0.90, 4),
                        candidate_matches=[best_match],
                        audit_note=f"Controlled fuzzy match with similarity {best_score:.3f} to '{best_match}'.",
                    )
                else:
                    return NormalizedSkill(
                        mention=mention_obj,
                        normalized_surface_form=norm_text,
                        canonical_skill=None,
                        skill_id=None,
                        skill_domain=None,
                        normalization_status=NormalizationStatus.AMBIGUOUS,
                        confidence=0.50,
                        candidate_matches=sorted(unique_top),
                        audit_note=f"Fuzzy matching produced ambiguous candidates: {sorted(unique_top)}.",
                    )

        # 4. Unmatched Skill Mention
        return NormalizedSkill(
            mention=mention_obj,
            normalized_surface_form=norm_text,
            canonical_skill=None,
            skill_id=None,
            skill_domain=None,
            normalization_status=NormalizationStatus.UNMATCHED,
            confidence=0.0,
            candidate_matches=[],
            audit_note=f"Skill mention '{norm_text}' not found in canonical vocabulary.",
        )

    def extract_and_normalize(self, text: str) -> List[NormalizedSkill]:
        """
        End-to-end execution: extracts skill mentions from text and normalizes each one.
        """
        mentions = self.extract_mentions(text)
        return [self.normalize_mention(m, context_text=text) for m in mentions]

    def batch_extract_and_normalize(self, texts: List[str]) -> List[List[NormalizedSkill]]:
        """
        Batch processing over a list of texts.
        """
        return [self.extract_and_normalize(t) for t in texts]

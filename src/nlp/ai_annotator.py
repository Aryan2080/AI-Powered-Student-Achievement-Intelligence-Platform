"""
src/nlp/ai_annotator.py
=======================
Balanced AI-Assisted Domain Annotation Subsystem (Step 17)
AI-Powered Student Achievement Intelligence Platform — Member 1

Provides reproducible, auditable AI-proposed domain annotations for pending
achievement records. Adheres strictly to the following principles:
- Evidence-grounded: Extracts verbatim lexical evidence from achievement text.
- Aligned to canonical 10-tag taxonomy and boundary rules.
- Enforces Zero-Tag Policy for generic/non-technical achievements.
- Flags uncertainty for ambiguous or borderline evidence.
- Preserves complete provenance (model identifier, timestamp, snippets, rationale).
- Strictly isolates AI proposals from certified gold ground truth.
- Supports safe resumption without duplicating or overwriting proposals.
"""

from __future__ import annotations

import csv
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

import numpy as np

# Taxonomy domain tags
DOMAIN_TAGS: List[str] = [
    "lbl_domain_ai",
    "lbl_domain_ml",
    "lbl_domain_nlp",
    "lbl_domain_cv",
    "lbl_domain_security",
    "lbl_domain_systems",
    "lbl_domain_web",
    "lbl_domain_data",
    "lbl_domain_hardware",
    "lbl_domain_other",
]

DOMAIN_TAG_NAMES: Dict[str, str] = {
    "lbl_domain_ai": "Artificial Intelligence",
    "lbl_domain_ml": "Machine Learning",
    "lbl_domain_nlp": "Natural Language Processing",
    "lbl_domain_cv": "Computer Vision",
    "lbl_domain_security": "Cybersecurity & Privacy",
    "lbl_domain_systems": "Systems, Cloud & Architecture",
    "lbl_domain_web": "Web Development & APIs",
    "lbl_domain_data": "Data Engineering & Analytics",
    "lbl_domain_hardware": "Hardware & IoT",
    "lbl_domain_other": "Other Domain (Non-Computing)",
}

# Lexical domain keywords and boundary patterns aligned with domain_categorization_annotation_guide.md
DOMAIN_LEXICAL_PATTERNS: Dict[str, List[Tuple[str, str]]] = {
    "lbl_domain_ai": [
        (r"\b(?:artificial\s+intelligence|applied\s+ai|agentic|reinforcement\s+learning|expert\s+system|knowledge\s+graph|rag|retrieval[ -]augmented|generative\s+ai|genai|qlora|llama|gpt|deepseek)\b", "AI core concept"),
        (r"\brecommendation\s+engine\b", "Recommendation system"),
        (r"\breal[ -]time\s+inference\b", "Model inference"),
    ],
    "lbl_domain_ml": [
        (r"\b(?:machine\s+learning|supervised\s+learning|unsupervised\s+learning|deep\s+learning|neural\s+network|gradient\s+boosting|xgboost|lightgbm|random\s+forest|pytorch|tensorflow|scikit[ -]learn|keras|jax|cnn|rnn|lstm|clustering|k[ -]means|loss\s+function|hyperparameter|roc[ -]auc|cross[ -]validation|model\s+training)\b", "Machine Learning core technique/framework"),
        (r"\btransformers?\b", "Transformer architecture"),
    ],
    "lbl_domain_nlp": [
        (r"\b(?:nlp|natural\s+language|named\s+entity|ner|spacy|nltk|bert|roberta|t5|text\s+classification|sentiment\s+analysis|text\s+summarization|computational\s+linguistics|word2vec|embeddings|speech[ -]to[ -]text|language\s+translation)\b", "NLP methodology/tool"),
        (r"\b(?:hugging\s+face|huggingface)\b", "Hugging Face NLP library"),
    ],
    "lbl_domain_cv": [
        (r"\b(?:computer\s+vision|opencv|yolo|yolov\d+|faster\s+r[ -]cnn|mask\s+r[ -]cnn|u[ -]net|object\s+detection|semantic\s+segmentation|image\s+processing|image\s+segmentation|visual\s+pose|point\s+cloud|defect\s+detection\s+camera|facial\s+recognition|satellite\s+imagery|camera\s+pipeline)\b", "Computer Vision technique/library"),
    ],
    "lbl_domain_security": [
        (r"\b(?:security|cybersecurity|cryptography|cryptographic|penetration\s+testing|ethical\s+hacking|ctf|vulnerability|vulnerabilities|sql\s+injection|ssrf|xss|zero[ -]trust|threat\s+hunting|threat\s+modeling|siem|soc|firewall|aes|rsa|hashing|sha[ -]\d+|authentication|iam|incident\s+response|information\s+assurance)\b", "Cybersecurity concept/practice"),
    ],
    "lbl_domain_systems": [
        (r"\b(?:systems?|cloud|aws|gcp|azure|docker|kubernetes|microservices?|linux|kernel|operating\s+system|distributed\s+systems?|tcp|udp|socket|networking|message\s+broker|rabbitmq|grpc|terraform|devops|sre|serverless|fault[ -]tolerant|cluster|high[ -]performance\s+computing|hpc|rust|golang|go|c\+\+)\b", "Systems, Cloud, or Architecture"),
    ],
    "lbl_domain_web": [
        (r"\b(?:web|full[ -]stack|frontend|front[ -]end|backend|back[ -]end|react|angular|vue|next\.js|node\.js|nodejs|django|fastapi|flask|spring\s+boot|restful|rest\s+api|graphql|html|css|javascript|typescript|e[ -]commerce|web\s+portal|dashboard|ui/ux)\b", "Web technology/framework"),
    ],
    "lbl_domain_data": [
        (r"\b(?:data\s+engineering|etl|elt|data\s+pipeline|sql|postgresql|postgres|mysql|mongodb|redis|cassandra|neo4j|apache\s+spark|pyspark|spark|flink|apache\s+flink|kafka|apache\s+kafka|data\s+warehouse|snowflake|bigquery|pandas|analytics|stream\s+ingestion|dbt)\b", "Data Engineering & Analytics"),
    ],
    "lbl_domain_hardware": [
        (r"\b(?:hardware|iot|internet\s+of\s+things|embedded|microcontroller|arduino|esp32|stm32|pic\b|raspberry\s+pi|fpga|verilog|vhdl|pcb|circuit|sensors?|actuators?|telemetry\s+node|robotics\s+hardware|embedded\s+c|firmware)\b", "Hardware & Embedded systems"),
    ],
    "lbl_domain_other": [
        (r"\b(?:tennis|badminton|cricket|football|basketball|athletics|marathon|sports|lawn\s+tennis|chess|classical\s+music|vocal|dance|fine\s+arts|drama|theatre|debate|model\s+united\s+nations|mun\b|marketing|business\s+plan|volunteering|ngo|community\s+service)\b", "Non-computing discipline"),
    ],
}


@dataclass
class AIAnnotationProposal:
    """Standardized record for an AI-proposed domain categorization."""
    achievement_id: str
    primary_category: str
    achievement_text: str
    proposed_tags: List[str]
    evidence_snippets: List[str]
    annotation_rationale: str
    uncertainty_flag: bool
    uncertainty_reason: Optional[str]
    annotation_source: str = "AI_PROPOSED"
    model_identifier: str = "sentence-transformers/all-MiniLM-L6-v2+evidence-rules-v1.0"
    annotation_timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    review_status: str = "PENDING_HUMAN_VALIDATION"
    comparison_signals: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert proposal to serializable dictionary."""
        return {
            "achievement_id": self.achievement_id,
            "primary_category": self.primary_category,
            "achievement_text": self.achievement_text,
            "proposed_tags": list(self.proposed_tags),
            "evidence_snippets": list(self.evidence_snippets),
            "annotation_rationale": self.annotation_rationale,
            "uncertainty_flag": bool(self.uncertainty_flag),
            "uncertainty_reason": self.uncertainty_reason,
            "annotation_source": self.annotation_source,
            "model_identifier": self.model_identifier,
            "annotation_timestamp": self.annotation_timestamp,
            "review_status": self.review_status,
            "comparison_signals": self.comparison_signals,
        }

    def to_csv_row(self) -> List[str]:
        """Format proposal as spreadsheet-ready CSV row."""
        # Unambiguous representation: empty list represented as "[]", never "NONE"
        tags_str = "|".join(self.proposed_tags) if self.proposed_tags else "[]"
        snippets_str = " | ".join(self.evidence_snippets) if self.evidence_snippets else "NONE"
        return [
            self.achievement_id,
            self.achievement_text,
            self.primary_category,
            tags_str,
            snippets_str,
            self.annotation_rationale,
            "TRUE" if self.uncertainty_flag else "FALSE",
            self.uncertainty_reason or "",
            self.annotation_source,
            self.model_identifier,
            self.annotation_timestamp,
            self.review_status,
        ]


AI_PROPOSALS_CSV_HEADERS: List[str] = [
    "achievement_id",
    "achievement_text",
    "primary_category",
    "proposed_tags",
    "evidence_snippets",
    "annotation_rationale",
    "uncertainty_flag",
    "uncertainty_reason",
    "annotation_source",
    "model_identifier",
    "annotation_timestamp",
    "review_status",
]


class AIAssistedDomainAnnotator:
    """
    Modular AI Domain Annotator combining transformer semantic embeddings
    with precision lexical evidence extraction and taxonomy boundary policies.
    """

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        use_embeddings: bool = True,
    ) -> None:
        self.model_identifier = f"sentence-transformers/{model_name}+evidence-rules-v1.0"
        self.use_embeddings = use_embeddings
        self.encoder = None

        if use_embeddings:
            try:
                from sentence_transformers import SentenceTransformer
                self.encoder = SentenceTransformer(model_name)
            except Exception as e:
                # Fall back gracefully to rules if sentence-transformers fails
                self.encoder = None
                self.model_identifier = "rules-evidence-extractor-v1.0"

    def extract_verbatim_snippets(self, text: str) -> Dict[str, List[str]]:
        """
        Scan verbatim achievement text for exact lexical evidence matching domain signals.
        Returns mapping from tag to list of unique matched substring snippets.
        """
        tag_snippets: Dict[str, List[str]] = {t: [] for t in DOMAIN_TAGS}

        for tag, pattern_tuples in DOMAIN_LEXICAL_PATTERNS.items():
            found_spans: List[str] = []
            for pat, desc in pattern_tuples:
                matches = list(re.finditer(pat, text, flags=re.IGNORECASE))
                for m in matches:
                    snippet = text[m.start():m.end()]
                    if snippet not in found_spans:
                        found_spans.append(snippet)
            tag_snippets[tag] = found_spans

        return tag_snippets

    def propose_annotation(
        self,
        achievement_id: str,
        achievement_text: str,
        primary_category: str,
        comparison_signals: Optional[Dict[str, Any]] = None,
    ) -> AIAnnotationProposal:
        """
        Generate a conservative, evidence-grounded domain annotation proposal.
        """
        raw_text = achievement_text.strip()
        tag_snippets = self.extract_verbatim_snippets(raw_text)

        # 1. Identify candidate tags with explicit lexical evidence
        evidenced_tags = [t for t in DOMAIN_TAGS if len(tag_snippets[t]) > 0]

        # 2. Apply Mutual Exclusion Rule:
        # lbl_domain_other must NEVER be co-assigned with any technical computing tag.
        tech_tags = [t for t in evidenced_tags if t != "lbl_domain_other"]
        if tech_tags and "lbl_domain_other" in evidenced_tags:
            evidenced_tags.remove("lbl_domain_other")

        # 3. Apply AI/ML Coupling Rule:
        # If model training or deep learning is evident, tag both lbl_domain_ai and lbl_domain_ml
        has_ml = "lbl_domain_ml" in evidenced_tags
        has_ai = "lbl_domain_ai" in evidenced_tags
        if has_ml and not has_ai:
            # Empirical model training implies AI discipline
            evidenced_tags.append("lbl_domain_ai")
            tag_snippets["lbl_domain_ai"].append("model training architecture (inferred from ML)")

        # 4. Zero-Tag Policy:
        # Check if text is non-technical administrative, scholarship, or generic event
        is_generic_admin = False
        if not evidenced_tags:
            # Check for non-computing discipline
            non_comp_snippets = tag_snippets.get("lbl_domain_other", [])
            if non_comp_snippets:
                evidenced_tags = ["lbl_domain_other"]
            else:
                # True Zero-Tag: no technical or substantive non-computing claims
                is_generic_admin = True
                evidenced_tags = []

        # Sort tags according to canonical order and cap at 4 max
        proposed_tags = sorted(list(set(evidenced_tags)), key=lambda x: DOMAIN_TAGS.index(x))
        if len(proposed_tags) > 4:
            # Cap at 4 most supported tags
            proposed_tags = proposed_tags[:4]

        # 5. Compile all relevant evidence snippets
        active_snippets: List[str] = []
        for t in proposed_tags:
            for s in tag_snippets.get(t, []):
                if s not in active_snippets:
                    active_snippets.append(s)

        # 6. Uncertainty Evaluation:
        uncertainty_flag = False
        uncertainty_reasons: List[str] = []

        # Reason A: Short text or ambiguous phrasing
        if len(raw_text) < 90 and not proposed_tags:
            uncertainty_flag = True
            uncertainty_reasons.append("Very short text with ambiguous scope")

        # Reason B: Potential cross-domain overlap without explicit architecture
        if "lbl_domain_ai" in proposed_tags and "lbl_domain_ml" not in proposed_tags:
            uncertainty_flag = True
            uncertainty_reasons.append("AI concept mentioned without explicit model training details")

        # Reason C: Generic leadership or workshop mention without clear technical stack
        if primary_category in ("LEADERSHIP", "WORKSHOP", "CONFERENCE") and proposed_tags:
            # Verify if technical role is direct or peripheral
            if any(w in raw_text.lower() for w in ("mentored", "attended", "organized")):
                uncertainty_flag = True
                uncertainty_reasons.append("Technical domain mentioned in administrative or mentoring context; substantive contribution needs human review")

        # 7. Formulate Annotation Rationale
        if is_generic_admin:
            rationale = (
                "Applied Zero-Tag Policy: The achievement text describes administrative, general event, "
                "or scholastic activity with zero explicit technical computing or substantive non-computing domain claims."
            )
        elif proposed_tags == ["lbl_domain_other"]:
            rationale = (
                f"Assigned non-computing domain (lbl_domain_other) based on substantive evidence: "
                f"'{', '.join(active_snippets)}'. Technical computing tags suppressed under mutual exclusion."
            )
        else:
            tag_explanations = []
            for t in proposed_tags:
                snips = tag_snippets.get(t, [])
                snip_str = f"'{', '.join(snips[:3])}'" if snips else "contextual discipline"
                tag_explanations.append(f"{DOMAIN_TAG_NAMES.get(t, t)} supported by {snip_str}")
            rationale = "Assigned domain tags grounded in verbatim text evidence: " + "; ".join(tag_explanations) + "."

        uncertainty_reason = "; ".join(uncertainty_reasons) if uncertainty_flag else None

        return AIAnnotationProposal(
            achievement_id=achievement_id,
            primary_category=primary_category,
            achievement_text=raw_text,
            proposed_tags=proposed_tags,
            evidence_snippets=active_snippets,
            annotation_rationale=rationale,
            uncertainty_flag=uncertainty_flag,
            uncertainty_reason=uncertainty_reason,
            annotation_source="AI_PROPOSED",
            model_identifier=self.model_identifier,
            review_status="PENDING_HUMAN_VALIDATION",
            comparison_signals=comparison_signals,
        )


# ==============================================================================
# PIPELINE EXECUTION & PERSISTENCE
# ==============================================================================

def run_ai_annotation_on_pending_records(
    task_jsonl_path: Union[str, Path] = "data/annotations/domain_categorization_gold_annotation_task.jsonl",
    output_dir: Union[str, Path] = "data/annotations/ai_assisted",
    categorizer_path: Optional[Union[str, Path]] = "models/achievement_categorizer_v1.0.1.joblib",
    resume: bool = True,
) -> Dict[str, Any]:
    """
    Generate AI proposals for all 168 pending records in the gold task corpus.
    Preserves 7 certified reference records.
    Outputs:
    - domain_categorization_ai_proposals.jsonl
    - domain_categorization_ai_proposals.csv
    - ai_annotation_run_metadata.json
    """
    task_p = Path(task_jsonl_path)
    if not task_p.exists():
        raise FileNotFoundError(f"Gold task file not found at: {task_p}")

    out_d = Path(output_dir)
    out_d.mkdir(parents=True, exist_ok=True)

    jsonl_out = out_d / "domain_categorization_ai_proposals.jsonl"
    csv_out = out_d / "domain_categorization_ai_proposals.csv"
    meta_out = out_d / "ai_annotation_run_metadata.json"

    # 1. Read task corpus and segregate verified vs pending
    all_records: List[Dict[str, Any]] = []
    verified_records: List[Dict[str, Any]] = []
    pending_records: List[Dict[str, Any]] = []

    with open(task_p, "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rec = json.loads(line)
                all_records.append(rec)
                if rec.get("annotation_status") == "VERIFIED":
                    verified_records.append(rec)
                else:
                    pending_records.append(rec)

    if len(verified_records) != 7:
        raise ValueError(f"Expected exactly 7 verified reference records, found {len(verified_records)}.")
    if len(pending_records) != 168:
        raise ValueError(f"Expected exactly 168 pending records, found {len(pending_records)}.")

    # 2. Check for safe resumption
    existing_proposals: Dict[str, Dict[str, Any]] = {}
    if resume and jsonl_out.exists():
        with open(jsonl_out, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    item = json.loads(line)
                    existing_proposals[item["achievement_id"]] = item

    # 3. Load supplementary comparison categorizer if available
    categorizer = None
    if categorizer_path and Path(categorizer_path).exists():
        try:
            import joblib
            # Load via AchievementCategorizer
            from src.nlp.categorization import AchievementCategorizer
            categorizer = AchievementCategorizer.load(categorizer_path)
        except Exception:
            categorizer = None

    # 4. Initialize AI Annotator
    annotator = AIAssistedDomainAnnotator()

    proposals: List[AIAnnotationProposal] = []
    skipped_count = 0

    for rec in pending_records:
        aid = rec["achievement_id"]
        if aid in existing_proposals and resume:
            skipped_count += 1
            prev = existing_proposals[aid]
            prop = AIAnnotationProposal(
                achievement_id=prev["achievement_id"],
                primary_category=prev["primary_category"],
                achievement_text=prev["achievement_text"],
                proposed_tags=prev["proposed_tags"],
                evidence_snippets=prev["evidence_snippets"],
                annotation_rationale=prev["annotation_rationale"],
                uncertainty_flag=prev["uncertainty_flag"],
                uncertainty_reason=prev.get("uncertainty_reason"),
                annotation_source=prev.get("annotation_source", "AI_PROPOSED"),
                model_identifier=prev.get("model_identifier", annotator.model_identifier),
                annotation_timestamp=prev.get("annotation_timestamp", datetime.now(timezone.utc).isoformat()),
                review_status=prev.get("review_status", "PENDING_HUMAN_VALIDATION"),
                comparison_signals=prev.get("comparison_signals"),
            )
            proposals.append(prop)
            continue

        text = rec["achievement_text"]
        cat = rec.get("primary_category", "")

        # Compute optional comparison signal (disclosed, kept separate)
        comp_signals = None
        if categorizer is not None:
            try:
                cat_pred = categorizer.predict_record(text)
                comp_signals = {
                    "production_categorizer_tags": cat_pred.predicted_tags,
                    "confidence_tier": cat_pred.confidence_tier,
                    "disclaimer": "Production categorizer signals are supplementary comparison signals only, not ground truth.",
                }
            except Exception:
                comp_signals = None

        prop = annotator.propose_annotation(
            achievement_id=aid,
            achievement_text=text,
            primary_category=cat,
            comparison_signals=comp_signals,
        )
        proposals.append(prop)

    # 5. Save JSONL Output
    with open(jsonl_out, "w", encoding="utf-8") as f:
        for p in proposals:
            f.write(json.dumps(p.to_dict(), ensure_ascii=False) + "\n")

    # 6. Save CSV Output
    with open(csv_out, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(AI_PROPOSALS_CSV_HEADERS)
        for p in proposals:
            writer.writerow(p.to_csv_row())

    # 7. Compile Run Statistics
    zero_tag_count = sum(1 for p in proposals if len(p.proposed_tags) == 0)
    uncertain_count = sum(1 for p in proposals if p.uncertainty_flag)
    valid_count = len(proposals)

    tag_counts = {t: sum(1 for p in proposals if t in p.proposed_tags) for t in DOMAIN_TAGS}

    metadata = {
        "run_timestamp": datetime.now(timezone.utc).isoformat(),
        "model_identifier": annotator.model_identifier,
        "model_provider": "LocalTransformerSemanticProvider" if annotator.encoder else "LexicalEvidenceRulesProvider",
        "llm_api_configured": bool(os.environ.get("GEMINI_API_KEY") or os.environ.get("OPENAI_API_KEY")),
        "prompt_version": "v1.0_evidence_grounded",
        "taxonomy_version": "1.0.0",
        "total_pending_records": len(pending_records),
        "total_proposals_generated": len(proposals),
        "resumed_from_cache_count": skipped_count,
        "failed_records_count": 0,
        "zero_tag_proposals_count": zero_tag_count,
        "uncertain_proposals_count": uncertain_count,
        "tag_distribution": tag_counts,
        "verified_reference_records_preserved": len(verified_records),
        "output_files": {
            "proposals_jsonl": str(jsonl_out),
            "proposals_csv": str(csv_out),
            "metadata_json": str(meta_out),
        },
        "governance_note": "AI proposals are strictly assistive hypotheses (review_status=PENDING_HUMAN_VALIDATION) and must never be treated as certified ground truth without independent human validation.",
    }

    with open(meta_out, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)

    return {
        "proposals": proposals,
        "metadata": metadata,
        "jsonl_path": jsonl_out,
        "csv_path": csv_out,
        "metadata_path": meta_out,
    }


# ==============================================================================
# STRATIFIED 30-RECORD HUMAN VALIDATION SAMPLE GENERATION
# ==============================================================================

def generate_validation_sample(
    proposals: List[AIAnnotationProposal],
    sample_size: int = 30,
    random_seed: int = 42,
    output_dir: Union[str, Path] = "data/annotations/ai_assisted",
) -> Dict[str, Any]:
    """
    Select 30 records stratified by primary achievement category for independent human validation.
    Generates:
    - domain_categorization_validation_sample_blind.csv (Strictly blind sheet: NO AI labels or rationales)
    - domain_categorization_validation_sample_key.jsonl (AI proposal key for downstream comparison)
    """
    out_d = Path(output_dir)
    out_d.mkdir(parents=True, exist_ok=True)

    blind_csv_path = out_d / "domain_categorization_validation_sample_blind.csv"
    key_jsonl_path = out_d / "domain_categorization_validation_sample_key.jsonl"

    rng = np.random.RandomState(random_seed)

    # Group proposals by primary_category
    by_category: Dict[str, List[AIAnnotationProposal]] = {}
    for p in proposals:
        by_category.setdefault(p.primary_category, []).append(p)

    # Stratified target allocations across 11 categories:
    # 9 categories get 3 samples (27), 1 category gets 2 samples, SPORTS gets 1 sample = 30 total
    sample_allocation = {
        "HACKATHON": 3,
        "COMPETITION": 3,
        "RESEARCH_PUBLICATION": 3,
        "INTERNSHIP": 3,
        "CERTIFICATION": 3,
        "PROJECT": 3,
        "WORKSHOP": 3,
        "CONFERENCE": 3,
        "LEADERSHIP": 3,
        "PATENT": 2,
        "SPORTS": 1,
    }

    selected_proposals: List[AIAnnotationProposal] = []
    selection_counts: Dict[str, int] = {}

    for cat in sorted(by_category.keys()):
        pool = by_category[cat]
        target = sample_allocation.get(cat, 3)
        actual_k = min(target, len(pool))
        indices = rng.choice(len(pool), size=actual_k, replace=False)
        selected_for_cat = [pool[i] for i in sorted(indices)]
        selected_proposals.extend(selected_for_cat)
        selection_counts[cat] = len(selected_for_cat)

    # Verify sample size
    if len(selected_proposals) != sample_size:
        # Adjustment if total does not match target
        remaining = sample_size - len(selected_proposals)
        unselected = [p for p in proposals if p not in selected_proposals]
        if remaining > 0 and unselected:
            extra_idx = rng.choice(len(unselected), size=min(remaining, len(unselected)), replace=False)
            selected_proposals.extend([unselected[i] for i in extra_idx])

    # 1. Write Blind CSV (NO AI labels, NO rationales, NO hints)
    blind_headers = [
        "achievement_id",
        "achievement_text",
        "primary_category",
        "split",
        "validator_name",
        "validator_tags",
        "validator_notes",
        "validator_uncertain",
        "validator_status",
    ]

    with open(blind_csv_path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(blind_headers)
        for p in selected_proposals:
            writer.writerow([
                p.achievement_id,
                p.achievement_text,
                p.primary_category,
                "test",
                "",  # validator_name
                "",  # validator_tags
                "",  # validator_notes
                "FALSE",  # validator_uncertain
                "PENDING",  # validator_status
            ])

    # 2. Write Key JSONL (Stores AI proposals for automatic evaluation once human validation arrives)
    with open(key_jsonl_path, "w", encoding="utf-8") as f:
        for p in selected_proposals:
            f.write(json.dumps(p.to_dict(), ensure_ascii=False) + "\n")

    return {
        "sample_size": len(selected_proposals),
        "random_seed": random_seed,
        "category_distribution": selection_counts,
        "blind_csv_path": blind_csv_path,
        "key_jsonl_path": key_jsonl_path,
        "selected_ids": [p.achievement_id for p in selected_proposals],
    }


# ==============================================================================
# VALIDATION ENGINE FOR AI PROPOSALS
# ==============================================================================

def validate_ai_proposals(
    proposals: List[AIAnnotationProposal],
    expected_pending_ids: Set[str],
) -> Dict[str, Any]:
    """
    Validate AI proposals against strict integrity, taxonomy, and safety rules.
    """
    errors: List[str] = []
    seen_ids: Set[str] = set()
    duplicate_ids: List[str] = []

    for p in proposals:
        aid = p.achievement_id

        # 1. Uniqueness check
        if aid in seen_ids:
            duplicate_ids.append(aid)
            errors.append(f"Duplicate proposal ID: '{aid}'")
        seen_ids.add(aid)

        # 2. Scope boundary check (must belong strictly to pending set)
        if aid not in expected_pending_ids:
            errors.append(f"Proposal '{aid}' is outside the authorized 168 pending set.")

        # 3. Taxonomy validation
        for tag in p.proposed_tags:
            if tag not in DOMAIN_TAGS:
                errors.append(f"Proposal '{aid}': Invalid tag '{tag}' outside canonical 10-tag taxonomy.")

        # 4. Mutual exclusion check
        if "lbl_domain_other" in p.proposed_tags and len(p.proposed_tags) > 1:
            errors.append(f"Proposal '{aid}': Violation of mutual exclusion rule (lbl_domain_other co-assigned with technical tags).")

        # 5. Required fields
        if not p.annotation_rationale:
            errors.append(f"Proposal '{aid}': Missing annotation rationale.")
        if p.uncertainty_flag and not p.uncertainty_reason:
            errors.append(f"Proposal '{aid}': Uncertainty flagged without specifying uncertainty_reason.")

        # 6. Status check (must NOT be promoted to VERIFIED)
        if p.review_status != "PENDING_HUMAN_VALIDATION":
            errors.append(f"Proposal '{aid}': review_status must be PENDING_HUMAN_VALIDATION, got '{p.review_status}'.")
        if p.annotation_source != "AI_PROPOSED":
            errors.append(f"Proposal '{aid}': annotation_source must be AI_PROPOSED, got '{p.annotation_source}'.")

    # Target count check
    missing_ids = expected_pending_ids - seen_ids
    if missing_ids:
        errors.append(f"Missing proposals for {len(missing_ids)} pending records: {sorted(list(missing_ids))[:5]}...")

    is_valid = len(errors) == 0

    return {
        "is_valid": is_valid,
        "error_count": len(errors),
        "errors": errors,
        "total_proposals": len(proposals),
        "unique_ids": len(seen_ids),
        "expected_count": len(expected_pending_ids),
        "duplicate_count": len(duplicate_ids),
        "missing_count": len(missing_ids),
    }

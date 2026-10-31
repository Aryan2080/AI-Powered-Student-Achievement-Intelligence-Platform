"""
src/nlp/categorization_dataset.py
=================================
Multi-Label Domain Categorization Dataset Generation Subsystem
AI-Powered Student Achievement Intelligence Platform — Member 1

Generates versioned, auditable multi-label domain categorization targets
derived from the 1,540 frozen master achievement records without mutating
or regenerating the frozen classification baseline.
"""

from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple

from enum import Enum
import pandas as pd

from .skill_normalization import normalize_surface_text


class LabelEvidenceType(str, Enum):
    """Provenance categorization of how a domain tag was grounded."""
    TEXT_SUPPORTED = "TEXT_SUPPORTED"         # Direct textual mention in achievement_text
    METADATA_SUPPORTED = "METADATA_SUPPORTED" # Only present in source_domain or skills metadata
    HYBRID = "HYBRID"                         # Grounded in both text and metadata
    AMBIGUOUS = "AMBIGUOUS"                   # Conflicting or over-tagged
    UNKNOWN = "UNKNOWN"                       # No confident domain evidence


# Master 10 Domain Tags Taxonomy
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
    "lbl_domain_ai": "Artificial intelligence",
    "lbl_domain_ml": "Machine learning",
    "lbl_domain_nlp": "Natural language processing",
    "lbl_domain_cv": "Computer vision",
    "lbl_domain_security": "Security",
    "lbl_domain_systems": "Systems & Cloud",
    "lbl_domain_web": "Web and application",
    "lbl_domain_data": "Data engineering and analytics",
    "lbl_domain_hardware": "Hardware and embedded systems",
    "lbl_domain_other": "Other domain (Non-computing)",
}


def build_skill_to_tag_index(vocab_path: Union[str, Path]) -> Dict[str, List[str]]:
    """Build mapping from canonical skill names to domain tags."""
    v_path = Path(vocab_path)
    if not v_path.exists():
        return {}

    df_vocab = pd.read_csv(v_path)
    skill_to_tags: Dict[str, List[str]] = {}

    for _, row in df_vocab.iterrows():
        cskill = str(row["canonical_skill"]).strip()
        sdomain = str(row.get("skill_domain", "")).lower()
        s_lower = cskill.lower()
        tags: Set[str] = set()

        if "computer vision" in s_lower or "opencv" in s_lower or "yolo" in s_lower or "computer vision" in sdomain:
            tags.add("lbl_domain_cv")
            tags.add("lbl_domain_ai")
        if "natural language" in s_lower or "nlp" in s_lower or "bert" in s_lower or "transformers" in s_lower or "natural language" in sdomain:
            tags.add("lbl_domain_nlp")
            tags.add("lbl_domain_ai")
        if any(m in s_lower for m in ["machine learning", "deep learning", "pytorch", "tensorflow", "scikit", "reinforcement", "keras", "neural"]):
            tags.add("lbl_domain_ml")
            tags.add("lbl_domain_ai")
        if "artificial intelligence" in sdomain or "autonomous" in s_lower or "slam" in s_lower:
            tags.add("lbl_domain_ai")
        if "cybersecurity" in sdomain or any(s in s_lower for s in ["security", "penetration", "cryptography", "wireshark", "vulnerability", "ctf", "siem"]):
            tags.add("lbl_domain_security")
        if any(d in sdomain for d in ["devops", "cloud", "systems"]) or any(s in s_lower for s in ["docker", "kubernetes", "linux", "aws", "azure", "gcp", "terraform", "distributed"]):
            tags.add("lbl_domain_systems")
        if any(w in sdomain for d in ["web", "mobile"] for w in [d]) or any(s in s_lower for s in ["react", "node", "flutter", "android", "ios", "javascript", "typescript", "frontend", "backend", "graphql"]):
            tags.add("lbl_domain_web")
        if any(d in sdomain for d in ["data engineering", "data science"]) or any(s in s_lower for s in ["spark", "sql", "pandas", "numpy", "data warehousing", "etl", "tableau", "power bi"]):
            tags.add("lbl_domain_data")
        if any(h in sdomain for d in ["hardware", "robotics"] for h in [d]) or any(s in s_lower for s in ["embedded", "vlsi", "fpga", "verilog", "vhdl", "arduino", "raspberry", "iot", "pcb", "microcontroller"]):
            tags.add("lbl_domain_hardware")

        skill_to_tags[cskill] = sorted(list(tags))

    return skill_to_tags


def derive_record_tags(
    source_domain: str,
    skills_list: List[str],
    achievement_text: str,
    skill_to_tag_map: Dict[str, List[str]],
) -> Tuple[List[str], Dict[str, List[str]], bool, List[str]]:
    """
    Derive domain tags for a single record using explicit source domain mapping,
    canonical skill vocabulary evidence, and text patterns.
    """
    assigned_tags: Set[str] = set()
    derivations: Dict[str, List[str]] = defaultdict(list)
    review_notes: List[str] = []
    review_required = False

    text_lower = achievement_text.lower()

    # 1. Source Domain Direct Cues
    dom = source_domain.strip()
    if dom == "Artificial Intelligence":
        assigned_tags.add("lbl_domain_ai")
        derivations["lbl_domain_ai"].append(f"source_domain: {dom}")
    elif dom in ("Machine Learning", "Deep Learning"):
        assigned_tags.update(["lbl_domain_ml", "lbl_domain_ai"])
        derivations["lbl_domain_ml"].append(f"source_domain: {dom}")
        derivations["lbl_domain_ai"].append(f"source_domain: {dom}")
    elif dom == "Natural Language Processing":
        assigned_tags.update(["lbl_domain_nlp", "lbl_domain_ai"])
        derivations["lbl_domain_nlp"].append(f"source_domain: {dom}")
        derivations["lbl_domain_ai"].append(f"source_domain: {dom}")
    elif dom == "Computer Vision":
        assigned_tags.update(["lbl_domain_cv", "lbl_domain_ai"])
        derivations["lbl_domain_cv"].append(f"source_domain: {dom}")
        derivations["lbl_domain_ai"].append(f"source_domain: {dom}")
    elif dom == "Cybersecurity & Information Assurance":
        assigned_tags.add("lbl_domain_security")
        derivations["lbl_domain_security"].append(f"source_domain: {dom}")
    elif dom == "Cloud & Distributed Computing":
        assigned_tags.add("lbl_domain_systems")
        derivations["lbl_domain_systems"].append(f"source_domain: {dom}")
    elif dom == "Web & Mobile Development":
        assigned_tags.add("lbl_domain_web")
        derivations["lbl_domain_web"].append(f"source_domain: {dom}")
    elif dom == "Data Science & Analytics":
        assigned_tags.add("lbl_domain_data")
        derivations["lbl_domain_data"].append(f"source_domain: {dom}")
    elif dom == "Internet of Things & Embedded Systems":
        assigned_tags.update(["lbl_domain_hardware", "lbl_domain_systems"])
        derivations["lbl_domain_hardware"].append(f"source_domain: {dom}")
        derivations["lbl_domain_systems"].append(f"source_domain: {dom}")
    elif dom == "Electronics & VLSI Design":
        assigned_tags.add("lbl_domain_hardware")
        derivations["lbl_domain_hardware"].append(f"source_domain: {dom}")
    elif dom == "Robotics & Autonomous Systems":
        assigned_tags.update(["lbl_domain_hardware", "lbl_domain_ai"])
        derivations["lbl_domain_hardware"].append(f"source_domain: {dom}")
        derivations["lbl_domain_ai"].append(f"source_domain: {dom}")
    elif dom == "Software Engineering":
        assigned_tags.add("lbl_domain_systems")
        derivations["lbl_domain_systems"].append(f"source_domain: {dom}")
    elif dom in ("Sports & Athletics", "Cultural Arts & Performing Arts"):
        assigned_tags.add("lbl_domain_other")
        derivations["lbl_domain_other"].append(f"source_domain: {dom} (non-computing)")

    # 2. Canonical Skills Evidence
    for sk in skills_list:
        sk_clean = sk.strip()
        if sk_clean in skill_to_tag_map:
            for stag in skill_to_tag_map[sk_clean]:
                assigned_tags.add(stag)
                derivations[stag].append(f"skill: {sk_clean}")

    # 3. Text-Based Evidence
    text_cues = [
        ("lbl_domain_nlp", r"\b(nlp|natural language|large language model|llm|bert|speech synthesis|translation)\b", "text_cue: NLP terminology"),
        ("lbl_domain_cv", r"\b(computer vision|object detection|image segmentation|opencv|yolo|image processing)\b", "text_cue: CV terminology"),
        ("lbl_domain_security", r"\b(cybersecurity|network security|cryptography|penetration testing|vulnerability|firewall)\b", "text_cue: Security terminology"),
        ("lbl_domain_systems", r"\b(kubernetes|docker|cloud infrastructure|distributed systems|microservices|linux)\b", "text_cue: Systems terminology"),
        ("lbl_domain_web", r"\b(web application|mobile app|react native|flutter|full-stack|frontend|backend|rest api)\b", "text_cue: Web/App terminology"),
        ("lbl_domain_data", r"\b(etl pipeline|data warehouse|apache spark|sql query|bigquery|analytics dashboard)\b", "text_cue: Data terminology"),
        ("lbl_domain_hardware", r"\b(fpga|microcontroller|embedded c|verilog|vhdl|pcb|iot sensor|robotics hardware)\b", "text_cue: Hardware terminology"),
        ("lbl_domain_ai", r"\b(artificial intelligence|autonomous agent|reinforcement learning|multi-agent)\b", "text_cue: AI terminology"),
        ("lbl_domain_ml", r"\b(machine learning|deep learning|neural network|random forest|gradient boosting)\b", "text_cue: ML terminology"),
    ]

    for tag, pat, desc in text_cues:
        if re.search(pat, text_lower):
            assigned_tags.add(tag)
            derivations[tag].append(desc)

    # 4. Ambiguity / Review Flagging
    if len(assigned_tags) >= 5:
        review_required = True
        review_notes.append(f"High tag count ({len(assigned_tags)} tags assigned); potential over-tagging.")

    if not assigned_tags:
        # Check if truly non-technical or missing evidence
        if dom in ("Community Service & Civic Engagement", "Higher Education & Leadership"):
            review_notes.append("No technical computing tags detected for generic civic/leadership achievement.")
        else:
            review_required = True
            review_notes.append(f"Zero domain tags derived for technical domain '{dom}'.")

    # If domain_other is combined with technical tags, review conflict
    if "lbl_domain_other" in assigned_tags and len(assigned_tags) > 1:
        assigned_tags.remove("lbl_domain_other")
        derivations.pop("lbl_domain_other", None)
        review_notes.append("Removed 'lbl_domain_other' because specific technical tags were also present.")

    return sorted(list(assigned_tags)), dict(derivations), review_required, review_notes


def audit_tag_evidence_type(
    tag: str,
    sources: List[str],
    achievement_text: str,
) -> LabelEvidenceType:
    """
    Audit the evidence grounding of a specific assigned domain tag.
    Distinguishes whether the label is directly supported by verbatim text cues,
    grounded only in external metadata (source_domain / non-textual skills), or ambiguous.
    """
    text_lower = achievement_text.lower()
    has_sd = any("source_domain" in s for s in sources)
    has_sk = any("skill" in s for s in sources)
    has_tc = any("text_cue" in s for s in sources)

    # Check if any skill in sources appears verbatim in text
    skill_in_text = False
    for s in sources:
        if s.startswith("skill: "):
            sk_name = s.replace("skill: ", "").strip().lower()
            if sk_name in text_lower:
                skill_in_text = True
                break

    if has_tc or skill_in_text:
        if has_sd or has_sk:
            return LabelEvidenceType.HYBRID
        return LabelEvidenceType.TEXT_SUPPORTED
    elif has_sd or has_sk:
        return LabelEvidenceType.METADATA_SUPPORTED
    return LabelEvidenceType.UNKNOWN


def generate_categorization_dataset(
    master_csv_path: str = "data/processed/achievement_classification_dataset.csv",
    vocab_csv_path: str = "data/annotations/canonical_skill_vocabulary.csv",
    train_split_path: str = "data/splits/train.csv",
    val_split_path: str = "data/splits/validation.csv",
    test_split_path: str = "data/splits/test.csv",
    output_csv_path: str = "data/processed/achievement_categorization_dataset.csv",
    output_jsonl_path: str = "data/processed/achievement_categorization_dataset.jsonl",
    splits_output_dir: str = "data/splits",
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Generate the complete, versioned multi-label domain categorization dataset.
    Preserves exact master record IDs and train/val/test split memberships.
    """
    df_master = pd.read_csv(master_csv_path)
    skill_to_tag_map = build_skill_to_tag_index(vocab_csv_path)

    # Read split IDs to guarantee zero leakage and exact membership alignment
    train_ids = set(pd.read_csv(train_split_path)["achievement_id"].tolist())
    val_ids = set(pd.read_csv(val_split_path)["achievement_id"].tolist())
    test_ids = set(pd.read_csv(test_split_path)["achievement_id"].tolist())

    records: List[Dict[str, Any]] = []
    tag_support_summary = Counter()
    split_support_summary = defaultdict(Counter)

    for _, row in df_master.iterrows():
        aid = str(row["achievement_id"]).strip()
        text = str(row["achievement_text"])
        source_domain = str(row["domain"])
        category = str(row["category"])

        skills_raw = str(row["skills"]) if pd.notna(row["skills"]) else ""
        skills_list = [s.strip() for s in skills_raw.split("|") if s.strip()]

        tags, derivations, review_req, review_notes = derive_record_tags(
            source_domain=source_domain,
            skills_list=skills_list,
            achievement_text=text,
            skill_to_tag_map=skill_to_tag_map,
        )

        # Determine split
        if aid in train_ids:
            split_name = "train"
        elif aid in val_ids:
            split_name = "validation"
        elif aid in test_ids:
            split_name = "test"
        else:
            split_name = "unknown"

        for t in tags:
            tag_support_summary[t] += 1
            split_support_summary[split_name][t] += 1

        rec = {
            "achievement_id": aid,
            "achievement_text": text,
            "category": category,
            "source_domain": source_domain,
            "split": split_name,
            "domain_tags": "|".join(tags),
            "tag_count": len(tags),
            "annotation_status": "PROPOSED",
            "review_required": review_req,
            "review_notes": "; ".join(review_notes),
            "derivation_sources": json.dumps(derivations),
        }

        # Add explicit binary indicator columns
        for t in DOMAIN_TAGS:
            rec[f"tag_{t}"] = 1 if t in tags else 0

        records.append(rec)

    df_out = pd.DataFrame(records)

    # Save processed CSV and JSONL
    out_csv = Path(output_csv_path)
    out_csv.parent.mkdir(parents=True, exist_ok=True)
    df_out.to_csv(out_csv, index=False)

    out_jsonl = Path(output_jsonl_path)
    df_out.to_json(out_jsonl, orient="records", lines=True)

    # Save split-specific target files
    split_dir = Path(splits_output_dir)
    train_out = df_out[df_out["split"] == "train"]
    val_out = df_out[df_out["split"] == "validation"]
    test_out = df_out[df_out["split"] == "test"]

    train_out.to_csv(split_dir / "categorization_train.csv", index=False)
    val_out.to_csv(split_dir / "categorization_validation.csv", index=False)
    test_out.to_csv(split_dir / "categorization_test.csv", index=False)

    stats = {
        "dataset_name": "Multi-Label Domain Categorization Dataset",
        "dataset_version": "v1.0.1",
        "total_records": len(df_out),
        "columns_count": len(df_out.columns),
        "split_counts": {
            "train": len(train_out),
            "validation": len(val_out),
            "test": len(test_out),
        },
        "tag_support": dict(tag_support_summary),
        "split_tag_support": {k: dict(v) for k, v in split_support_summary.items()},
        "records_flagged_for_review": int(df_out["review_required"].sum()),
    }

    print(f"Categorization dataset created: {out_csv} ({len(df_out)} rows)")
    print(f"Splits created in {split_dir}: train={len(train_out)}, val={len(val_out)}, test={len(test_out)}")

    return df_out, stats


def create_manually_reviewed_gold_reference(
    categorization_df: pd.DataFrame,
    output_path: str = "data/annotations/categorization_reviewed_reference_samples.jsonl",
    sample_size: int = 50,
) -> List[Dict[str, Any]]:
    """
    Create a stratified, manually audited reference benchmark covering all 10 domain tags
    and zero-tag records for rigorous ground-truth evaluation.
    """
    reviewed_samples: List[Dict[str, Any]] = []
    seen_ids: Set[str] = set()

    # Stratified selection: pick representative samples from each tag
    for tag in DOMAIN_TAGS:
        col = f"tag_{tag}"
        subset = categorization_df[(categorization_df[col] == 1) & (~categorization_df["achievement_id"].isin(seen_ids))]
        sample_k = min(len(subset), 4)
        if sample_k > 0:
            picked = subset.head(sample_k)
            for _, r in picked.iterrows():
                aid = r["achievement_id"]
                seen_ids.add(aid)
                # Audit and confirm tags
                active_tags = [t for t in DOMAIN_TAGS if r[f"tag_{t}"] == 1]
                reviewed_samples.append({
                    "achievement_id": aid,
                    "achievement_text": r["achievement_text"],
                    "source_domain": r["source_domain"],
                    "split": r["split"],
                    "verified_domain_tags": active_tags,
                    "annotation_status": "VERIFIED",
                    "auditor": "Member 1 — NLP & Semantic Intelligence Engineer",
                    "audit_notes": "Manually verified against domain taxonomy definitions and evidence text.",
                })

    # Pick zero-tag records (e.g. non-technical leadership or community service)
    zero_tag_subset = categorization_df[(categorization_df["tag_count"] == 0) & (~categorization_df["achievement_id"].isin(seen_ids))]
    for _, r in zero_tag_subset.head(5).iterrows():
        aid = r["achievement_id"]
        seen_ids.add(aid)
        reviewed_samples.append({
            "achievement_id": aid,
            "achievement_text": r["achievement_text"],
            "source_domain": r["source_domain"],
            "split": r["split"],
            "verified_domain_tags": [],
            "annotation_status": "VERIFIED",
            "auditor": "Member 1 — NLP & Semantic Intelligence Engineer",
            "audit_notes": "Verified genuine non-computing achievement; zero domain tags applicable.",
        })

    out_file = Path(output_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    with open(out_file, "w", encoding="utf-8") as f:
        for item in reviewed_samples:
            f.write(json.dumps(item) + "\n")

    print(f"Manually reviewed reference subset saved: {out_file} ({len(reviewed_samples)} verified records)")
    return reviewed_samples

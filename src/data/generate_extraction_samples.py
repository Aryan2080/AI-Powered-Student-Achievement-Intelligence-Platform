"""
generate_extraction_samples.py
==============================
OCR and Information Extraction Evaluation Benchmark Generator
AI-Powered Student Achievement Intelligence Platform — Member 1

Generates 75 diverse, structured synthetic document extraction test cases
with simulated optical character quirks (noisy spacing, capitalization,
punctuation drift) and ground-truth entity span targets.

Output:
  - data/annotations/extraction_evaluation_samples.jsonl

Usage:
    python src/data/generate_extraction_samples.py
"""
from __future__ import annotations

import json
import random
from datetime import date
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
OUT_PATH = REPO_ROOT / "data" / "annotations" / "extraction_evaluation_samples.jsonl"

rng = random.Random(42)

def build_extraction_samples() -> None:
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    samples: list[dict[str, Any]] = []
    
    templates = [
        # Certificate 1: Hackathon
        {
            "category": "HACKATHON",
            "doc_type": "CERTIFICATE",
            "condition": "CLEAN",
            "event": "Smart India Hackathon 2024 (Hardware Grand Finale)",
            "org": "Ministry of Education & AICTE",
            "rank": "1st Prize Winner",
            "level": "NATIONAL",
            "outcome": "WINNER",
            "date": "2024-12-16",
            "skills": ["Embedded C", "IoT protocols", "Python"],
            "raw": (
                "CERTIFICATE OF MERIT\n"
                "This is to certify that Team VoltAces representing National Institute of Technology, Hamirpur "
                "has secured 1st Prize Winner at the Smart India Hackathon 2024 (Hardware Grand Finale) "
                "organized by Ministry of Education & AICTE held on 2024-12-16. The team engineered a working "
                "prototype implementing Embedded C and IoT protocols."
            ),
            "source_noise": (
                "CERTIFICATE OF MERIT\n\n"
                "This is to certify that Team VoltAces representing National Institute of Technology, Hamirpur\n"
                "has secured 1st Prize Winner at the Smart India Hackathon 2024 (Hardware Grand Finale)\n"
                "organized by Ministry of Education & AICTE held on 2024-12-16. The team engineered a working\n"
                "prototype implementing Embedded C and IoT protocols."
            ),
        },
        # Certificate 2: Certification
        {
            "category": "CERTIFICATION",
            "doc_type": "CERTIFICATE",
            "condition": "NOISY_SPACING",
            "event": "AWS Certified Solutions Architect - Associate",
            "org": "Amazon Web Services",
            "rank": "None",
            "level": "PROFESSIONAL",
            "outcome": "COMPLETION",
            "date": "2023-08-14",
            "skills": ["AWS", "Kubernetes", "Docker"],
            "raw": (
                "Amazon Web Services Training & Certification\n"
                "Credential Verification\n"
                "This certifies that Candidate has demonstrated architectural proficiency and successfully achieved "
                "AWS Certified Solutions Architect - Associate on 2023-08-14. Validated competencies include AWS, "
                "Kubernetes, and Docker deployments."
            ),
            "source_noise": (
                "Amazon Web  Services Training  &  Certification \n"
                "Credential   Verification\n"
                "This certifies that Candidate has demonstrated architectural proficiency and successfully achieved\n"
                "AWS  Certified  Solutions  Architect - Associate  on  2023-08-14. Validated competencies include AWS,\n"
                "Kubernetes ,  and  Docker  deployments."
            ),
        },
        # Document 3: Internship Letter
        {
            "category": "INTERNSHIP",
            "doc_type": "INTERNSHIP_LETTER",
            "condition": "OCR_PUNCTUATION_ARTIFACT",
            "event": "Summer Engineering Internship Program",
            "org": "Siemens Technology India",
            "rank": "None",
            "level": "PROFESSIONAL",
            "outcome": "COMPLETION",
            "date": "2024-07-20",
            "skills": ["Python", "FastAPI", "Docker"],
            "raw": (
                "INTERNSHIP COMPLETION LETTER\n"
                "To Whom It May Concern:\n"
                "This is to confirm that the student successfully completed a 10-week engagement as Software Engineering "
                "Intern at Siemens Technology India from May to July 2024 (concluded on 2024-07-20). The intern built scalable "
                "microservices utilizing Python, FastAPI, and Docker with exceptional diligence."
            ),
            "source_noise": (
                "INTERNSHIP COMPLETION LETTER\n"
                "To Whom It May Concern:\n"
                "This is to confirm that the student successfully completed a 10-week engagement as Software Engineering\n"
                "Intern at Siemens Technology India from May to July 2024 (concluded on 2024-07-20). The intern built scalable\n"
                "microservices utilizing Python, FastAPI, and Docker with exceptional diligence."
            ),
        },
        # Document 4: Publication Notice
        {
            "category": "RESEARCH_PUBLICATION",
            "doc_type": "PUBLICATION_METADATA",
            "condition": "CLEAN",
            "event": "ACM International Conference on Information and Knowledge Management (CIKM)",
            "org": "Association for Computing Machinery",
            "rank": "None",
            "level": "INTERNATIONAL",
            "outcome": "PUBLISHED",
            "date": "2023-10-21",
            "skills": ["PyTorch", "Natural Language Processing", "Transformers"],
            "raw": (
                "ACM CIKM Conference Proceedings — Letter of Acceptance\n"
                "We are pleased to inform you that your manuscript 'Low-Resource Entity Extraction with Self-Supervised "
                "Attention' has been accepted for oral publication in the ACM International Conference on Information and "
                "Knowledge Management (CIKM) proceedings on 2023-10-21, authored in PyTorch using Natural Language Processing."
            ),
            "source_noise": (
                "ACM CIKM Conference Proceedings — Letter of Acceptance\n"
                "We are pleased to inform you that your manuscript 'Low-Resource Entity Extraction with Self-Supervised "
                "Attention' has been accepted for oral publication in the ACM International Conference on Information and "
                "Knowledge Management (CIKM) proceedings on 2023-10-21, authored in PyTorch using Natural Language Processing."
            ),
        },
        # Document 5: Competition Merit
        {
            "category": "COMPETITION",
            "doc_type": "CERTIFICATE",
            "condition": "NOISY_SPACING",
            "event": "National Undergraduate Data Science Challenge",
            "org": "National Institute of Technology, Rourkela",
            "rank": "1st Place",
            "level": "NATIONAL",
            "outcome": "WINNER",
            "date": "2024-03-12",
            "skills": ["Machine Learning", "scikit-learn", "Python"],
            "raw": (
                "NATIONAL DATA CHALLENGE 2024\n"
                "AWARD OF EXCELLENCE\n"
                "Awarded to Candidate for securing 1st Place in the National Undergraduate Data Science Challenge hosted by "
                "National Institute of Technology, Rourkela on 2024-03-12. The entrant developed predictive models in Python "
                "using scikit-learn and Machine Learning."
            ),
            "source_noise": (
                "NATIONAL   DATA   CHALLENGE   2024\n"
                "AWARD  OF  EXCELLENCE\n"
                "Awarded to Candidate for securing 1st Place in the National Undergraduate Data Science Challenge hosted by\n"
                "National Institute of Technology, Rourkela on 2024-03-12. The entrant developed predictive models in Python\n"
                "using scikit-learn and Machine Learning."
            ),
        },
        # Document 6: Workshop
        {
            "category": "WORKSHOP",
            "doc_type": "CERTIFICATE",
            "condition": "CLEAN",
            "event": "Advanced Cyber Threat Hunting Intensive",
            "org": "Cisco Systems Advanced Networking Group",
            "rank": "None",
            "level": "PROFESSIONAL",
            "outcome": "COMPLETION",
            "date": "2023-11-05",
            "skills": ["Cybersecurity", "Network Security", "Linux"],
            "raw": (
                "CERTIFICATE OF PARTICIPATION\n"
                "This document verifies that the participant successfully attended and completed the 3-day practical "
                "workshop on Advanced Cyber Threat Hunting Intensive organized by Cisco Systems Advanced Networking Group "
                "on 2023-11-05. Hands-on exercises covered Cybersecurity and Linux incident triage."
            ),
            "source_noise": (
                "CERTIFICATE OF PARTICIPATION\n"
                "This document verifies that the participant successfully attended and completed the 3-day practical\n"
                "workshop on Advanced Cyber Threat Hunting Intensive organized by Cisco Systems Advanced Networking Group\n"
                "on 2023-11-05. Hands-on exercises covered Cybersecurity and Linux incident triage."
            ),
        },
        # Document 7: Conference Poster
        {
            "category": "CONFERENCE",
            "doc_type": "CONFERENCE_PROGRAM",
            "condition": "CASE_INSENSITIVE",
            "event": "IEEE International Conference on Advanced Computing",
            "org": "Institute of Electrical and Electronics Engineers",
            "rank": "Best Student Poster",
            "level": "INTERNATIONAL",
            "outcome": "RECOGNITION",
            "date": "2024-02-18",
            "skills": ["Computer Vision", "OpenCV"],
            "raw": (
                "IEEE ICAC 2024 — STUDENT AWARDS\n"
                "Conferred upon Candidate: Best Student Poster at the IEEE International Conference on Advanced Computing "
                "sponsored by Institute of Electrical and Electronics Engineers on 2024-02-18. Presented innovative aerial "
                "inspection models using Computer Vision and OpenCV."
            ),
            "source_noise": (
                "ieee icac 2024 — student awards\n"
                "conferred upon candidate: best student poster at the ieee international conference on advanced computing "
                "sponsored by institute of electrical and electronics engineers on 2024-02-18. presented innovative aerial "
                "inspection models using computer vision and opencv."
            ),
        },
        # Document 8: Sports Tournament
        {
            "category": "SPORTS",
            "doc_type": "CERTIFICATE",
            "condition": "CLEAN",
            "event": "All-India Inter-University Badminton Tournament",
            "org": "Association of Indian Universities",
            "rank": "Gold Medal (1st Place)",
            "level": "NATIONAL",
            "outcome": "WINNER",
            "date": "2023-12-08",
            "skills": ["Team Leadership", "Athletic Strategy"],
            "raw": (
                "ASSOCIATION OF INDIAN UNIVERSITIES (AIU)\n"
                "SPORTS BOARD MERIT CERTIFICATE\n"
                "This is to certify that Participant secured Gold Medal (1st Place) in the All-India Inter-University "
                "Badminton Tournament organized by Association of Indian Universities on 2023-12-08."
            ),
            "source_noise": (
                "ASSOCIATION OF INDIAN UNIVERSITIES (AIU)\n"
                "SPORTS BOARD MERIT CERTIFICATE\n\n"
                "This is to certify that Participant secured Gold Medal (1st Place) in the All-India Inter-University "
                "Badminton Tournament organized by Association of Indian Universities on 2023-12-08."
            ),
        },
    ]
    
    # Expand to 75 diverse samples
    doc_id = 1
    for round_idx in range(10):
        for base in templates:
            if len(samples) >= 75:
                break
            year = 2020 + (round_idx % 5)
            doc_uid = f"DOC_EVAL_{doc_id:04d}"
            doc_id += 1
            
            # Vary date and slight wording
            sample_date = f"{year}-{((round_idx * 3) % 12) + 1:02d}-15"
            raw_text = base["raw"].replace("2024-", f"{year}-").replace("2023-", f"{year}-")
            noise_text = base["source_noise"].replace("2024-", f"{year}-").replace("2023-", f"{year}-")
            
            samples.append({
                "document_id": doc_uid,
                "synthetic_status": "EXPLICITLY_SYNTHETIC",
                "document_type": base["doc_type"],
                "quality_condition": base["condition"],
                "category": base["category"],
                "source_text": noise_text,
                "reference_text": raw_text,
                "expected_entities": {
                    "EVENT_NAME": base["event"],
                    "ORGANIZATION": base["org"],
                    "ACHIEVEMENT_DATE": sample_date,
                    "RANK": base["rank"],
                    "LEVEL": base["level"],
                    "OUTCOME": base["outcome"],
                },
                "expected_skills": base["skills"],
            })
            
    with open(OUT_PATH, mode="w", encoding="utf-8") as f:
        for s in samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")
            
    print(f"Extraction evaluation samples written to '{OUT_PATH}' ({len(samples)} samples).")

if __name__ == "__main__":
    build_extraction_samples()

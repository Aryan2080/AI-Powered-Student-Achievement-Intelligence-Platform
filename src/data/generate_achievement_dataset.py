"""
generate_achievement_dataset.py
================================
Synthetic Achievement Classification Dataset Generator
AI-Powered Student Achievement Intelligence Platform — Member 1

Generates ~1,500 realistic, diverse, explicitly synthetic achievement records
across 14 taxonomy categories using scenario-based generation.
Ensures zero category-predictable ID leakage, natural linguistic variety,
boundary ambiguity cases, controlled missingness, and full metadata tracking.
Target: 105-112 unique records per category (Total >= 1,500 unique records).

Usage:
    python src/data/generate_achievement_dataset.py
"""
from __future__ import annotations

import csv
import hashlib
import json
import random
import re
import unicodedata
from datetime import date, timedelta
from pathlib import Path
from typing import Any

# ─────────────────────────────────────────────────────────────────────────────
# Constants & Paths
# ─────────────────────────────────────────────────────────────────────────────

RANDOM_SEED = 42
REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_PROCESSED = REPO_ROOT / "data" / "processed"
DATA_SCHEMA = REPO_ROOT / "data" / "schema"
DATA_MANIFESTS = REPO_ROOT / "data" / "manifests"
DATA_CONFIG = REPO_ROOT / "data" / "config"

GENERATION_ID = "GEN_v1_seed42_20261025"
SCHEMA_VERSION = "1.0.0"
DATASET_VERSION = "achievement_dataset_v1.0.0"

CATEGORIES = [
    "HACKATHON",
    "COMPETITION",
    "RESEARCH_PUBLICATION",
    "PATENT",
    "INTERNSHIP",
    "CERTIFICATION",
    "PROJECT",
    "WORKSHOP",
    "CONFERENCE",
    "LEADERSHIP",
    "SPORTS",
    "CULTURAL",
    "VOLUNTEERING",
    "OTHER",
]

TARGET_PER_CATEGORY = 110  # 14 * 110 = 1,540 raw records targeted

LEVELS = [
    "COLLEGE",
    "UNIVERSITY",
    "LOCAL",
    "DISTRICT",
    "STATE",
    "NATIONAL",
    "INTERNATIONAL",
    "ORGANIZATIONAL",
    "PROFESSIONAL",
    "OTHER",
    "UNKNOWN",
]

OUTCOMES = [
    "PARTICIPATION",
    "COMPLETION",
    "WINNER",
    "FIRST_PLACE",
    "SECOND_PLACE",
    "THIRD_PLACE",
    "FINALIST",
    "PRESENTED",
    "PUBLISHED",
    "GRANTED",
    "FILED",
    "LEADERSHIP",
    "RECOGNITION",
    "OTHER",
    "UNKNOWN",
]

FIELDNAMES = [
    "achievement_id",
    "achievement_text",
    "normalized_text",
    "category",
    "domain",
    "level",
    "outcome",
    "event_name",
    "organization",
    "achievement_date",
    "rank",
    "skills",
    "source_type",
    "evidence_id",
    "source_id",
    "annotation_status",
    "labeler_id",
    "quality_status",
    "record_origin",
    "generation_id",
    "generation_method",
    "source_license",
    "source_url",
    "source_access_date",
    "synthetic_status",
    "validation_flags",
]

rng = random.Random(RANDOM_SEED)

# ─────────────────────────────────────────────────────────────────────────────
# Extensive Entities & Combinatoric Vocabulary Pools
# ─────────────────────────────────────────────────────────────────────────────

TECHNICAL_SKILLS = [
    "Python", "Java", "C++", "C#", "Rust", "Go", "TypeScript", "JavaScript", "Kotlin", "Swift",
    "R", "MATLAB", "SQL", "PostgreSQL", "MySQL", "MongoDB", "Redis", "Cassandra", "Neo4j",
    "PyTorch", "TensorFlow", "Keras", "scikit-learn", "Hugging Face Transformers", "OpenCV",
    "spaCy", "NLTK", "FastAPI", "Django", "Flask", "React", "Next.js", "Node.js", "Docker",
    "Kubernetes", "AWS", "Google Cloud Platform", "Microsoft Azure", "Apache Spark", "Apache Kafka",
    "Flink", "Hadoop", "Airflow", "dbt", "Elasticsearch", "Tableau", "Power BI", "Pandas",
    "NumPy", "SciPy", "Matplotlib", "Seaborn", "Linux", "Git", "CI/CD", "GitHub Actions",
    "Microservices", "RESTful APIs", "GraphQL", "gRPC", "Embedded C", "RTOS", "ROS", "SLAM",
    "Arduino", "Raspberry Pi", "FPGA", "Verilog", "VHDL", "PCB Design", "Computer Vision",
    "Natural Language Processing", "Large Language Models", "Deep Learning", "Reinforcement Learning",
    "Federated Learning", "Graph Neural Networks", "Edge AI", "Cybersecurity", "Penetration Testing",
    "Network Security", "Cryptography", "Blockchain", "Solidity", "Smart Contracts",
]

SOFT_SKILLS = [
    "Team Leadership", "Agile Project Management", "Technical Writing", "Public Speaking",
    "Cross-functional Collaboration", "Stakeholder Communication", "System Architecture",
    "Problem Solving", "Peer Mentoring", "Event Organization", "Strategic Planning",
    "User Research", "Quality Assurance", "Design Thinking", "Scientific Rigor",
]

ALL_SKILL_POOL = TECHNICAL_SKILLS + SOFT_SKILLS

INSTITUTIONS = [
    "National Institute of Technology, Rourkela", "Indian Institute of Information Technology, Allahabad",
    "Vellore Institute of Technology, Vellore", "Birla Institute of Technology and Science, Pilani",
    "Delhi Technological University", "College of Engineering, Guindy",
    "PSG College of Technology, Coimbatore", "Thapar Institute of Engineering and Technology, Patiala",
    "Manipal Institute of Technology, Manipal", "National Institute of Technology, Tiruchirappalli",
    "Jadavpur University Faculty of Engineering", "Indian Institute of Space Science and Technology",
    "National Institute of Technology, Warangal", "Sardar Patel Institute of Technology, Mumbai",
    "Institute of Chemical Technology, Mumbai", "University of Hyderabad School of Computer Sciences",
    "Malaviya National Institute of Technology, Jaipur", "International Institute of Information Technology, Bangalore",
    "Indian Institute of Engineering Science and Technology, Shibpur", "Coimbatore Institute of Technology",
    "RV College of Engineering, Bengaluru", "College of Engineering, Pune (COEP)",
    "BMS College of Engineering, Bengaluru", "SSN College of Engineering, Chennai",
]

CORPORATES_AND_LABS = [
    "Siemens Technology India", "Bosch Engineering Research Center", "Tata Consultancy Services Research",
    "Infosys Center for Emerging Technologies", "Wipro Applied AI Center", "Qualcomm Wireless R&D Lab",
    "Intel Architecture Labs", "Oracle Cloud Infrastructure Team", "Samsung R&D Institute India",
    "Cisco Systems Advanced Networking Group", "Honeywell Aerospace Technologies", "NVIDIA AI Technology Center",
    "Dell Technologies Applied Innovation", "ABB Robotics & Automation Division", "Schneider Electric Innovation Hub",
    "Accenture Technology Innovation Labs", "Philips Healthcare R&D", "Larsen & Toubro Technology Services",
    "Texas Instruments Analog R&D", "SAP Labs India Core Platforms", "Micron Memory & Systems Lab",
    "Applied Materials Nano-Manufacturing Lab", "Cadence Design Systems R&D",
]

NON_PROFITS_AND_NGOS = [
    "Pratham Education Initiative", "Goonj Community Network", "Teach For Youth Alliance",
    "Akshaya Patra Humanitarian Mission", "Youth for Seva Foundation", "U&I Educational Trust",
    "HelpAge Community Outreach", "Robin Hood Army Student Chapter", "Bhookh Relief Foundation",
    "Gram Vikas Rural Tech Initiative", "Child Rights and You (CRY) Volunteer Network",
    "Make A Difference (MAD) Youth Guild", "Society for People's Welfare and Education",
    "Samarthanam Trust for the Disabled", "EcoCare Clean Energy Action Forum", "GreenEarth Student Volunteers",
    "Sankalp Rural Literacy Mission", "Rotaract Youth Action Council",
]

# ─────────────────────────────────────────────────────────────────────────────
# Helper Utilities
# ─────────────────────────────────────────────────────────────────────────────

def _make_id(counter: int) -> str:
    """Generate a clean neutral ID with zero category leakage."""
    return f"ACH{counter:06d}"

def _random_skills(k_min: int = 1, k_max: int = 4) -> list[str]:
    k = rng.randint(k_min, k_max)
    return rng.sample(ALL_SKILL_POOL, min(k, len(ALL_SKILL_POOL)))

def _random_date(start_year: int = 2020, end_year: int = 2025) -> str | None:
    if rng.random() < 0.12:
        return None
    start_d = date(start_year, 1, 1)
    end_d = date(end_year, 10, 20)
    delta_days = (end_d - start_d).days
    random_days = rng.randint(0, delta_days)
    return (start_d + timedelta(days=random_days)).isoformat()

def _clean_text(raw_text: str) -> str:
    text = unicodedata.normalize("NFC", raw_text)
    text = re.sub(r"\s+", " ", text).strip()
    return text

# ─────────────────────────────────────────────────────────────────────────────
# Robust Category Generators with Combinatoric Uniqueness
# ─────────────────────────────────────────────────────────────────────────────

def generate_hackathon_record(idx: int) -> dict[str, Any]:
    prefixes = ["Smart India", "HackX", "InnovateAI", "Global FinTech", "GreenMobility", "BioHealth", "CyberShield", "EduInnovate", "CleanTech", "RoboConstruct", "DataSprint", "CodeGenesis"]
    suffixes = ["Grand Finale", "48-Hour Sprint", "National Challenge", "Innovation Jam", "Buildathon", "Developer Hack", "Protothon", "36-Hour Hack"]
    ev_name = f"{rng.choice(prefixes)} {rng.choice(suffixes)} {rng.choice([2021, 2022, 2023, 2024, 2025])}"
    
    org = rng.choice(INSTITUTIONS + CORPORATES_AND_LABS)
    skills = _random_skills(2, 4)
    domains = ["Artificial Intelligence", "Web & Mobile Development", "Robotics & Autonomous Systems",
               "Smart Infrastructure & Energy", "Healthcare & Medical Informatics", "FinTech & Financial Engineering"]
    domain = rng.choice(domains)
    team_size = rng.randint(3, 5)
    hours = rng.choice([24, 36, 48, 60])
    
    variant = idx % 6
    if variant == 0:
        outcome = "FIRST_PLACE"
        rank = "1st Place"
        text = (f"Led our {team_size}-person student team to 1st place out of {rng.randint(80, 250)} teams at {ev_name}, organized by {org}. "
                f"Within the {hours}-hour continuous development sprint, we engineered a scalable {domain.lower()} solution "
                f"leveraging {skills[0]} and {skills[1]}, complete with automated telemetry and real-time inference.")
    elif variant == 1:
        outcome = "SECOND_PLACE"
        rank = "2nd Place"
        text = (f"Awarded First Runner-Up (2nd position) at {ev_name} hosted by {org}. Our team developed a functional "
                f"prototype for rapid alert dissemination using {skills[0]} and {skills[1]}, successfully defending our technical "
                f"architecture before an industrial judging panel during the final demo session.")
    elif variant == 2:
        outcome = "FINALIST"
        rank = "Top 10 Finalist"
        text = (f"Qualified as one of the top 10 finalist teams at {ev_name} among {rng.randint(200, 600)} applicant projects. "
                f"Constructed an end-to-end working system utilizing {', '.join(skills)} over a {hours}-hour physical build window.")
    elif variant == 3:
        outcome = "WINNER"
        rank = "Track Winner"
        text = (f"Won the Best Innovation Award in the {domain} track at {ev_name}. Collaborated with {team_size-1} peers to implement "
                f"a low-power edge telemetry unit running {skills[0]} and {skills[1]} on embedded processors.")
    elif variant == 4:
        outcome = "PARTICIPATION"
        rank = "Participant"
        text = (f"Participated in {ev_name} held at {org}, serving as the team's core backend architect. Built modular microservices "
                f"and responsive data streaming endpoints using {skills[0]} during the intensive {hours}-hour build challenge.")
    else:
        outcome = "RECOGNITION"
        rank = "Special Mention"
        text = (f"Received Special Jury Recognition at the {ev_name} {hours}-hour sprint for outstanding UI/UX and fault-tolerant "
                f"system reliability. Built an assistive platform incorporating {skills[0]} and {skills[1]}.")

    return {
        "achievement_text": text,
        "category": "HACKATHON",
        "domain": domain,
        "level": rng.choice(["STATE", "NATIONAL", "INTERNATIONAL", "UNIVERSITY"]),
        "outcome": outcome,
        "event_name": ev_name,
        "organization": org,
        "achievement_date": _random_date(2021, 2025),
        "rank": rank,
        "skills": "|".join(skills),
        "source_type": rng.choice(["CERTIFICATE", "PROJECT_DESCRIPTION", "SYNTHETIC_RECORD"]),
    }

def generate_competition_record(idx: int) -> dict[str, Any]:
    comp_types = [
        ("ACM-ICPC Asia Regional Preliminary", "INTERNATIONAL", "Software Engineering"),
        ("National Undergraduate Data Science Challenge", "NATIONAL", "Data Science & Analytics"),
        ("TCS CodeVita Global Coding Arena", "INTERNATIONAL", "Software Engineering"),
        ("All-India Inter-University Robotics Cup", "NATIONAL", "Robotics & Autonomous Systems"),
        ("National Algorithmic Speed Challenge", "NATIONAL", "Software Engineering"),
        ("Inter-Collegiate Business Analytics Olympiad", "NATIONAL", "Data Science & Analytics"),
        ("State Engineering Mathematics Olympiad", "STATE", "Higher Education & Leadership"),
        ("Kaggle Community Predictive Modeling Challenge", "INTERNATIONAL", "Machine Learning"),
        ("National Cybersecurity CTF Invitational", "NATIONAL", "Cybersecurity & Information Assurance"),
        ("University Model United Nations Security Debate", "UNIVERSITY", "Higher Education & Leadership"),
        ("National Collegiate Embedded Systems Design Contest", "NATIONAL", "Internet of Things & Embedded Systems"),
        ("State-Level Algorithmic Problem Solving Invitational", "STATE", "Software Engineering"),
    ]
    base_name, default_level, default_domain = rng.choice(comp_types)
    year = rng.choice([2021, 2022, 2023, 2024, 2025])
    ev_name = f"{base_name} {year}"
    org = rng.choice(INSTITUTIONS + CORPORATES_AND_LABS)
    skills = _random_skills(1, 3)
    entrants = rng.randint(250, 1500)
    
    variant = idx % 6
    if variant == 0:
        outcome = "WINNER"
        rank = "1st Place"
        text = (f"Clinched First Place in the {ev_name} after solving 9 out of 10 complex algorithmic problems within "
                f"the 5-hour time window, beating {entrants} university teams nationally.")
    elif variant == 1:
        outcome = "SECOND_PLACE"
        rank = "2nd Place"
        text = (f"Achieved 2nd Place nationally in the {ev_name} organized by {org}. Engineered high-throughput algorithms "
                f"in {skills[0]} and executed rigorous complexity optimizations to clear held-out performance benchmarks.")
    elif variant == 2:
        outcome = "THIRD_PLACE"
        rank = "3rd Place"
        text = (f"Secured Bronze Medal (3rd place) in the {ev_name}. Built ensemble regression pipelines using {skills[0]} "
                f"evaluating on private test leaderboards across {entrants} competitive entrants.")
    elif variant == 3:
        outcome = "FINALIST"
        rank = "National Finalist"
        text = (f"Qualified as a National Finalist in the {ev_name}. Solved advanced graph theory and dynamic programming challenges "
                f"under timed competition constraints using {skills[0]}.")
    elif variant == 4:
        outcome = "PARTICIPATION"
        rank = "Top 5%"
        text = (f"Finished in the top 5th percentile at {ev_name} amongst over {entrants} participating undergraduate coders, "
                f"successfully passing 8 automated verification test suites.")
    else:
        outcome = "RECOGNITION"
        rank = "Honorable Mention"
        text = (f"Conferred Honorable Mention at {ev_name} for formulating an optimal linear-time solution in {skills[0]} "
                f"adjudicated against rigid time and memory resource ceilings.")

    return {
        "achievement_text": text,
        "category": "COMPETITION",
        "domain": default_domain,
        "level": default_level,
        "outcome": outcome,
        "event_name": ev_name,
        "organization": org,
        "achievement_date": _random_date(2021, 2025),
        "rank": rank,
        "skills": "|".join(skills),
        "source_type": rng.choice(["CERTIFICATE", "MANUAL_RECORD", "SYNTHETIC_RECORD"]),
    }

def generate_research_publication_record(idx: int) -> dict[str, Any]:
    venues = [
        ("IEEE Transactions on Artificial Intelligence", "INTERNATIONAL", "Journal Article"),
        ("ACM International Conference on Information and Knowledge Management (CIKM)", "INTERNATIONAL", "Conference Paper"),
        ("Springer Nature Journal of Medical Systems", "INTERNATIONAL", "Journal Article"),
        ("Elsevier Biomedical Signal Processing and Control", "INTERNATIONAL", "Journal Article"),
        ("IEEE International Conference on Big Data (BigData)", "INTERNATIONAL", "Conference Paper"),
        ("International Joint Conference on Neural Networks (IJCNN)", "INTERNATIONAL", "Conference Paper"),
        ("ACL Findings: Association for Computational Linguistics", "INTERNATIONAL", "Conference Paper"),
        ("arXiv cs.CV e-Print Repository (Archival Preprint)", "INTERNATIONAL", "Preprint"),
        ("IEEE Access Multidisciplinary Journal", "INTERNATIONAL", "Journal Article"),
        ("Proceedings of the Indian Academy of Sciences (Technological Sciences)", "NATIONAL", "Journal Article"),
        ("Elsevier Computer Communications and Networking", "INTERNATIONAL", "Journal Article"),
        ("IEEE Internet of Things Journal", "INTERNATIONAL", "Journal Article"),
    ]
    venue_name, default_level, pub_type = rng.choice(venues)
    org = rng.choice(INSTITUTIONS)
    skills = _random_skills(2, 4)
    domains = ["Natural Language Processing", "Computer Vision", "Machine Learning",
               "Healthcare & Medical Informatics", "Cybersecurity & Information Assurance", "Internet of Things & Embedded Systems"]
    domain = rng.choice(domains)
    
    topics = [
        "Low-Resource Clinical Entity Recognition", "Adversarial Robustness in Graph Attention Networks",
        "Real-Time Defect Segmentation in Aerial Photovoltaic Arrays", "Federated Differential Privacy in Edge IoT",
        "Multimodal Emotion Recognition with Sparse Attention", "Zero-Shot Indic Language Cross-Lingual Transfer",
        "Energy-Aware Routing in High-Density Wireless Sensor Grids", "Automated EEG Anomaly Detection Using Wavelet Neural Networks"
    ]
    topic = rng.choice(topics)
    pct = rng.randint(4, 15)
    
    variant = idx % 5
    if variant == 0:
        outcome = "PUBLISHED"
        text = (f"Published a peer-reviewed research paper titled '{topic}' in {venue_name}. Conducted extensive ablation studies "
                f"using {skills[0]} and {skills[1]}, demonstrating a {pct}.2% improvement in F1-score over existing published baselines.")
    elif variant == 1:
        outcome = "PUBLISHED"
        text = (f"First author on peer-reviewed study '{topic}' accepted for publication in {venue_name}. Formulated a semi-supervised "
                f"pipeline using {skills[0]}, supervised by faculty from {org}.")
    elif variant == 2:
        outcome = "PUBLISHED"
        text = (f"Co-authored research paper in {venue_name} focusing on {domain.lower()} architectures. Designed dataset curation pipelines, "
                f"conducted cross-validation experiments with {skills[0]}, and authored methodology and experimental analysis sections.")
    elif variant == 3:
        outcome = "PUBLISHED"
        text = (f"Presented and published our paper in {venue_name} ({pub_type}). Addressed algorithmic bottlenecks in "
                f"{topic.lower()} using {skills[0]} and {skills[1]}, followed by formal peer defense.")
    else:
        outcome = "PUBLISHED"
        text = (f"Authored archival paper titled 'Benchmarking Multi-modal Foundation Models for {topic}', published in "
                f"{venue_name}. Implemented zero-shot evaluation protocols using {skills[0]} across standardized public benchmarks.")

    return {
        "achievement_text": text,
        "category": "RESEARCH_PUBLICATION",
        "domain": domain,
        "level": default_level,
        "outcome": outcome,
        "event_name": venue_name,
        "organization": org,
        "achievement_date": _random_date(2021, 2025),
        "rank": "None",
        "skills": "|".join(skills),
        "source_type": "PUBLICATION_METADATA",
    }

def generate_patent_record(idx: int) -> dict[str, Any]:
    offices = [
        ("Indian Patent Office (IPO)", "NATIONAL"),
        ("United States Patent and Trademark Office (USPTO)", "INTERNATIONAL"),
        ("World Intellectual Property Organization (WIPO - PCT)", "INTERNATIONAL"),
        ("European Patent Office (EPO)", "INTERNATIONAL"),
    ]
    office_name, default_level = rng.choice(offices)
    org = rng.choice(INSTITUTIONS + CORPORATES_AND_LABS)
    skills = _random_skills(1, 3)
    domains = ["Robotics & Autonomous Systems", "Internet of Things & Embedded Systems",
               "Healthcare & Medical Informatics", "Smart Infrastructure & Energy", "Electronics & VLSI Design"]
    domain = rng.choice(domains)
    app_num = f"{rng.randint(2021, 2025)}{rng.randint(100000, 999999)}"
    
    inventions = [
        "A Non-Invasive Continuous Blood Glucose Telemetry Apparatus Utilizing Multi-Spectral Optical Sensors",
        "An Intelligent Hybrid Energy Harvesting Circuit for Wireless Sensor Nodes in Precision Agriculture",
        "Method and System for Automated Dynamic Bandwidth Allocation in High-Density IoT Mesh Topologies",
        "A Fault-Tolerant Edge Computing Architecture for Real-Time Robotic Anomaly Intervention",
        "Apparatus and Embedded Logic for Dynamic Battery Thermal Management in Electric Vehicles",
        "An Adaptive Impedance-Matching System for Wireless Power Transfer in Implantable Medical Devices",
        "Method for Hardware-Accelerated Cryptographic Key Exchange in Low-Resource Microcontrollers",
    ]
    title = rng.choice(inventions)
    
    variant = idx % 4
    if variant == 0:
        outcome = "FILED"
        rank = "Patent Application Filed"
        text = (f"Co-inventor on patent application #{app_num} filed with the {office_name}: '{title}'. Engineered sensor hardware interface "
                f"and low-power firmware in {skills[0]} in conjunction with {org}.")
    elif variant == 1:
        outcome = "GRANTED"
        rank = "Patent Granted"
        text = (f"Granted utility patent from {office_name} (Patent #{app_num}) for '{title}'. Designed power-distribution switching topology "
                f"and validated simulation benchmarks with researchers at {org}.")
    elif variant == 2:
        outcome = "FILED"
        rank = "Published Application"
        text = (f"Patent application published by {office_name} (App No. {app_num}): '{title}', conceptualized and prototyped in collaboration "
                f"with mentors at {org} using {skills[0]}.")
    else:
        outcome = "FILED"
        rank = "Provisional Specification"
        text = (f"Filed provisional patent specification with {office_name} (Filing No. {app_num}) for '{title}', implementing firmware "
                f"routines programmed in {skills[0]} for low-latency operational intervention.")

    return {
        "achievement_text": text,
        "category": "PATENT",
        "domain": domain,
        "level": default_level,
        "outcome": outcome,
        "event_name": f"{office_name} Filing",
        "organization": org,
        "achievement_date": _random_date(2021, 2025),
        "rank": rank,
        "skills": "|".join(skills),
        "source_type": "SYNTHETIC_RECORD",
    }

def generate_internship_record(idx: int) -> dict[str, Any]:
    roles = [
        "Machine Learning Engineering Intern", "Software Development Engineer Intern",
        "Data Engineering Intern", "Embedded Systems R&D Intern",
        "Cybersecurity Analyst Intern", "Cloud Infrastructure Intern",
        "Full Stack Development Intern", "AI Research Intern",
        "Autonomous Vehicles Perception Intern", "DevOps & SRE Intern",
        "Firmware Engineering Intern", "Site Reliability Engineering Intern",
    ]
    role = rng.choice(roles)
    org = rng.choice(CORPORATES_AND_LABS)
    skills = _random_skills(2, 5)
    domains = ["Software Engineering", "Cloud & Distributed Computing", "Machine Learning",
               "Data Science & Analytics", "Cybersecurity & Information Assurance", "Robotics & Autonomous Systems"]
    domain = rng.choice(domains)
    duration = rng.choice(["8 weeks", "10 weeks", "12 weeks", "6 months", "3 months", "4 months"])
    latency_cut = rng.randint(18, 45)
    tb_vol = rng.randint(2, 10)
    
    variant = idx % 5
    if variant == 0:
        outcome = "COMPLETION"
        text = (f"Completed a {duration} on-site internship as {role} at {org}. Spearheaded the migration of legacy microservices "
                f"to containerized deployments using {skills[0]} and {skills[1]}, cutting endpoint latency by {latency_cut}% across production environments.")
    elif variant == 1:
        outcome = "RECOGNITION"
        text = (f"Earned Outstanding Intern Performance Rating during my {duration} stint as {role} at {org}. Designed automated "
                f"data validation pipelines in {skills[0]} processing over {tb_vol} TB of daily telemetry logs.")
    elif variant == 2:
        outcome = "COMPLETION"
        text = (f"Served as {role} at {org} for {duration}. Developed and unit-tested fault-tolerant backend modules using {skills[0]} "
                f"and {skills[1]}, adhering to strict enterprise agile sprints and code review governance.")
    elif variant == 3:
        outcome = "COMPLETION"
        text = (f"Successfully concluded a {duration} research-oriented internship at {org}. Integrated real-time streaming architectures "
                f"with {skills[0]} and authored comprehensive internal system documentation.")
    else:
        outcome = "RECOGNITION"
        text = (f"Offered a Pre-Placement Offer (PPO) following exemplary execution as {role} during a {duration} internship with {org}. "
                f"Architected an internal developer dashboard using {skills[0]} and {skills[1]}.")

    return {
        "achievement_text": text,
        "category": "INTERNSHIP",
        "domain": domain,
        "level": "PROFESSIONAL",
        "outcome": outcome,
        "event_name": None,
        "organization": org,
        "achievement_date": _random_date(2021, 2025),
        "rank": "None",
        "skills": "|".join(skills),
        "source_type": rng.choice(["CERTIFICATE", "RESUME_TEXT", "SYNTHETIC_RECORD"]),
    }

def generate_certification_record(idx: int) -> dict[str, Any]:
    certs = [
        ("AWS Certified Solutions Architect - Associate", "Amazon Web Services", "Cloud & Distributed Computing", ["AWS", "Docker", "Kubernetes", "Linux"]),
        ("Google Cloud Professional Data Engineer", "Google Cloud", "Data Science & Analytics", ["Google Cloud Platform", "Apache Spark", "SQL", "BigQuery"]),
        ("Microsoft Certified: Azure AI Engineer Associate", "Microsoft", "Artificial Intelligence", ["Microsoft Azure", "Python", "Computer Vision", "NLP"]),
        ("Certified Kubernetes Administrator (CKA)", "Cloud Native Computing Foundation", "Cloud & Distributed Computing", ["Kubernetes", "Docker", "Linux"]),
        ("TensorFlow Developer Certificate", "Google Brain", "Machine Learning", ["TensorFlow", "Keras", "Deep Learning", "Python"]),
        ("Deep Learning Specialization", "DeepLearning.AI / Coursera", "Deep Learning", ["PyTorch", "Deep Learning", "Convolutional Neural Networks", "Python"]),
        ("Certified Information Systems Security Professional Associate (CISSP)", "ISC2", "Cybersecurity & Information Assurance", ["Network Security", "Cryptography", "Cybersecurity"]),
        ("Oracle Certified Professional: Java SE 11 Developer", "Oracle Corporation", "Software Engineering", ["Java", "OOP", "SQL"]),
        ("HashiCorp Certified: Terraform Associate", "HashiCorp", "Cloud & Distributed Computing", ["CI/CD", "Cloud Infrastructure", "DevOps"]),
        ("NVIDIA Fundamentals of Deep Learning", "NVIDIA Deep Learning Institute", "Artificial Intelligence", ["PyTorch", "GPU Acceleration", "Computer Vision"]),
        ("Red Hat Certified System Administrator (RHCSA)", "Red Hat", "Cloud & Distributed Computing", ["Linux", "Bash", "System Administration"]),
        ("Databricks Certified Associate Developer for Apache Spark", "Databricks", "Data Science & Analytics", ["Apache Spark", "Python", "Data Pipelines"]),
        ("CompTIA Security+ Certification (SY0-601)", "CompTIA", "Cybersecurity & Information Assurance", ["Network Security", "Vulnerability Scanning", "Cybersecurity"]),
        ("Professional Scrum Master I (PSM I)", "Scrum.org", "Software Engineering", ["Agile Project Management", "Scrum", "Team Leadership"]),
        ("Meta Back-End Developer Professional Certificate", "Meta / Coursera", "Web & Mobile Development", ["Django", "Python", "RESTful APIs", "SQL"]),
    ]
    cert_name, issuer, default_domain, cert_skills = rng.choice(certs)
    skills = rng.sample(cert_skills, min(len(cert_skills), rng.randint(2, 4)))
    hours = rng.choice([40, 50, 60, 80, 100])
    score = rng.randint(84, 98)
    cred_id = f"{issuer[:3].upper()}-{rng.randint(100000, 999999)}"
    
    variant = idx % 5
    if variant == 0:
        text = (f"Successfully passed the proctored certification examination for {cert_name} (Credential #{cred_id}), issued by {issuer}. "
                f"Demonstrated architectural mastery in high-availability deployments and security configurations using {skills[0]} and {skills[1]}.")
    elif variant == 1:
        text = (f"Achieved professional industry credential: {cert_name} ({issuer}, Verification ID: {cred_id}). Completed {hours}+ hours of "
                f"coursework, hands-on lab evaluations, and a 3-hour invigilated technical evaluation with a score of {score}%.")
    elif variant == 2:
        text = (f"Completed verified credential program for {cert_name} from {issuer}. Validated practical competency in building "
                f"scalable pipelines with {skills[0]} and implementing enterprise best practices (License {cred_id}).")
    elif variant == 3:
        text = (f"Earned industry certification {cert_name} with an examination grade of {score}%. Hands-on invigilated exam assessed "
                f"fault recovery, troubleshooting, and container orchestration using {skills[0]}.")
    else:
        text = (f"Awarded verified certificate for {cert_name} by {issuer}. Successfully cleared {hours} hours of practical performance "
                f"tasks covering distributed architectures and security controls with {skills[0]} and {skills[1]}.")

    return {
        "achievement_text": text,
        "category": "CERTIFICATION",
        "domain": default_domain,
        "level": "PROFESSIONAL",
        "outcome": "COMPLETION",
        "event_name": cert_name,
        "organization": issuer,
        "achievement_date": _random_date(2021, 2025),
        "rank": "None",
        "skills": "|".join(skills),
        "source_type": "CERTIFICATE",
    }

def generate_project_record(idx: int) -> dict[str, Any]:
    project_types = [
        "Final Year Capstone Project", "Undergraduate Honors Thesis Project",
        "Independent Open-Source Software Contribution", "Interdisciplinary Research Prototype",
        "Departmental Engineering Innovation Project", "Self-Directed Practical Implementation",
        "Multi-Semester Collaborative Engineering Project",
    ]
    p_type = rng.choice(project_types)
    org = rng.choice(INSTITUTIONS)
    skills = _random_skills(2, 5)
    domains = ["Robotics & Autonomous Systems", "Computer Vision", "Natural Language Processing",
               "Smart Infrastructure & Energy", "Web & Mobile Development", "Cybersecurity & Information Assurance",
               "Internet of Things & Embedded Systems"]
    domain = rng.choice(domains)
    
    ideas = [
        ("autonomous agricultural drone survey platform", "low-latency visual telemetry across 50 hectares"),
        ("distributed honeypot intrusion detection network", "modular sensor traps capturing 100,000+ attack vectors"),
        ("high-performance vector indexing microservice", "nearest-neighbor lookups with sub-5ms latency"),
        ("intelligent Braille-to-speech assistive tablet device", "tactile sensor arrays delivering speech in under 120ms"),
        ("dual-axis solar tracking inverter with IoT telemetry", "dynamic irradiance optimization yielding 14% higher power"),
        ("automated clinical triage prioritization pipeline", "semantic symptom extraction handling 500 patient records per minute"),
        ("decentralized verifiable credential issuance ledger", "zero-knowledge proof verification on mobile hardware"),
    ]
    proj_desc, spec_outcome = rng.choice(ideas)
    
    variant = idx % 5
    if variant == 0:
        outcome = "COMPLETION"
        text = (f"Engineered an {proj_desc} as our {p_type} at {org}. Designed low-latency "
                f"modules using {skills[0]} and {skills[1]}, delivering {spec_outcome}.")
    elif variant == 1:
        outcome = "RECOGNITION"
        text = (f"Awarded Best Departmental Capstone Project for developing an {proj_desc}. "
                f"Constructed modular services in {skills[0]} and {skills[1]} achieving {spec_outcome}.")
    elif variant == 2:
        outcome = "COMPLETION"
        text = (f"Developed and open-sourced an {proj_desc} utilizing {skills[0]} as a {p_type} at {org}. "
                f"Maintained clean test suites, achieved over {rng.randint(200, 1500)} GitHub stars, and delivered {spec_outcome}.")
    elif variant == 3:
        outcome = "COMPLETION"
        text = (f"Constructed an {proj_desc} as an {p_type} supervised by {org} faculty. Integrated system logic "
                f"programmed in {skills[0]} and {skills[1]}, completing thorough hardware-in-the-loop validation.")
    else:
        outcome = "RECOGNITION"
        text = (f"Fabricated an {proj_desc} for our {p_type} at {org}. Evaluated performance with {skills[0]}, "
                f"securing an A+ distinction from external industry evaluators.")

    return {
        "achievement_text": text,
        "category": "PROJECT",
        "domain": domain,
        "level": rng.choice(["COLLEGE", "UNIVERSITY", "ORGANIZATIONAL"]),
        "outcome": outcome,
        "event_name": None,
        "organization": org,
        "achievement_date": _random_date(2021, 2025),
        "rank": "None",
        "skills": "|".join(skills),
        "source_type": "PROJECT_DESCRIPTION",
    }

def generate_workshop_record(idx: int) -> dict[str, Any]:
    workshops = [
        ("Hands-On Deep Reinforcement Learning Intensive", "Artificial Intelligence", ["PyTorch", "Reinforcement Learning", "Python"]),
        ("Enterprise Microservices Architecture with Kubernetes", "Cloud & Distributed Computing", ["Kubernetes", "Docker", "Microservices"]),
        ("Hardware-Accelerated Computer Vision with Edge GPUs", "Computer Vision", ["OpenCV", "Edge AI", "C++"]),
        ("Advanced Cyber Threat Hunting and Incident Response", "Cybersecurity & Information Assurance", ["Network Security", "Penetration Testing", "Linux"]),
        ("Autonomous Robotics Navigation with ROS 2 and Gazebo", "Robotics & Autonomous Systems", ["ROS", "SLAM", "C++"]),
        ("Full-Stack Modern Web Engineering Masterclass", "Web & Mobile Development", ["React", "TypeScript", "Node.js"]),
        ("FPGA Design for High-Speed Digital Signal Processing", "Electronics & VLSI Design", ["FPGA", "Verilog", "Embedded Systems"]),
        ("Practical Large Language Model Alignment and RAG Systems", "Natural Language Processing", ["Large Language Models", "Python", "Vector Databases"]),
        ("Big Data Stream Analytics with Apache Kafka and Flink", "Data Science & Analytics", ["Apache Kafka", "Flink", "Java"]),
        ("Embedded Firmware Development with FreeRTOS", "Internet of Things & Embedded Systems", ["Embedded C", "RTOS", "ARM Cortex"]),
    ]
    ws_name, default_domain, ws_skills = rng.choice(workshops)
    org = rng.choice(INSTITUTIONS + CORPORATES_AND_LABS)
    skills = rng.sample(ws_skills, min(len(ws_skills), rng.randint(2, 3)))
    duration = rng.choice(["2-day", "3-day", "5-day", "weekend", "week-long"])
    year = rng.choice([2021, 2022, 2023, 2024, 2025])
    
    variant = idx % 4
    if variant == 0:
        outcome = "COMPLETION"
        text = (f"Completed the intensive {duration} technical workshop on '{ws_name}' ({year}) conducted by {org}. Built and evaluated "
                f"hands-on lab implementations using {skills[0]} and {skills[1]}.")
    elif variant == 1:
        outcome = "PARTICIPATION"
        text = (f"Participated in the {duration} advanced training program on '{ws_name}' hosted at {org}. Executed practical "
                f"exercises in system profiling, deployment scaling, and pipeline configuration with {skills[0]}.")
    elif variant == 2:
        outcome = "COMPLETION"
        text = (f"Awarded Certificate of Completion for the '{ws_name}' workshop organized by {org}. Completed all laboratory "
                f"milestones and submitted an end-of-workshop project implementing {skills[0]}.")
    else:
        outcome = "PARTICIPATION"
        text = (f"Attended hands-on technical workshop on '{ws_name}', facilitated by engineering leads from {org}. Explored "
                f"industrial production architectures and built prototype components with {skills[0]}.")

    return {
        "achievement_text": text,
        "category": "WORKSHOP",
        "domain": default_domain,
        "level": rng.choice(["COLLEGE", "UNIVERSITY", "NATIONAL", "ORGANIZATIONAL"]),
        "outcome": outcome,
        "event_name": f"{ws_name} ({year})",
        "organization": org,
        "achievement_date": _random_date(2021, 2025),
        "rank": "None",
        "skills": "|".join(skills),
        "source_type": "CERTIFICATE",
    }

def generate_conference_record(idx: int) -> dict[str, Any]:
    confs = [
        ("IEEE International Conference on Advanced Computing and Communications", "INTERNATIONAL"),
        ("National Symposium on VLSI and Embedded Systems", "NATIONAL"),
        ("ACM Student Research Colloquium on Artificial Intelligence", "NATIONAL"),
        ("International Conference on Cloud Computing and Big Data Analytics", "INTERNATIONAL"),
        ("All-India Conference on Sustainable Engineering Innovations", "NATIONAL"),
        ("Asia-Pacific Robotics and Automation Technical Summit", "INTERNATIONAL"),
        ("International Symposium on Cyber Defense and Digital Forensics", "INTERNATIONAL"),
        ("Annual National Biomedical Engineering Colloquium", "NATIONAL"),
        ("IEEE International Conference on Signal Processing and Communications", "INTERNATIONAL"),
        ("National Conference on Emerging Trends in Computing Technologies", "NATIONAL"),
    ]
    conf_name, default_level = rng.choice(confs)
    year = rng.choice([2021, 2022, 2023, 2024, 2025])
    conf_full = f"{conf_name} ({year})"
    org = rng.choice(INSTITUTIONS)
    skills = _random_skills(1, 3)
    domains = ["Artificial Intelligence", "Robotics & Autonomous Systems", "Cloud & Distributed Computing",
               "Cybersecurity & Information Assurance", "Healthcare & Medical Informatics", "Electronics & VLSI Design"]
    domain = rng.choice(domains)
    delegates = rng.randint(150, 600)
    
    variant = idx % 5
    if variant == 0:
        outcome = "PRESENTED"
        rank = "Oral Presenter"
        text = (f"Delivered an oral presentation at {conf_full} held at {org}. Presented our preliminary experimental findings "
                f"on {domain.lower()} architectures and fielded technical inquiries during the peer question session.")
    elif variant == 1:
        outcome = "PRESENTED"
        rank = "Poster Presenter"
        text = (f"Presented an interactive research poster at the {conf_full}. Showcased benchmark comparisons of {skills[0]} "
                f"algorithms to over {delegates} visiting delegates and faculty researchers.")
    elif variant == 2:
        outcome = "PARTICIPATION"
        rank = "Student Delegate"
        text = (f"Attended {conf_full} as an official student delegate representing {org}. Participated in keynote plenary sessions "
                f"and technical tracks regarding emerging trends in {domain.lower()}.")
    elif variant == 3:
        outcome = "RECOGNITION"
        rank = "Best Poster Presentation"
        text = (f"Conferred the Best Student Poster Award at {conf_full}. Evaluated by the organizing committee on clarity, "
                f"depth of technical analysis in {skills[0]}, and oral defense.")
    else:
        outcome = "RECOGNITION"
        rank = "Student Volunteer Lead"
        text = (f"Served as Student Technical Coordinator for {conf_full} organized by {org}. Facilitated audiovisual and technical "
                f"session handoffs for 14 parallel research presentation tracks.")

    return {
        "achievement_text": text,
        "category": "CONFERENCE",
        "domain": domain,
        "level": default_level,
        "outcome": outcome,
        "event_name": conf_full,
        "organization": org,
        "achievement_date": _random_date(2021, 2025),
        "rank": rank,
        "skills": "|".join(skills),
        "source_type": rng.choice(["CERTIFICATE", "MANUAL_RECORD", "SYNTHETIC_RECORD"]),
    }

def generate_leadership_record(idx: int) -> dict[str, Any]:
    roles = [
        ("President", "ACM Student Chapter"),
        ("Chairperson", "IEEE Student Branch"),
        ("Lead Organizer", "Annual National Collegiate Technical Fest"),
        ("Head of Technical Operations", "University Robotics Club"),
        ("Secretary", "Developer Student Club (GDSC)"),
        ("Convener", "Campus Open-Source Developers Guild"),
        ("Chief Coordinator", "University Innovation and Entrepreneurship Cell"),
        ("Captain", "Inter-Collegiate Coding Team"),
        ("Vice President", "Women in Technology Campus Forum"),
        ("Editor-in-Chief", "Faculty of Engineering Annual Technical Journal"),
        ("Director of Student Affairs", "Collegiate Technical Council"),
        ("Head Coordinator", "University AI Research Study Circle"),
    ]
    role_title, entity_name = rng.choice(roles)
    org = rng.choice(INSTITUTIONS)
    skills = _random_skills(1, 3)
    domain = rng.choice(["Higher Education & Leadership", "Software Engineering", "Artificial Intelligence",
                        "Robotics & Autonomous Systems", "Community Service & Civic Engagement"])
    year_span = rng.choice(["2021-2022", "2022-2023", "2023-2024", "2024-2025"])
    team_members = rng.randint(18, 55)
    participants = rng.randint(1200, 3500)
    
    variant = idx % 4
    if variant == 0:
        text = (f"Elected as {role_title} of {entity_name} at {org} for the {year_span} academic session. Directed a core team of {team_members} "
                f"student leads, oversaw an operating budget of INR {rng.randint(2, 8)}.5 Lakhs, and hosted 16 technical events engaging {participants}+ participants.")
    elif variant == 1:
        text = (f"Served as {role_title} of {entity_name}. Mentored junior engineering students in {skills[0]}, initiated peer study groups, "
                f"and established collaborative industry guest speaker sessions with senior engineering leaders during the {year_span} tenure.")
    elif variant == 2:
        text = (f"Spearheaded operations as {role_title} for {entity_name} across the campus. Successfully coordinated logistics, corporate "
                f"sponsorship outreach, and technical hackathon logistics for over {participants} visiting delegates during {year_span}.")
    else:
        text = (f"Held the post of {role_title} in {entity_name} at {org} ({year_span}). Structured hands-on coding bootcamps covering {skills[0]} "
                f"and instituted an automated peer assignment grading portal for club members.")

    return {
        "achievement_text": text,
        "category": "LEADERSHIP",
        "domain": domain,
        "level": rng.choice(["COLLEGE", "UNIVERSITY", "STATE"]),
        "outcome": "LEADERSHIP",
        "event_name": entity_name,
        "organization": org,
        "achievement_date": _random_date(2021, 2025),
        "rank": role_title,
        "skills": "|".join(skills),
        "source_type": rng.choice(["CERTIFICATE", "MANUAL_RECORD", "SYNTHETIC_RECORD"]),
    }

def generate_sports_record(idx: int) -> dict[str, Any]:
    sports_events = [
        ("All-India Inter-University Badminton Tournament", "NATIONAL", "Badminton"),
        ("State Collegiate Table Tennis Championship", "STATE", "Table Tennis"),
        ("Inter-Zone University Basketball Tournament", "STATE", "Basketball"),
        ("National University Athletics Meet (400m Sprint)", "NATIONAL", "Athletics"),
        ("State Inter-Engineering Football Championship", "STATE", "Football"),
        ("District Collegiate Chess Championship", "DISTRICT", "Chess"),
        ("All-India Invitational University Volleyball Cup", "NATIONAL", "Volleyball"),
        ("Inter-Collegiate Lawn Tennis Tournament", "UNIVERSITY", "Tennis"),
        ("State University Aquatics Meet (100m Freestyle)", "STATE", "Swimming"),
        ("Inter-Department Annual Athletic Games", "COLLEGE", "Athletics"),
        ("National Inter-Collegiate Cricket Trophy", "NATIONAL", "Cricket"),
        ("State Taekwondo Martial Arts Invitational", "STATE", "Martial Arts"),
        ("University Cross-Country 10km Marathon", "UNIVERSITY", "Athletics"),
        ("All-India Inter-Engineering Badminton Open", "NATIONAL", "Badminton"),
    ]
    ev_name, default_level, sport_name = rng.choice(sports_events)
    year = rng.choice([2021, 2022, 2023, 2024, 2025])
    full_ev = f"{ev_name} ({year})"
    org = rng.choice(INSTITUTIONS)
    rounds = rng.randint(4, 7)
    
    variant = idx % 5
    if variant == 0:
        outcome = "WINNER"
        rank = "1 (Gold Medal)"
        text = (f"Won the Gold Medal (1st place) in {sport_name} at the {full_ev}. Competed across {rounds} single-elimination rounds "
                f"representing {org} and maintained undefeated match records throughout the tournament.")
    elif variant == 1:
        outcome = "SECOND_PLACE"
        rank = "2 (Silver Medal)"
        text = (f"Secured Silver Medal (2nd position) at the {full_ev}. Represented our university squad across competitive "
                f"inter-state fixtures, scoring critical points during the semi-final matches.")
    elif variant == 2:
        outcome = "THIRD_PLACE"
        rank = "3 (Bronze Medal)"
        text = (f"Earned Bronze Medal (3rd place) in the {full_ev} hosted by {org}, emerging victorious in the third-place playoff match "
                f"after a closely contested finish.")
    elif variant == 3:
        outcome = "PARTICIPATION"
        rank = "Quarterfinalist"
        text = (f"Represented {org} in {sport_name} at the {full_ev}. Advanced to the tournament quarterfinals after clearing rigorous "
                f"regional qualifying trials.")
    else:
        outcome = "RECOGNITION"
        rank = "Team Captain / MVP"
        text = (f"Captained the university {sport_name} team to victory in the finals of {full_ev}. Named Most Valuable Player (MVP) "
                f"of the tournament for exceptional tactical court leadership and teamwork.")

    return {
        "achievement_text": text,
        "category": "SPORTS",
        "domain": "Sports & Athletics",
        "level": default_level,
        "outcome": outcome,
        "event_name": full_ev,
        "organization": org,
        "achievement_date": _random_date(2021, 2025),
        "rank": rank,
        "skills": "Athletic Discipline|Team Strategy|Endurance",
        "source_type": "CERTIFICATE",
    }

def generate_cultural_record(idx: int) -> dict[str, Any]:
    cultural_events = [
        ("National Inter-University Youth Cultural Festival (AIU)", "NATIONAL", "Classical Music Vocal"),
        ("State Collegiate Classical Dance Competition", "STATE", "Bharatanatyam Dance"),
        ("All-India Inter-Collegiate Literary and Debate Championship", "NATIONAL", "Parliamentary Debate"),
        ("National Student Drama and One-Act Play Festival", "NATIONAL", "Theatrical Drama"),
        ("Inter-University Western Band Showcase", "UNIVERSITY", "Instrumental Music"),
        ("State Photographic and Fine Arts Salon", "STATE", "Digital Photography"),
        ("Inter-Collegiate Creative Writing and Poetry Slam", "DISTRICT", "Creative Writing"),
        ("University Annual Cultural Fest (Gala Finale)", "UNIVERSITY", "Contemporary Dance"),
        ("National Inter-Collegiate Street Play Competition (Nukkad Natak)", "NATIONAL", "Street Theatre"),
        ("All-India Classical Instrumental Arts Sabha", "NATIONAL", "Carnatic Violin"),
        ("State Youth Elocution and Oratory Championship", "STATE", "Public Speaking"),
        ("Collegiate Painting and Digital Illustration Exhibition", "COLLEGE", "Fine Arts"),
    ]
    ev_name, default_level, art_form = rng.choice(cultural_events)
    year = rng.choice([2021, 2022, 2023, 2024, 2025])
    full_ev = f"{ev_name} ({year})"
    org = rng.choice(INSTITUTIONS)
    institutions_competing = rng.randint(25, 60)
    
    variant = idx % 5
    if variant == 0:
        outcome = "FIRST_PLACE"
        rank = "1st Prize"
        text = (f"Awarded First Prize in {art_form} at {full_ev}. Adjudicated by an eminent panel of national artists, competing against "
                f"contingents from {institutions_competing} premier institutions across the country.")
    elif variant == 1:
        outcome = "SECOND_PLACE"
        rank = "2nd Prize"
        text = (f"Secured 2nd Position in {art_form} at {full_ev} representing {org}. Delivered a 15-minute live stage performance "
                f"demonstrating rhythmic complexity and expressive mastery.")
    elif variant == 2:
        outcome = "THIRD_PLACE"
        rank = "3rd Prize"
        text = (f"Placed Third in the competitive {art_form} category at {full_ev}, receiving a trophy and certificate of artistic excellence "
                f"before an audience of faculty and peers.")
    elif variant == 3:
        outcome = "PARTICIPATION"
        rank = "Finalist Performer"
        text = (f"Performed in the grand finale of {full_ev} under the {art_form} category, advancing through two elimination rounds "
                f"before an audience of over {rng.randint(1000, 2500)} attendees.")
    else:
        outcome = "RECOGNITION"
        rank = "Special Jury Award"
        text = (f"Conferred the Special Jury Award for Artistic Originality in {art_form} at {full_ev}. Commended for innovative "
                f"thematic choreography and staging precision.")

    return {
        "achievement_text": text,
        "category": "CULTURAL",
        "domain": "Cultural Arts & Performing Arts",
        "level": default_level,
        "outcome": outcome,
        "event_name": full_ev,
        "organization": org,
        "achievement_date": _random_date(2021, 2025),
        "rank": rank,
        "skills": "Public Performance|Stage Presence|Creative Composition",
        "source_type": "CERTIFICATE",
    }

def generate_volunteering_record(idx: int) -> dict[str, Any]:
    initiatives = [
        ("Digital Literacy Outreach for Rural Primary Schools", "Education Outreach", 80),
        ("Youth Flood Relief and Emergency Supplies Distribution Mission", "Disaster Relief", 120),
        ("Weekly Community Coding and STEM Tutoring for Underprivileged Youth", "Skill Development", 100),
        ("Annual Campus Blood Donation and Health Screening Drive", "Public Health", 45),
        ("Afforestation and Urban Watershed Restoration Initiative", "Environmental Action", 60),
        ("Assistive Audio-Book Recording for Visually Impaired Students", "Inclusive Technology", 75),
        ("Community Cleanliness and Plastic Recycling Awareness Drive", "Sanitation & Civic Action", 50),
        ("Elderly Care Companion and Digital Literacy Workshops", "Community Welfare", 65),
        ("Rural Health and Sanitation Water Testing Volunteer Campaign", "Public Health", 90),
        ("Underprivileged Youth Mentorship in Mathematics and Science", "Education Outreach", 85),
    ]
    init_name, init_type, base_hrs = rng.choice(initiatives)
    hrs = base_hrs + rng.randint(-10, 25)
    ngo = rng.choice(NON_PROFITS_AND_NGOS)
    org = rng.choice(INSTITUTIONS)
    students = rng.randint(20, 60)
    villages = rng.randint(3, 12)
    skills = _random_skills(1, 2)
    
    variant = idx % 4
    if variant == 0:
        outcome = "COMPLETION"
        text = (f"Completed {hrs} verified hours of community service with {ngo} in the '{init_name}' program. Facilitated hands-on "
                f"instruction sessions and mentored {students} young students in basic digital computing skills.")
    elif variant == 1:
        outcome = "RECOGNITION"
        text = (f"Recognized as Volunteer of the Quarter by {ngo} for leading the '{init_name}' campaign. Coordinated a team of 18 "
                f"student volunteers from {org} and distributed educational and sanitation kits across {villages} local communities.")
    elif variant == 2:
        outcome = "PARTICIPATION"
        text = (f"Volunteered actively in the '{init_name}' collaborative initiative spearheaded by {ngo}. Managed ground inventory logistics "
                f"and conducted safety orientation workshops for community beneficiaries across {hrs} service hours.")
    else:
        outcome = "COMPLETION"
        text = (f"Successfully fulfilled {hrs} hours of voluntary social service with {ngo}. Prepared curriculum materials and led "
                f"community awareness drives on environmental conservation, water testing, and digital safety.")

    return {
        "achievement_text": text,
        "category": "VOLUNTEERING",
        "domain": "Community Service & Civic Engagement",
        "level": rng.choice(["LOCAL", "DISTRICT", "STATE"]),
        "outcome": outcome,
        "event_name": init_name,
        "organization": ngo,
        "achievement_date": _random_date(2021, 2025),
        "rank": "None",
        "skills": "|".join(skills) if skills else "Community Outreach|Empathetic Mentoring",
        "source_type": rng.choice(["CERTIFICATE", "MANUAL_RECORD", "SYNTHETIC_RECORD"]),
    }

def generate_other_record(idx: int) -> dict[str, Any]:
    # Rich combinatoric pool for the OTHER category (academic honors, scholarships, fellowships, dean's list, etc.)
    honors_templates = [
        ("Received the University Gold Medal for securing Rank 1 across all 8 semesters of the Bachelor of Technology degree in {dept} at {org}.",
         "Higher Education & Leadership", "UNIVERSITY", "RECOGNITION", "Academic Convocation Honors", "University Gold Medal (Rank 1)"),
        ("Conferred the National Merit Scholarship for Academic Excellence by the Ministry of Education for ranking in the top {pct}% nationally in {year}.",
         "Higher Education & Leadership", "NATIONAL", "RECOGNITION", "National Merit Scholarship Scheme", "Top Scholastic Scholar"),
        ("Selected for the prestigious Global Student Ambassador Fellowship program ({year}), participating in bilateral academic exchange sessions at {org}.",
         "Higher Education & Leadership", "INTERNATIONAL", "PARTICIPATION", "Global Student Ambassador Program", "Student Ambassador Fellow"),
        ("Awarded Institute Merit Scholarship for maintaining a cumulative Grade Point Average (CGPA) of {gpa}/10.00 during the {academic_year} academic year at {org}.",
         "Higher Education & Leadership", "COLLEGE", "RECOGNITION", "Annual Merit Scholarship Award", "Dean's Honor List"),
        ("Received the Campus Best Outgoing Student Award at {org} ({year}), evaluated on composite academic scores, co-curricular breadth, and disciplinary conduct.",
         "Higher Education & Leadership", "COLLEGE", "RECOGNITION", "Annual College Day Awards", "Best Outgoing Student"),
        ("Selected as a Visiting Scholar for a {weeks}-week summer academic residency at {org} investigating interdisciplinary sciences in {year}.",
         "Higher Education & Leadership", "INTERNATIONAL", "COMPLETION", "Summer Academic Residency", "Visiting Student Fellow"),
        ("Recognized with the Alumni Endowment Fellowship Award for exceptional overall academic integrity, resilience, and scholastic merit at {org}.",
         "Higher Education & Leadership", "UNIVERSITY", "RECOGNITION", "Alumni Foundation Honors", "Endowment Scholar"),
        ("Secured Government Technical Talent Stipend ({year}) for outstanding scholastic aptitude in STEM subjects while enrolled at {org}.",
         "Higher Education & Leadership", "NATIONAL", "RECOGNITION", "STEM Scholastic Scholarship", "National Merit Awardee"),
        ("Awarded Dean's Commendation for Academic Distinction in Semester {sem} ({year}) at {org}, achieving a semester GPA of {gpa}.",
         "Higher Education & Leadership", "COLLEGE", "RECOGNITION", "Dean's Honor Roll", "Academic Distinction"),
        ("Inducted into the Collegiate Scholastic Honor Society ({year}) at {org} in recognition of ranking within the top 2% of the graduating engineering cohort.",
         "Higher Education & Leadership", "UNIVERSITY", "RECOGNITION", "Honor Society Induction", "Honor Society Member"),
    ]
    
    depts = ["Computer Science and Engineering", "Information Technology", "Electronics and Communication Engineering",
             "Electrical and Electronics Engineering", "Mechanical Engineering", "Biotechnology", "Data Engineering"]
    dept = rng.choice(depts)
    org = rng.choice(INSTITUTIONS)
    year = rng.choice([2021, 2022, 2023, 2024, 2025])
    academic_year = f"{year-1}-{year}"
    pct = round(rng.uniform(0.05, 0.5), 2)
    gpa = round(rng.uniform(9.45, 9.98), 2)
    sem = rng.randint(3, 8)
    weeks = rng.choice([4, 6, 8, 10])
    
    tmpl, domain, level, outcome, ev_name, rank = rng.choice(honors_templates)
    text = tmpl.format(dept=dept, org=org, year=year, academic_year=academic_year, pct=pct, gpa=gpa, sem=sem, weeks=weeks)
    
    return {
        "achievement_text": text,
        "category": "OTHER",
        "domain": domain,
        "level": level,
        "outcome": outcome,
        "event_name": ev_name,
        "organization": org,
        "achievement_date": _random_date(2021, 2025),
        "rank": rank,
        "skills": "Academic Excellence|Scholastic Rigor|Analytical Thinking",
        "source_type": "CERTIFICATE",
    }

CATEGORY_GENERATOR_MAP = {
    "HACKATHON": generate_hackathon_record,
    "COMPETITION": generate_competition_record,
    "RESEARCH_PUBLICATION": generate_research_publication_record,
    "PATENT": generate_patent_record,
    "INTERNSHIP": generate_internship_record,
    "CERTIFICATION": generate_certification_record,
    "PROJECT": generate_project_record,
    "WORKSHOP": generate_workshop_record,
    "CONFERENCE": generate_conference_record,
    "LEADERSHIP": generate_leadership_record,
    "SPORTS": generate_sports_record,
    "CULTURAL": generate_cultural_record,
    "VOLUNTEERING": generate_volunteering_record,
    "OTHER": generate_other_record,
}

# ─────────────────────────────────────────────────────────────────────────────
# Quality Check & Validation Routine
# ─────────────────────────────────────────────────────────────────────────────

def validate_record_integrity(rec: dict[str, Any]) -> list[str]:
    flags = []
    text = rec.get("achievement_text", "").strip()
    if not text:
        flags.append("EMPTY_TEXT")
    elif len(text) < 35:
        flags.append("TEXT_TOO_SHORT")
    
    if rec.get("category") not in CATEGORIES:
        flags.append(f"INVALID_CATEGORY_{rec.get('category')}")
    
    if rec.get("level") not in LEVELS:
        flags.append(f"INVALID_LEVEL_{rec.get('level')}")
        
    if rec.get("outcome") not in OUTCOMES:
        flags.append(f"INVALID_OUTCOME_{rec.get('outcome')}")
        
    ach_id = rec.get("achievement_id", "")
    if not re.match(r"^ACH\d{6}$", ach_id):
        flags.append("MALFORMED_ACHIEVEMENT_ID")
        
    return flags

# ─────────────────────────────────────────────────────────────────────────────
# Main Dataset Assembly & Generation Routine
# ─────────────────────────────────────────────────────────────────────────────

def build_dataset() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rng.seed(RANDOM_SEED)
    raw_records = []
    seen_hashes = set()
    cleaned_records = []
    duplicate_records = []
    
    counter = 1
    
    for cat in CATEGORIES:
        gen_fn = CATEGORY_GENERATOR_MAP[cat]
        cat_count = 0
        attempts = 0
        
        while cat_count < TARGET_PER_CATEGORY and attempts < TARGET_PER_CATEGORY * 8:
            attempts += 1
            data = gen_fn(attempts)
            raw_text = data["achievement_text"]
            norm_text = _clean_text(raw_text)
            
            h = hashlib.sha256(norm_text.lower().encode("utf-8")).hexdigest()
            if h in seen_hashes:
                # Duplicate detected during generation
                duplicate_records.append({"achievement_text": raw_text, "category": cat})
                continue
                
            seen_hashes.add(h)
            ach_id = _make_id(counter)
            counter += 1
            cat_count += 1
            
            rec = {
                "achievement_id": ach_id,
                "achievement_text": raw_text,
                "normalized_text": norm_text,
                "category": cat,
                "domain": data.get("domain", "Higher Education & Leadership"),
                "level": data.get("level", "UNKNOWN"),
                "outcome": data.get("outcome", "UNKNOWN"),
                "event_name": data.get("event_name"),
                "organization": data.get("organization"),
                "achievement_date": data.get("achievement_date"),
                "rank": data.get("rank", "None"),
                "skills": data.get("skills", ""),
                "source_type": data.get("source_type", "SYNTHETIC_RECORD"),
                "evidence_id": None,
                "source_id": f"SRC_SYNTHETIC_{GENERATION_ID}",
                "annotation_status": "AUTO_GENERATED",
                "labeler_id": "SYNTHETIC_GENERATION",
                "quality_status": "VALIDATED",
                "record_origin": "SYNTHETIC",
                "generation_id": GENERATION_ID,
                "generation_method": "SCENARIO_BASED",
                "source_license": "SYNTHETIC_NO_LICENSE",
                "source_url": None,
                "source_access_date": None,
                "synthetic_status": "EXPLICITLY_SYNTHETIC",
                "validation_flags": "",
            }
            
            flags = validate_record_integrity(rec)
            if flags:
                rec["validation_flags"] = "|".join(flags)
                rec["quality_status"] = "NEEDS_REVIEW"
                
            cleaned_records.append(rec)
            
    # Deterministic final shuffle across categories
    rng.shuffle(cleaned_records)
    return cleaned_records, duplicate_records

# ─────────────────────────────────────────────────────────────────────────────
# File Saving Utilities
# ─────────────────────────────────────────────────────────────────────────────

def save_csv(records: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(records)

def save_jsonl(records: list[dict[str, Any]], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for r in records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

def save_schema(path: Path) -> None:
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "title": "AchievementClassificationRecord",
        "description": "Schema for the primary achievement classification dataset in the AI-Powered Student Achievement Intelligence Platform.",
        "type": "object",
        "required": [
            "achievement_id", "achievement_text", "normalized_text", "category",
            "domain", "level", "outcome", "source_type", "annotation_status",
            "labeler_id", "quality_status", "record_origin", "generation_id",
            "synthetic_status"
        ],
        "properties": {
            "achievement_id": {"type": "string", "pattern": "^ACH\\d{6}$"},
            "achievement_text": {"type": "string", "minLength": 20},
            "normalized_text": {"type": "string", "minLength": 20},
            "category": {"type": "string", "enum": CATEGORIES},
            "domain": {"type": "string"},
            "level": {"type": "string", "enum": LEVELS},
            "outcome": {"type": "string", "enum": OUTCOMES},
            "event_name": {"type": ["string", "null"]},
            "organization": {"type": ["string", "null"]},
            "achievement_date": {"type": ["string", "null"], "format": "date"},
            "rank": {"type": ["string", "null"]},
            "skills": {"type": "string"},
            "source_type": {"type": "string"},
            "evidence_id": {"type": ["string", "null"]},
            "source_id": {"type": "string"},
            "annotation_status": {"type": "string", "enum": ["AUTO_GENERATED", "HUMAN_REVIEWED", "NEEDS_REVIEW", "REJECTED"]},
            "labeler_id": {"type": "string"},
            "quality_status": {"type": "string", "enum": ["VALIDATED", "NEEDS_REVIEW", "REJECTED"]},
            "record_origin": {"type": "string", "enum": ["SYNTHETIC", "REAL_SOURCE"]},
            "generation_id": {"type": "string"},
            "generation_method": {"type": "string"},
            "source_license": {"type": "string"},
            "source_url": {"type": ["string", "null"]},
            "source_access_date": {"type": ["string", "null"]},
            "synthetic_status": {"type": "string", "enum": ["EXPLICITLY_SYNTHETIC", "REAL"]},
            "validation_flags": {"type": "string"}
        }
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)

def save_manifest(records: list[dict[str, Any]], dupes: list[dict[str, Any]], path: Path) -> None:
    from collections import Counter
    cat_counts = Counter(r["category"] for r in records)
    manifest = {
        "dataset_name": "Achievement Classification Dataset",
        "dataset_version": DATASET_VERSION,
        "generation_id": GENERATION_ID,
        "generation_timestamp": date.today().isoformat(),
        "random_seed": RANDOM_SEED,
        "total_records": len(records),
        "synthetic_records": sum(1 for r in records if r["record_origin"] == "SYNTHETIC"),
        "real_source_records": sum(1 for r in records if r["record_origin"] == "REAL_SOURCE"),
        "exact_duplicates_detected": len(dupes),
        "categories_represented": len(cat_counts),
        "category_distribution": dict(cat_counts),
        "quality_status_summary": dict(Counter(r["quality_status"] for r in records)),
        "artifacts": {
            "processed_csv": "data/processed/achievement_classification_dataset.csv",
            "processed_jsonl": "data/processed/achievement_classification_dataset.jsonl",
            "schema_json": "data/schema/achievement_classification_schema.json",
            "config_json": "data/config/synthetic_generation_config.json"
        },
        "license_and_governance": {
            "license": "Research & Educational Use Only",
            "provenance_statement": "All records in this dataset are explicitly synthetic representations generated for NLP benchmark development. No actual student private data is included."
        }
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

def save_config(path: Path) -> None:
    config = {
        "generation_id": GENERATION_ID,
        "random_seed": RANDOM_SEED,
        "target_per_category": TARGET_PER_CATEGORY,
        "num_categories": len(CATEGORIES),
        "expected_total": TARGET_PER_CATEGORY * len(CATEGORIES),
        "generation_strategy": "SCENARIO_BASED",
        "categories": CATEGORIES,
        "controlled_vocabularies": {
            "levels": LEVELS,
            "outcomes": OUTCOMES
        },
        "linguistic_variation": [
            "Formal Institutional Tone",
            "Concise Resume Bullet Points",
            "Detailed Technical Narrative",
            "Award Citation Prose",
            "Credential Verification Summary"
        ],
        "metadata_leakage_controls": [
            "Neutral Achievement IDs (ACH######)",
            "No category names in event or organization names",
            "Exclusion of metadata fields from classifier training inputs"
        ]
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)

# ─────────────────────────────────────────────────────────────────────────────
# Execution Entry Point
# ─────────────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"=== Synthetic Achievement Dataset Generator (v{SCHEMA_VERSION}) ===")
    print(f"Seed: {RANDOM_SEED} | Target: {TARGET_PER_CATEGORY} records x {len(CATEGORIES)} categories = {TARGET_PER_CATEGORY * len(CATEGORIES)}")
    
    clean_recs, dupe_recs = build_dataset()
    print(f"Generated {len(clean_recs)} valid unique records. Exact duplicates filtered during generation: {len(dupe_recs)}")
    
    from collections import Counter
    counts = Counter(r["category"] for r in clean_recs)
    for cat in CATEGORIES:
        print(f"  - {cat:<22}: {counts.get(cat, 0)} records")
        
    save_csv(clean_recs, DATA_PROCESSED / "achievement_classification_dataset.csv")
    save_jsonl(clean_recs, DATA_PROCESSED / "achievement_classification_dataset.jsonl")
    save_schema(DATA_SCHEMA / "achievement_classification_schema.json")
    save_manifest(clean_recs, dupe_recs, DATA_MANIFESTS / "achievement_classification_manifest.json")
    save_config(DATA_CONFIG / "synthetic_generation_config.json")
    
    print("\nDataset files successfully generated and saved to 'data/'.")

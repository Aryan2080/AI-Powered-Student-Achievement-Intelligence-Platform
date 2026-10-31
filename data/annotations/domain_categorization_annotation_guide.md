# Multi-Label Domain Categorization Annotation Guide & Adjudication Protocol

**AI-Powered Student Achievement Intelligence Platform**  
**Role:** Member 1 — NLP & Semantic Intelligence Engineer  
**Document Version:** 1.0.0  
**Status:** Canonical Reference Guide for Independent Evaluation  

---

## 1. Scope & Foundational Principles

This document defines the formal annotation guidelines, boundary disambiguation rules, multi-tag co-occurrence policies, and inter-annotator adjudication protocols for the **10-Domain Achievement Categorization Taxonomy**.

### 1.1 Independence & The "Text-Only" Principle
1. **Evidence-Grounded Annotation:** Annotators must evaluate **only** the verbatim text of the student achievement claim. Annotations must never rely on private scenario metadata (`source_domain`), unmentioned student background, or assumed institutional curriculum.
2. **Conservative Assignment (Precision-First):** Do not assign a domain tag merely because a technical field *could* be involved. An achievement must provide explicit, auditable lexical evidence or direct substantive context.
3. **Strict Orthogonality to Primary Category:** Single-label primary category (1-of-14 taxonomy: `CERTIFICATION`, `HACKATHON`, `INTERNSHIP`, `RESEARCH_PUBLICATION`, etc.) reflects the *operational activity type*. Multi-label domain tags reflect the *subject areas, technical disciplines, and academic knowledge domains* demonstrated. They are completely independent.

---

## 2. The 10 Domain Tags: Scope & Boundary Disambiguation

### 2.1 `lbl_domain_ai` (Artificial Intelligence)
- **Scope:** Broad umbrella artificial intelligence concepts, autonomous agent architectures, cognitive reasoning systems, heuristic search, game-playing AI, knowledge graphs, expert systems, and modern generative AI / LLM applications.
- **Inclusion Examples:** *"Trained a multi-agent reinforcement learning policy for warehouse navigation"*, *"Fine-tuned a Llama-3 8B model using QLoRA for legal document analysis"*, *"Developed an expert recommendation system"*.
- **Boundary with ML:** `lbl_domain_ai` is broader than `lbl_domain_ml`. If an achievement involves empirical model training, neural networks, or statistical learning, tag **both** `lbl_domain_ai` and `lbl_domain_ml`. If an achievement involves pure symbolic logic, A* search, or game heuristics without statistical learning, tag `lbl_domain_ai` only.

### 2.2 `lbl_domain_ml` (Machine Learning)
- **Scope:** Empirical statistical learning, supervised/unsupervised algorithms, deep neural network architectures, model training/evaluation pipelines, hyperparameter optimization, and ML frameworks (PyTorch, TensorFlow, Scikit-Learn, JAX, XGBoost).
- **Inclusion Examples:** *"Trained an XGBoost gradient boosting classifier achieving 92% ROC-AUC"*, *"Implemented a convolutional neural network with custom loss functions in PyTorch"*, *"Performed k-means clustering and PCA dimensionality reduction"*.
- **Exclusion:** Using a commercial SaaS API (e.g. OpenAI API key or Google Translate API) without model training, fine-tuning, or statistical evaluation is **not** sufficient for `lbl_domain_ml` (tag `lbl_domain_web` or `lbl_domain_ai` instead).

### 2.3 `lbl_domain_nlp` (Natural Language Processing)
- **Scope:** Computational linguistics, text processing, syntax parsing, named entity recognition (NER), transformer architectures (BERT, RoBERTa, T5, GPT), language translation, text summarization, sentiment analysis, speech-to-text, and embeddings.
- **Inclusion Examples:** *"Built an automated biomedical named entity recognition pipeline using spaCy and BioBERT"*, *"Engineered a Retrieval-Augmented Generation (RAG) system for question answering"*.
- **Boundary:** Simple string manipulation, regex matching, or basic keyword search does **not** qualify for `lbl_domain_nlp`.

### 2.4 `lbl_domain_cv` (Computer Vision)
- **Scope:** Image processing, video stream analytics, optical feature extraction, object detection (YOLO, Faster R-CNN), image segmentation (U-Net, Mask R-CNN), visual pose estimation, 3D point clouds, OpenCV, and facial recognition.
- **Inclusion Examples:** *"Engineered a real-time defect detection camera pipeline using OpenCV and YOLOv8"*, *"Implemented semantic segmentation on satellite imagery"*.
- **Exclusion:** Graphic design, UI mockups, 3D game modeling, or video editing does **not** qualify for `lbl_domain_cv`.

### 2.5 `lbl_domain_security` (Cybersecurity & Privacy)
- **Scope:** Information security, network vulnerability assessment, penetration testing, cryptography, threat modeling, security operations (SOC/SIEM), ethical hacking (CTFs), authentication/IAM, zero-trust architectures, and digital forensics.
- **Inclusion Examples:** *"Earned CISSP Associate credential demonstrating mastery in cryptography and network security"*, *"Identified critical SQL injection and SSRF vulnerabilities in university web portal"*, *"Won 2nd place in National Inter-Collegiate CTF Invitational"*.
- **Boundary:** Basic password configuration or standard user login in a web app does **not** qualify for `lbl_domain_security` unless explicit security mechanisms or threat models are demonstrated.

### 2.6 `lbl_domain_systems` (Systems, Cloud & Architecture)
- **Scope:** Operating systems, distributed systems, cloud computing infrastructure (AWS, GCP, Azure), container orchestration (Docker, Kubernetes), microservices architectures, networking protocols, Linux kernel, DevOps/SRE, and high-performance computing.
- **Inclusion Examples:** *"Architected a fault-tolerant microservice cluster on AWS EKS using Terraform and Istio"*, *"Engineered an asynchronous message broker with custom TCP socket handling in Go"*.
- **Boundary with Web:** `lbl_domain_systems` focuses on the underlying infrastructure, runtime, orchestration, and scalability, whereas `lbl_domain_web` focuses on application endpoints, frontends, and client-server interfaces. Many modern projects qualify for both.

### 2.7 `lbl_domain_web` (Web Development & APIs)
- **Scope:** Full-stack, frontend, and backend web technologies. Modern web frameworks (React, Angular, Vue, Next.js), backend runtimes (Node.js, Django, FastAPI, Flask, Spring Boot), REST APIs, GraphQL, web sockets, and mobile app development.
- **Inclusion Examples:** *"Developed a responsive e-commerce web platform using React, Node.js, and MongoDB"*, *"Engineered authenticated RESTful API endpoints in FastAPI with OpenAPI documentation"*.
- **Exclusion:** Static HTML/CSS text formatting with no interactive components or backend services.

### 2.8 `lbl_domain_data` (Data Engineering & Analytics)
- **Scope:** Data engineering pipelines (ETL/ELT), relational and NoSQL databases, SQL querying, big data frameworks (Apache Spark, Kafka, Flink, Hadoop), data warehousing (Snowflake, BigQuery), business intelligence, and exploratory data analysis.
- **Inclusion Examples:** *"Designed an automated real-time stream ingestion pipeline using Apache Kafka and Apache Spark Streaming"*, *"Optimized multi-table analytical SQL queries over 10M rows in PostgreSQL"*.
- **Boundary:** Storing simple state in a local SQLite file during a tutorial does not qualify for `lbl_domain_data` unless substantive schema design, indexing, or ETL logic is present.

### 2.9 `lbl_domain_hardware` (Hardware & IoT)
- **Scope:** Electronic circuit design, PCB layout, microcontrollers (Arduino, ESP32, STM32, PIC), microprocessors (Raspberry Pi), FPGA development (Verilog, VHDL), robotics hardware, embedded C/C++, sensors, actuators, and Internet of Things (IoT).
- **Inclusion Examples:** *"Designed a two-layer PCB and firmware in embedded C for a solar-powered environmental telemetry node"*, *"Programmed an FPGA accelerator in Verilog for matrix multiplication"*.
- **Boundary:** Pure software simulations without physical hardware or embedded microcontroller interfaces should be tagged under `lbl_domain_systems` or `lbl_domain_ai`.

### 2.10 `lbl_domain_other` (Other domain — Non-computing)
- **Scope:** Substantive non-computing disciplines: business management, marketing, fine arts, classical music, sports, athletics, debate/MUN, environmental advocacy, and community volunteering.
- **Mutual Exclusion Rule:** `lbl_domain_other` must **never** be co-assigned with any of the 9 technical computing tags. If specific technical tags are present, `lbl_domain_other` is strictly suppressed.

---

## 3. The Zero-Tag Policy (Handling Non-Technical & Ambiguous Claims)

A critical limitation discovered in Step 11 was that classifiers over-predict technical tags when presented with vague or non-technical claims.
Annotators must strictly enforce the **Zero-Tag Policy**:

### 3.1 When to Assign Zero Tags (`[]`)
1. **Purely Administrative / Generic Honors:**
   - Example: *"Awarded the Dean's Merit Scholarship for high academic ranking and scholastic integrity."*  
     $\rightarrow$ Primary category: `SCHOLARSHIP`. Domain tags: `[]` (0 tags).
2. **Ambiguous or Unspecified Event Claims:**
   - Example: *"Participated as an active delegate at the National Youth Leadership Summit 2023."*  
     $\rightarrow$ Primary category: `CONFERENCE`. Domain tags: `[]` (0 tags).
3. **General Attendance / Roll Call / Orientation:**
   - Example: *"Attended the university faculty orientation on ethics and compliance."*  
     $\rightarrow$ Primary category: `WORKSHOP`. Domain tags: `[]` (0 tags).

> **RULE:** Never force-assign `lbl_domain_other` to generic academic honors. `lbl_domain_other` is reserved for explicit non-computing disciplines (e.g. classical vocal music, chess championships, football tournaments). If an achievement is merely generic academic administration, assign **0 tags** (`[]`).

---

## 4. Multi-Domain Assignment Rules

Students frequently build multidisciplinary artifacts. The maximum recommended tags per achievement is **4 tags**. If $\ge 5$ tags appear relevant, review for over-tagging and select only the **substantive** primary disciplines.

| Multidisciplinary Scenario | Assigned Tags | Rationale |
| :--- | :--- | :--- |
| Computer Vision Edge Drone on AWS | `lbl_domain_ai`, `lbl_domain_cv`, `lbl_domain_ml`, `lbl_domain_systems` | Vision model (CV/ML/AI) deployed on cloud infrastructure (Systems). |
| Secure Healthcare Portal with Clinical Notes NLP | `lbl_domain_nlp`, `lbl_domain_security`, `lbl_domain_web` | Clinical text processing (NLP) in an encrypted, authenticated (Security) web application (Web). |
| IoT Soil Telemetry with Spark Analytics Dashboard | `lbl_domain_hardware`, `lbl_domain_data`, `lbl_domain_web` | Microcontroller sensors (Hardware) streaming to ETL pipelines (Data) with a web UI (Web). |

---

## 5. Dual-Annotator Review & Adjudication Protocol

To guarantee gold-label validity, all candidate evaluation records must undergo the following 4-step adjudication protocol:

```
[Candidate Text] 
       │
       ├────────────────────────┐
       ▼                        ▼
[Annotator 1]            [Annotator 2]
(Blind tagging)          (Blind tagging)
       │                        │
       └───────────┬────────────┘
                   ▼
       [Agreement Verification]
       ├── Match: Perfect Agreement ───────► [VERIFIED GOLD TAGS]
       └── Discrepancy (FP/FN on any tag) ──► [Lead Adjudicator Review]
                                                      │
                                                      ▼
                                            [Consensus Adjudication]
                                            + Audit Rationale
```

### 5.1 Discrepancy Resolution Protocol
1. **Step 1:** Annotators independently tag the record without visibility into model predictions or provisional heuristic labels.
2. **Step 2:** An automated diff compares Annotator 1 vs Annotator 2.
3. **Step 3:** If identical, the record is promoted to `VERIFIED`.
4. **Step 4:** If any discrepancy exists (e.g., Annotator 1 tagged `[ai, ml]`, Annotator 2 tagged `[ai]`), the Lead Adjudicator reviews the verbatim text against Section 2 boundary rules, decides the final tag set, and records the `adjudication_notes`.

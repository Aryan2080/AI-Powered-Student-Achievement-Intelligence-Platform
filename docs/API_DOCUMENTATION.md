# REST API Reference & Specification
**AI-Powered Student Achievement Intelligence Platform — Member 3**  
**Base URL:** `/api/v1` | **Interactive Swagger UI:** `http://localhost:8000/docs`

---

## 1. Authentication (`/api/v1/auth`)

### `POST /auth/register`
Create a new user account (Student, Faculty, or Admin).
- **Request Body:**
  ```json
  {
    "email": "student@university.edu",
    "password": "securepassword123",
    "full_name": "Aarav Sharma",
    "role": "STUDENT",
    "department": "Computer Science",
    "program": "B.Tech",
    "year_of_study": 3,
    "gpa": 8.85
  }
  ```
- **Response (201 Created):**
  ```json
  {
    "access_token": "eyJhbGciOiJIUzI1NiIsIn...",
    "token_type": "bearer",
    "role": "STUDENT",
    "user_id": "USR-8fa291b",
    "student_id": "STU-2026-0001"
  }
  ```

### `POST /auth/login`
Authenticate email and password to receive JWT bearer access token.
- **Request Body:**
  ```json
  {
    "email": "student@university.edu",
    "password": "securepassword123"
  }
  ```

### `GET /auth/me`
Introspect token claims and current user profile identity.

---

## 2. Recommendations (`/api/v1/recommendations`)

### `GET /recommendations/{student_id}`
Generate personalized, hard-filtered, multi-criteria ranked opportunity recommendations.
- **Query Parameters:**
  - `top_k` (int, default=10, max=50): Number of opportunities to return.
  - `opportunity_type` (str, optional): `HACKATHON`, `INTERNSHIP`, `RESEARCH_GRANT`, `COMPETITION`, `SCHOLARSHIP`, `CONFERENCE`.
- **Response (200 OK):**
  ```json
  {
    "student_id": "STU-2026-0001",
    "generated_at": "2026-11-04T10:30:00Z",
    "total_recommendations": 10,
    "algorithm_version": "v1.2.0-hybrid",
    "encoder_model": "all-MiniLM-L6-v2",
    "recommendations": [
      {
        "rank": 1,
        "opportunity": {
          "opportunity_id": "OPP-2026-HACK-0001",
          "title": "National AI Innovation Hackathon 2026",
          "opportunity_type": "HACKATHON",
          "organization": "Smart India Hackathon",
          "deadline": "2026-12-15",
          "required_skills": ["Python", "PyTorch", "OpenCV"],
          "domain_tags": ["lbl_domain_ai", "lbl_domain_cv"]
        },
        "match_score": 0.9421,
        "scores": {
          "semantic_similarity": 0.9312,
          "skill_match_score": 1.0000,
          "domain_match_score": 0.9500,
          "urgency_score": 0.8500,
          "composite_score": 0.9421
        },
        "matched_skills": ["Python", "PyTorch", "OpenCV"],
        "missing_skills": [],
        "eligibility_status": "ELIGIBLE",
        "explanation": "Recommended based on your verified hackathon achievement 'Winner (1st Prize) at Smart India Hackathon 2024'. You match 3 of 3 required skills (Python, PyTorch, OpenCV). Deadline is approaching on 2026-12-15."
      }
    ]
  }
  ```

---

## 3. Achievements (`/api/v1/achievements`)

### `POST /achievements`
Submit a new student achievement for automated NLP feature extraction and faculty review.

### `POST /achievements/ingest`
Idempotent bulk or upstream ingestion endpoint consuming verified records from Member 1 or Member 2 pipelines. Requires `source_achievement_id` as unique idempotency key.

### `GET /achievements/student/{student_id}`
Retrieve all historical achievements for a student, filterable by `status=VERIFIED` or `PENDING`.

---

## 4. Faculty Administration (`/api/v1/faculty`)

### `GET /faculty/verification-queue`
List pending student submissions awaiting departmental verification.

### `POST /faculty/verify/{achievement_id}`
Approve or reject a submission with audit remarks, dispatching in-app notification to the student.

### `GET /faculty/talent-search`
Search student pool by authenticated skills, department, and minimum GPA.

---

## 5. Institutional Analytics (`/api/v1/analytics`)

### `GET /analytics/department/{department}`
Retrieve aggregate category distributions and top skills with privacy suppression for small cell sizes ($\le 3$).

### `GET /analytics/student/{student_id}`
Retrieve student competency breakdown, verified skill counts, and profile completion gauge.

---

## 6. Official Reports (`/api/v1/reports`)

### `GET /reports/transcript/{student_id}`
Download cryptographically authenticated **Student Achievement Transcript (PDF)**.

### `GET /reports/department/{department}`
Download **Departmental Analytics Summary (CSV)**.

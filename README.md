# AI-Powered Meeting Intelligence, Preparation & Conversation Analytics Platform

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110+-009688.svg)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Code Style: Black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Tests: Pytest](https://img.shields.io/badge/tests-25%20passed-brightgreen.svg)](https://docs.pytest.org/)

An enterprise-grade, full-lifecycle meeting intelligence platform that analyzes meetings **BEFORE, DURING, and AFTER** the meeting:
- **BEFORE:** Generate structured pre-meeting agendas, expected discussion topics, questions, decisions, and role-based contribution targets.
- **DURING:** Track social dynamics, conversation cadence, idea provenance, potential attribution shifts, speaking balance, and real-time agenda drift.
- **AFTER:** Compare expected vs. actual topic coverage, audit employee attendance & in-time punctuality, detect participation gaps, and identify recurring unresolved topics across historical meetings.

Unlike basic meeting summarizers that generate static bullet points, this platform combines linguistic heuristics, semantic vector embeddings, and relational tracking—powering an interactive, real-time **Meeting Dynamics Replay** and deep executive analytics.

---

## Exact Access URLs

| Interface | URL | Description |
| :--- | :--- | :--- |
| **Interactive Dashboard** | [http://127.0.0.1:8000](http://127.0.0.1:8000) | Full executive dashboard with 10 tabs and 10 executive stat cards |
| **Interactive Swagger API** | [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) | Interactive OpenAPI documentation and test runner |
| **ReDoc Documentation** | [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc) | Human-readable API specifications and schemas |
| **Health Check API** | [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health) | System health, database status, and demo mode verification |

---

## Table of Contents

1. [Problem Statement & Scientific Neutrality](#problem-statement--scientific-neutrality)
2. [Complete 7-Feature Expansion](#complete-7-feature-expansion)
3. [Existing Core Capabilities](#existing-core-capabilities)
4. [System Architecture & Analytical Pipeline](#system-architecture--analytical-pipeline)
5. [Data Models & Relational Schema](#data-models--relational-schema)
6. [Technology Stack](#technology-stack)
7. [Installation & Setup](#installation--setup)
8. [Environment Configuration](#environment-configuration)
9. [Running the Application](#running-the-application)
10. [Step-by-Step Feature Workflows](#step-by-step-feature-workflows)
11. [API Reference](#api-reference)
12. [Testing & Quality Assurance](#testing--quality-assurance)
13. [Security & Privacy Governance](#security--privacy-governance)

---

## Problem Statement & Scientific Neutrality

Traditional meeting software operates strictly post-facto and generates superficial summaries that omit:
1. **Punctuality & Attendance Visibility:** Who arrived late or left early?
2. **Intentional Preparation:** What should have been covered vs. what actually was discussed?
3. **Domain Coverage:** Did specialized participants discuss their designated technical domains?
4. **Meeting Discipline:** Did dialogue drift into tangents, and for how long?
5. **Conversational Inclusivity:** Did some participants struggle to contribute?
6. **Cross-Meeting Amnesia:** Are teams debating the exact same unresolved blocker across multiple sprints?

### Core Principle: Strict Epistemological Distinction & Neutrality

The platform strictly differentiates between:
- **Observed Data:** Actual dialogue timestamps, turn counts, and verified calendar event logs.
- **AI-Generated Expectations:** Predictive planning agendas and domain targets (clearly marked `"AI-generated expected discussion"`).
- **Inferred Data:** Transcript-detected turn bounds (explicitly labeled `"Estimated from transcript"`).

> **Scientific Neutrality Notice:** The platform **never evaluates employee competence or personal performance**. Labels such as `"poor performer"` or `"unproductive"` are strictly prohibited. Metrics are reported using neutral behavioral language: `Topic coverage`, `Observed participation`, `Speaking-time distribution`, and `Estimated attendance`.

---

## Complete 7-Feature Expansion

### Feature 1: Employee Meeting In-Time & Attendance Analytics
- **Dual Source Tracking:**
  - **Verified Attendance:** Official meeting join/leave calendar logs or manual API logs.
  - **Estimated Attendance:** Inferred from first and last spoken dialogue turns in the transcript (`"Estimated from transcript"`).
- **Participant Metrics:** Join time, leave time, total attended duration, meeting total duration, attendance percentage, late arrival (+minutes), early leave (-minutes).
- **Status Badges:** `On time`, `Late`, `Left early`, `Partial attendance`, `Verified`, `Estimated`.
- **Visuals:** Attendance % bar chart and presence timeline tracks showing participant presence intervals relative to runtime.

### Feature 2: Topic → Expected Conversation Generator
- **Pre-Meeting AI Planning:** Users enter topic, objective, duration, type, department, and participants.
- **Structured Plan:** Timed Suggested Agenda, Expected Topics, Expected Questions, Expected Decisions, Expected Action Areas, and Suggested Discussion Leads.
- **Deterministic Fallback:** 100% offline rule/template engine when no external LLM API key is present.
- **Interactive Editing & Persistence:** Users can review, edit, and save plans directly into the meeting database.

### Feature 3: Role-Based Expected Contribution
- **Domain Modeling:** Maps employee roles and responsibilities (e.g., Project Manager, Data Scientist, Backend Developer, QA Engineer) into expected technical topics.
- **Expected vs. Actual Deliberation:** Compares expected domain topics with actual dialogue content.
- **Inclusivity Metrics:** Topic coverage %, speaking time share %, questions asked, ideas introduced, action items owned, and decisions contributed to.

### Feature 4: Meeting Topic Coverage Score
- **Explainable Coverage:** Compares planned agenda topics against extracted transcript topics using semantic cosine matching and synonym expansion.
- **Clear Scoring:** Computes `Covered`, `Partially Covered`, and `Not Discussed / Missing` topics with an explainable reason.
- **Visual Meter:** Formatted progress meter bar (`████████░░ 67%`) accompanied by a detailed deliberation evidence table.

### Feature 5: Agenda Drift Detector
- **Off-Topic Detection:** Scans dialogue turns for discussions deviating significantly from planned agenda topics.
- **Incident Categorization:** Classifies drift as `Minor Drift` (<5 min), `Moderate Drift` (5-10 min), or `Significant Drift` (>10 min).
- **Proportional Timeline Bar:** Visual progression bar displaying green On-Agenda blocks and rose Potential Drift blocks with tooltip intervals.
- **Human-in-the-Loop Verification:** Interactive `[Confirm Drift]` and `[Not Drift]` buttons that store feedback for continuous model refinement.

### Feature 6: Silent Participant / Participation Gap Analyzer
- **Empirical Gap Detection:** Flags participants whose observed speaking time is significantly below the group baseline without judgment.
- **Neutral Contextualization:** Displays explanatory notices: *"Low speaking time may have multiple causes, including meeting role, topic relevance, or meeting structure."*
- **Facilitation Suggestion:** Recommends inclusive moderation: *"Consider inviting input from participants who have not yet contributed to the current topic."*

### Feature 7: Repeated Discussion Detector
- **Cross-Meeting Semantic Clustering:** Identifies persistent deliberative themes across historical meetings using semantic matching and synonym expansion.
- **Historical Trajectory:** Visualizes meeting sequence chains (`Q3 Retrospective ─── Q4 Sprint Planning`).
- **Resolution Tracking:** Tracks whether recurring issues remain `Unresolved` or reached `Resolved` consensus decisions.
- **Modal Drilldown:** `[View Meetings]` modal reveals historical meeting dates, discussion leads, durations, and verbatim transcript excerpts.

---

## Existing Core Capabilities

All pre-existing features remain active and fully integrated:
- **Searchable Transcript:** Full-text keyword search, speaker filtering, topic filtering, click-to-replay.
- **Action Item Review Lifecycle:** Detects tasks with linguistic owners and natural due dates; allows Accept, Edit, Reject review workflows.
- **Speaking-Time Distribution & Cadence:** Bar charts, turn distributions, and quartile filtering (Entire, First 25%, First 50%, Second 50%, Last 25%).
- **Ideas & Idea Journeys:** Semantic extraction, overlap matrices, attribution shift detection, and multi-stage lifecycle trees.
- **Consensus Decisions:** Identifies team agreements and links them to underlying ideas.
- **Chronological Topics:** Segmentation with resolution status tags.
- **Interactive Social Graph:** Cytoscape.js network with node sizes proportional to speaking time and directed edges for interruptions, replies, and idea overlaps.
- **Meeting Dynamics Replay:** Real-time scrubber with Play/Pause and variable playback speeds.
- **Multi-Meeting Comparison:** Empirical comparison charts and metrics tables across meetings.
- **External Integrations:** Slack Block Kit dispatch, Jira issue creation, and Trello card creation.
- **Complete JSON & CSV Export:** Backwards-compatible export enriched with attendance, coverage, drift, gaps, and recurring topics.

---

## System Architecture & Analytical Pipeline

```text
                                 PRE-MEETING
                      ┌────────────────────────────────┐
                      │  Topic / Objective / Roles     │
                      └───────────────┬────────────────┘
                                      │
                                      ▼
                      ┌────────────────────────────────┐
                      │    Meeting Plan Generator      │
                      │  - Suggested Agenda & Outcomes │
                      │  - Expected Topics & Questions │
                      │  - Role Domain Expectations    │
                      └───────────────┬────────────────┘
                                      │
                                 DURING & POST
                                      ▼
                      ┌────────────────────────────────┐
                      │    Raw Transcript Ingestion    │
                      │ (Zoom, Teams, Meet, Text, VTT) │
                      └───────────────┬────────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        ▼                             ▼                             ▼
┌───────────────────┐       ┌───────────────────┐       ┌───────────────────┐
│ Attendance Engine │       │ Dialogue Parsers  │       │ Semantic Matcher  │
│ - Verified Logs   │       │ - Turn Cadence    │       │ - N-Gram Cosine   │
│ - Turn Bounds     │       │ - Interruptions   │       │ - Synonym Expans. │
│ - Late / Early    │       │ - Actions/Decis.  │       │ - Cross-Meeting   │
└─────────┬─────────┘       └─────────┬─────────┘       └─────────┬─────────┘
          │                           │                           │
          └───────────────────────────┼───────────────────────────┘
                                      │
                                      ▼
                      ┌────────────────────────────────┐
                      │   Relational SQLite Storage    │
                      │  (Participants, Attendance,    │
                      │   Plans, Drifts, RecurTopics)  │
                      └───────────────┬────────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        ▼                             ▼                             ▼
┌───────────────────┐       ┌───────────────────┐       ┌───────────────────┐
│ Executive Cards   │       │ Visual Timelines  │       │ REST Endpoints &  │
│ - 10 Core KPIs    │       │ - Presence Bar    │       │ Backward-Compat.  │
│ - Tooltip Details │       │ - Drift Segments  │       │ JSON / CSV Export │
│ - Governance Badg.│       │ - Cytoscape Graph │       │ & Integrations    │
└───────────────────┘       └───────────────────┘       └───────────────────┘
```

---

## Data Models & Relational Schema

The relational database (`meetings.db`) utilizes SQLAlchemy 2.0 with safe auto-migration:

- **`Meeting`**: Title, date, duration, active participants, relationships to:
  - `attendance_records` (`Attendance`)
  - `meeting_plan` (`MeetingPlan`)
  - `agenda_drifts` (`AgendaDrift`)
  - `transcript_segments`, `topics`, `decisions`, `ideas`, `action_items`
- **`Participant`**: Name, avatar color, speaking metrics, `employee_id`, `role`, `department`, `responsibilities`.
- **`Attendance`**: Join time, leave time, duration minutes, attendance %, late arrival min, early leave min, `is_verified` flag, status badge.
- **`MeetingPlan`**: Planned duration, type, objective, department, JSON-encoded suggested agenda, expected topics, expected questions, expected decisions, expected action areas, and role expectations.
- **`AgendaDrift`**: Start time, end time, duration minutes, detected off-topic subject, expected topic, severity category (`Minor`, `Moderate`, `Significant`), confidence score, transcript excerpt, `user_feedback_status`.
- **`RecurringTopic` & `RecurringTopicOccurrence`**: Topic title, normalized keywords, decision status, occurrences count, first/last meeting references, meeting link, duration, lead speaker, and transcript excerpt.

---

## Technology Stack

### Backend
- **Python 3.11+**
- **FastAPI**: Asynchronous, high-performance RESTful API framework.
- **SQLAlchemy 2.0**: Relational ORM configured with auto-migrating SQLite storage.
- **Pydantic v2**: Strict schema validation and serialization.
- **Scikit-Learn**: Cosine semantic similarity matching and CountVectorizer embeddings.
- **NetworkX**: Graph theory algorithms for network degree and centrality.
- **Dateparser**: Multi-format natural language date resolution.
- **HTTPX**: Non-blocking asynchronous HTTP client.

### Frontend
- **HTML5 & Modern Dark UI**: Sleek glassmorphism palette, responsive layout, semantic navigation.
- **Chart.js**: Horizontal attendance duration charts, turn cadence distributions, multi-meeting comparisons.
- **Cytoscape.js**: Interactive force-directed and circular network graph rendering.
- **Vanilla JavaScript (ES6+)**: Reactive state architecture with zero external framework overhead.

---

## Installation & Setup

### Prerequisites
- Python 3.11 or higher
- Git

### 1. Clone & Enter Repository
```bash
git clone https://github.com/your-username/meeting-intelligence.git
cd meeting.project
```

### 2. Create Virtual Environment
```bash
python -m venv venv

# Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Linux / macOS
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## Environment Configuration

Copy the example environment file:
```bash
cp .env.example .env
```

Key environment settings in `.env`:
```ini
APP_NAME="Meeting Intelligence, Preparation & Conversation Analytics Platform"
APP_ENV="development"
DEBUG=true

# Demo Mode (100% Offline Capability)
DEMO_MODE=true

# Database Storage
DATABASE_URL="sqlite:///./meetings.db"

# LLM Configuration (Optional - Defaults to local heuristic & template engine)
LLM_PROVIDER="demo" # options: demo, openai, anthropic
OPENAI_API_KEY=""

# Integrations (Simulated in DEMO_MODE, Live when tokens provided)
SLACK_WEBHOOK_URL=""
JIRA_SERVER_URL=""
TRELLO_API_KEY=""
```

---

## Running the Application

Start the backend server using Uvicorn:
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open your browser:
- **Dashboard:** [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Swagger Documentation:** [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Documentation:** [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- **Health Endpoint:** [http://127.0.0.1:8000/api/health](http://127.0.0.1:8000/api/health)

---

## Step-by-Step Feature Workflows

### 1. Loading the Demo Dataset
Click the top **"Seed Demo Meeting"** button or select `"Q4 Sprint Planning & Architecture Sync"` from the meeting dropdown:
- Automatically loads 5 participants (`Alice`, `Bob`, `Charlie`, `David`, `Emily`).
- Seeds verified attendance records, late arrivals (Bob), and early departures (Emily).
- Seeds a pre-meeting plan, agenda drift incident (catering banter), participation gap (Emily), and historical cross-meeting recurring topics from Q3 Retrospective.

### 2. Generating a Pre-Meeting Plan (Meeting Preparation Tab)
1. Navigate to the **"Meeting Preparation"** tab.
2. Click **"Sync From Active Meeting"** or enter a custom topic (e.g., `"Cloud Migration & Database Scaling"`).
3. Add expected participants with their roles and domain responsibilities.
4. Click **"Generate Expected Conversation Plan"**.
5. The system renders a timed Suggested Agenda, Expected Topics, Expected Questions, Expected Decisions, Expected Action Areas, and Role Expectations.
6. Click **"Save Meeting Plan"** to bind the plan to the meeting and recalculate topic coverage.

### 3. Reviewing Attendance & In-Time Punctuality (Attendance Tab)
1. Navigate to the **"Attendance"** tab.
2. Review the 5 summary cards: Average Attendance (85.8%), On-Time Arrivals (3), Late Arrivals (1), Early Departures (1), and Verified/Estimated ratio (5 / 0).
3. Inspect the attendance percentage chart and the **Participant Presence Timeline** tracks.
4. Click **"Edit"** on any participant row to modify join/leave times or toggle between *Verified attendance* and *Estimated from transcript*.

### 4. Evaluating Expected vs. Actual Coverage (Expected vs Actual Tab)
1. Navigate to the **"Expected vs Actual"** tab.
2. View the overall **Topic Coverage Score** progress bar (`████████░░ 66.7%`) and the explainable rationale.
3. Review the breakdown of Covered, Partially Covered, and Not Discussed topics with discussion durations and verbatim evidence quotes.
4. Review the **Role-Based Expected vs Actual Contribution** cards showing domain topic coverage and speaking metrics without judgmental labels.

### 5. Investigating Agenda Drift (Agenda Analysis Tab)
1. Navigate to the **"Agenda Analysis"** tab.
2. View the segmented progression timeline showing On-Agenda intervals and detected drift intervals.
3. Click the interactive **[Confirm Drift]** or **[Not Drift]** buttons to record human feedback.

### 6. Inspecting Participation Gaps (Participation Tab)
1. Navigate to the **"Participation"** tab.
2. Scroll to the **"Observed Participation Gaps & Inclusive Facilitation"** section.
3. Review Emily's low observed speaking share (4.4%) accompanied by neutral contextualization and inclusive facilitation suggestions.

### 7. Tracking Cross-Meeting Trajectory (Recurring Topics Tab)
1. Navigate to the **"Recurring Topics"** tab.
2. Filter topics by `All`, `Unresolved`, `Repeated (2+ Meetings)`, or `Resolved`.
3. Click **"View Meetings"** to inspect historical meeting dates, discussion leads, and transcript excerpts across sprint sessions.

---

## API Reference

### Health & Core
- `GET /api/health` - System health, DB connection, and demo status.
- `GET /api/meetings` - List all meetings.
- `GET /api/meetings/{id}` - Complete meeting summary.
- `POST /api/meetings/seed-demo` - Seed demo meeting with historical Q3 data.
- `POST /api/meetings/upload` - Upload `.txt`, `.vtt`, `.srt`, or raw dialogue text.
- `GET /api/meetings/{id}/export?format=json|csv` - Extended JSON/CSV export.

### Feature 1: Attendance Analytics
- `GET /api/meetings/{id}/attendance` - Participant join/leave times, duration, punctuality metrics, and summary.
- `POST /api/meetings/{id}/attendance` - Log verified attendance record.
- `PUT /api/meetings/{id}/attendance/{participant_id}` - Update participant attendance details.

### Features 2 & 3: Meeting Preparation & Role Expectations
- `POST /api/meetings/meeting-plan/generate` - Generate meeting plan without binding.
- `POST /api/meetings/{id}/meeting-plan/generate` - Generate meeting plan for specific meeting.
- `GET /api/meetings/{id}/meeting-plan` - Retrieve stored meeting plan.
- `POST /api/meetings/{id}/meeting-plan` - Save/update meeting plan.
- `GET /api/meetings/{id}/expected-topics` - Retrieve planned expected topics list.
- `GET /api/meetings/{id}/role-contributions` - Compare expected vs actual role contributions.

### Features 4 & 5: Coverage & Agenda Drift
- `GET /api/meetings/{id}/topic-coverage` - Explainable topic coverage score and breakdown.
- `GET /api/meetings/{id}/agenda-drift` - Detected drift segments, timeline intervals, and metrics.
- `POST /api/meetings/{id}/agenda-drift/{drift_id}/feedback` - Record user feedback (Confirm/Dispute).

### Features 6 & 7: Participation Gaps & Recurring Topics
- `GET /api/meetings/{id}/participation-gaps` - Identify low observed participation with facilitation tips.
- `GET /api/meetings/{id}/recurring-topics` - Recurring topics relevant to this meeting.
- `GET /api/analytics/recurring-topics` - Global cross-meeting recurring topic trajectories.

---

## Testing & Quality Assurance

The test suite covers all existing and expanded analytical services and API endpoints:
```bash
python -m pytest -v
```

### Test Suite Summary (25/25 Passing):
1. `tests/test_advanced_features.py`:
   - `test_attendance_calculation`: Join/leave duration, punctuality, and attendance %.
   - `test_meeting_plan_generation`: Deterministic template fallback and structured agenda.
   - `test_role_based_contributions`: Expected domain topics vs observed turns.
   - `test_topic_coverage_score`: Explainable score, progress bar, and topic breakdown.
   - `test_agenda_drift_detection`: Off-topic bounds, duration %, and user feedback loop.
   - `test_participation_gaps_neutrality`: Statistical gap threshold and neutral governance.
   - `test_recurring_topics_analyzer`: Cross-meeting semantic clustering and resolution status.
   - `test_attendance_api_endpoints`: GET, POST, and PUT endpoints for attendance records.
   - `test_export_includes_new_features`: Backwards-compatible JSON and CSV exports.
2. `tests/test_actions.py`: Linguistic action item extraction, owner assignment, natural due dates.
3. `tests/test_speakers.py`: Speaking-time distribution, turn length metrics, std dev.
4. `tests/test_interruptions.py`: Dialogue timing cadence and incomplete sentence heuristics.
5. `tests/test_ideas.py`: Idea extraction, semantic cosine similarity, attribution shifts.
6. `tests/test_decisions_topics.py`: Consensus detection, topic segmentation, unresolved topics.
7. `tests/test_replay_graph.py`: Time-sliced replay snapshots and NetworkX social graph.
8. `tests/test_api.py`: FastAPI endpoints, confirmation review lifecycle, and export streaming.
9. `tests/test_parser.py`: Multi-platform transcript format parsing and timestamp normalization.

---

## Security & Privacy Governance

1. **Transcript Confidentiality:** Transcripts are processed locally in memory. No dialogue is sent to unconfigured cloud endpoints.
2. **Credential Safety:** Secrets and webhook URLs are managed exclusively through `.env` and never leaked to frontend JavaScript.
3. **Auditability & Explainability:** Every analytical metric provides the underlying timestamps, duration, and verbatim dialogue quotes.
4. **Strict Epistemological Humility:** The system labels AI predictions as expectations and transcript turn bounds as estimates, ensuring factual integrity.

---

## Summary of Modified & Created Files

### Backend Services & Models
- `app/models/attendance.py` (Created): Attendance ORM model.
- `app/models/meeting_plan.py` (Created): MeetingPlan ORM model.
- `app/models/agenda_drift.py` (Created): AgendaDrift ORM model.
- `app/models/recurring_topic.py` (Created): RecurringTopic and Occurrence ORM models.
- `app/models/participant.py` (Modified): Added `employee_id`, `role`, `department`, `responsibilities`.
- `app/models/meeting.py` (Modified): Added relationships for attendance, plan, and drift.
- `app/database/database.py` (Modified): Added safe SQLite auto-migration for new participant columns.
- `app/schemas/schemas.py` (Modified): Pydantic schemas for Features 1-7.
- `app/services/semantic_matcher.py` (Created): N-gram cosine similarity and synonym expansion engine.
- `app/services/attendance_analyzer.py` (Created): Verified vs estimated attendance calculations.
- `app/services/meeting_planner.py` (Created): Pre-meeting AI agenda and role expectations generator.
- `app/services/role_contribution_analyzer.py` (Created): Domain expectation vs actual contribution comparator.
- `app/services/topic_coverage_analyzer.py` (Created): Explainable coverage score and progress bar.
- `app/services/agenda_drift_detector.py` (Created): Off-topic drift detection and timeline interval mapping.
- `app/services/participation_gap_analyzer.py` (Created): Neutral participation gap identification.
- `app/services/recurring_topics_analyzer.py` (Created): Historical cross-meeting topic trajectory tracker.
- `app/api/attendance.py` (Created): Attendance REST endpoints.
- `app/api/meeting_plan.py` (Created): Meeting plan and agenda generator endpoints.
- `app/api/analytics.py` (Modified): Added coverage, drift, gaps, role contribution, and recurring topics endpoints.
- `app/api/meetings.py` (Modified): Enhanced demo seeding with historical Q3 meeting and updated exports.
- `app/main.py` (Modified): Mounted attendance, meeting plan, and global analytics routers.

### Frontend
- `frontend/index.html` (Modified): Added 5 navigation tabs, 10 executive stat cards, 5 new tab panes, and 2 new modal dialogs.
- `frontend/css/style.css` (Modified): Added styles for badges, presence timeline tracks, drift bars, role cards, recurring trajectory nodes, and gap cards.
- `frontend/js/api.js` (Modified): Added API client methods for all 7 features.
- `frontend/js/app.js` (Modified): Added State fields, parallel data loading, overview card updaters, and renderers for Features 1-7.

### Tests & Sample Data
- `sample_data/sample_meeting.txt` (Modified): Added realistic catering drift and early leave turns.
- `tests/test_advanced_features.py` (Created): Comprehensive test suite covering all 7 features.
- `README.md` (Modified): Comprehensive documentation of full platform and feature workflows.

---

## License

Distributed under the MIT License. See `LICENSE` for more information.

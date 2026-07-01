# Provenance Guard

Provenance Guard is a Flask API that evaluates submitted writing using multiple provenance signals, combines those signals into a confidence score, returns a plain-English transparency label, supports creator appeals, and records decisions in a structured audit log.

The project is designed around a writing-platform scenario where falsely labeling a human creator’s work as AI-generated is harmful. Because of that, the scoring and labels are intentionally conservative: middle-range scores become `uncertain` instead of forcing an accusation.

The project also includes a lightweight demo frontend so the system can be tested from a browser instead of only through command-line API requests.

---

## Rubric Coverage Summary

- Content submission endpoint: `POST /submit`
- Structured JSON response with attribution, confidence, label, and signal scores
- Multi-signal pipeline: LLM, stylometric, and predictability signals
- Confidence scoring with documented weights and thresholds
- Transparency labels for likely human, uncertain, and likely AI
- Appeals workflow through `POST /appeal`
- Appeal status changes to `under_review`
- Structured audit log through `GET /log`
- Rate limiting on `POST /submit`
- Analytics dashboard through `GET /analytics`
- Provenance certificate through `POST /verify-creator`
- Structured metadata support through `POST /submit-metadata`
- Demo frontend at `GET /`
- Optional Groq cloud inference and local Ollama/Qwen inference
- SQLite audit persistence
- Pytest coverage for core logic and API workflows

---

## Features

### Required Features

- `POST /submit` accepts creator text and returns structured JSON.
- Three detection signals run on each text submission:
  - LLM signal
  - Stylometric signal
  - Predictability signal
- Confidence scoring combines all signal scores into one final score.
- Transparency labels change based on the final attribution result.
- `POST /appeal` lets a creator dispute a classification.
- `GET /log` returns a structured audit log.
- Flask-Limiter protects `POST /submit` from request flooding.

### Stretch Features

- Ensemble detection with three distinct signals.
- `GET /analytics` dashboard metrics.
- `POST /verify-creator` provenance certificate.
- `POST /submit-metadata` structured metadata support for non-text content.
- Demo frontend served at `GET /` for easier testing and walkthroughs.
- Optional local LLM inference through Ollama/Qwen.
- Frontend demo/admin provider selector for switching between Groq and local Ollama.
- SQLite persistence instead of JSON-file audit storage.
- 60 passing pytest tests covering core logic, latency instrumentation, and API workflows.

---

## Tech Stack

- Python
- Flask
- Flask-Limiter
- Groq API
- Ollama local inference
- Qwen local model support through Ollama
- python-dotenv
- HTML/CSS/JavaScript frontend
- SQLite persistence through Python’s built-in `sqlite3`
- pytest

---

## Setup

Clone the repo:

```bash
git clone https://github.com/debanjawn/provenance-guard.git
cd provenance-guard
```

Create and activate a virtual environment.

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Install dependencies:

```powershell
pip install -r requirements.txt
```

Create a real `.env` file in the repo root:

```env
LLM_PROVIDER=groq
GROQ_API_KEY=your_actual_groq_key_here
GROQ_MODEL=llama-3.1-8b-instant

OLLAMA_MODEL=qwen2.5-coder:14b
OLLAMA_BASE_URL=http://localhost:11434
```

The repo includes `.env.example` as a safe template. Do not commit your real `.env`.

Local audit entries are stored in `provenance_guard.db`, which is created automatically when the app starts. The project originally used `audit_log.json` for prototype storage, but SQLite is used now to reduce the risk of lost audit entries under concurrent writes.

Run the app:

```powershell
python app.py
```

The API runs locally at:

```text
http://127.0.0.1:5000
```

The demo frontend runs at:

```text
http://127.0.0.1:5000/
```

Health check:

```powershell
Invoke-RestMethod http://127.0.0.1:5000/health
```

Expected response:

```json
{
  "message": "Provenance Guard API is running",
  "status": "ok"
}
```

---

## LLM Provider Configuration

The LLM signal supports both Groq cloud inference and local Ollama/Qwen inference.

The default provider is controlled through `.env`:

```env
LLM_PROVIDER=groq
```

or:

```env
LLM_PROVIDER=ollama
```

If `LLM_PROVIDER` is missing or invalid, the app defaults to Groq.

### Groq Cloud Inference

To use Groq:

```env
LLM_PROVIDER=groq
GROQ_API_KEY=your_actual_groq_key_here
GROQ_MODEL=llama-3.1-8b-instant
```

Then run:

```powershell
python app.py
```

### Local Ollama/Qwen Inference

To use local Ollama/Qwen inference:

1. Install and run Ollama.
2. Pull the model:

```powershell
ollama pull qwen2.5-coder:14b
```

3. Configure `.env`:

```env
LLM_PROVIDER=ollama
OLLAMA_MODEL=qwen2.5-coder:14b
OLLAMA_BASE_URL=http://localhost:11434
```

4. Run the app:

```powershell
python app.py
```

This allows the LLM signal to run locally through Ollama instead of sending the LLM prompt to Groq.

### Frontend Provider Selector

The demo frontend includes a global admin-style provider selector labeled:

```text
AI Provider for LLM-backed actions
```

Options:

- Default from `.env`
- Groq cloud
- Local Ollama/Qwen

This selector is intended for local demos and interviews. It does not expose API keys or secret values. It currently affects text classification through `POST /submit`, because that is the feature that uses the LLM signal. Other routes like appeals, analytics, audit logs, verification, and metadata scoring do not currently call an LLM.

The app also exposes a safe non-secret endpoint:

```text
GET /llm-provider
```

Example response:

```json
{
  "default_provider": "ollama",
  "default_provider_label": "Local Ollama/Qwen"
}
```

---

## Architecture

### Post-Feedback Improvements

- The Flask app now uses an application factory pattern through `create_app()`.
- Tests create isolated app instances with temporary configuration instead of reloading the `app` module.
- SQLite is initialized once at startup, and `audit_log.py` operations now run against that initialized database instead of defensively calling `init_db()` on every operation.
- This makes configuration and tests more predictable and aligns the project more closely with common production Flask patterns.

### Submission Flow

```text
POST /submit
(raw JSON: creator_id, text, optional llm_provider)
        ↓
app.py validates input
(validated creator_id + raw text + provider selection)
        ↓
Generate content_id
(content_id + creator_id + raw text)
        ↓
detectors/llm_signal.py
(raw text + provider selection → llm_score + llm_reason)
        ↓
detectors/stylometric_signal.py
(raw text → stylometric_score + metrics)
        ↓
detectors/predictability_signal.py
(raw text → predictability_score + metrics)
        ↓
scoring.py
(llm_score + stylometric_score + predictability_score → combined confidence + attribution)
        ↓
labels.py
(attribution + confidence → transparency label text)
        ↓
audit_log.py
(content_id + creator_id + signal scores + confidence + attribution + label + status)
        ↓
SQLite database
(provenance_guard.db)
        ↓
JSON response
(content_id + attribution + confidence + signal_scores + label + status + llm_provider)
```

### Appeal Flow

```text
POST /appeal
(raw JSON: content_id, creator_reasoning)
        ↓
app.py validates appeal request
(validated content_id + creator reasoning)
        ↓
Find original submission
(original classification + confidence + status)
        ↓
Update status
(status → under_review)
        ↓
audit_log.py
(content_id + original classification + appeal reasoning + updated status)
        ↓
SQLite database
(provenance_guard.db)
        ↓
JSON response
(content_id + status + confirmation message)
```

---

## Demo Frontend

The project includes a dependency-free frontend served by Flask at:

```text
GET /
```

The frontend makes the project easier to demo without manually typing every request in PowerShell or curl.

It supports:

- selecting the LLM provider for LLM-backed actions
- submitting text to `POST /submit`
- viewing attribution, combined confidence, thresholds, calibration details, and individual signal scores
- viewing which LLM provider was used
- submitting appeals to `POST /appeal`
- fetching the audit log from `GET /log`
- fetching analytics from `GET /analytics`
- verifying a creator through `POST /verify-creator`
- submitting structured metadata through `POST /submit-metadata`

The frontend uses plain HTML, CSS, and JavaScript:

```text
templates/index.html
static/style.css
static/script.js
```

It does not expose secrets. It only sends safe provider values such as `default`, `groq`, or `ollama`.

---

## API Endpoints

### `GET /`

Serves the browser demo frontend.

Open:

```text
http://127.0.0.1:5000/
```

Use this page to test the main features visually:

- text submission
- LLM provider selection
- transparency label output
- appeal submission
- audit log viewing
- analytics
- creator verification
- metadata provenance checks

---

### `GET /health`

Returns a simple health check.

Response:

```json
{
  "message": "Provenance Guard API is running",
  "status": "ok"
}
```

---

### `GET /llm-provider`

Returns safe, non-secret information about the default LLM provider.

Example response:

```json
{
  "default_provider": "ollama",
  "default_provider_label": "Local Ollama/Qwen"
}
```

This endpoint does not expose API keys or `.env` contents.

---

### `POST /submit`

Submits text for provenance classification.

Request:

```json
{
  "creator_id": "test-user-1",
  "text": "The sun dipped below the horizon, painting the sky in hues of amber and rose."
}
```

Optional provider override for local demo use:

```json
{
  "creator_id": "test-user-1",
  "llm_provider": "ollama",
  "text": "The sun dipped below the horizon, painting the sky in hues of amber and rose."
}
```

Valid `llm_provider` values:

```text
default
groq
ollama
```

Response example:

```json
{
  "attribution": "likely_human",
  "calibration_summary": {
    "calibration_rule": null,
    "calibration_rule_applied": false,
    "distance_to_likely_ai": 0.4471,
    "distance_to_likely_human": 0.0,
    "explanation": "Likely AI requires a high combined score or strong agreement between elevated LLM and predictability signals, so polished writing alone can still remain uncertain.",
    "weights": {
      "llm": 0.45,
      "predictability": 0.25,
      "stylometric": 0.3
    }
  },
  "classification_thresholds": {
    "likely_ai_min": 0.75,
    "likely_human_max": 0.39
  },
  "confidence": 0.3029,
  "content_id": "0571a271a0c34139b25349fe10fba30b",
  "label": "This text appears more consistent with human-written work based on the signals reviewed. This label is not a guarantee, but the system did not find strong signs of AI generation.",
  "llm_provider": "ollama",
  "signal_contributions": {
    "llm": 0.135,
    "predictability": 0.013,
    "stylometric": 0.1549
  },
  "signal_scores": {
    "llm": 0.3,
    "predictability": 0.0521,
    "stylometric": 0.5164
  },
  "status": "classified"
}
```

---

### `POST /appeal`

Submits an appeal for a previous classification.

Request:

```json
{
  "content_id": "18c3ffe225dc4e7884dcf9cbc8e4494d",
  "creator_reasoning": "I wrote this myself from personal experience. My writing style may appear more formal than typical."
}
```

Response:

```json
{
  "content_id": "18c3ffe225dc4e7884dcf9cbc8e4494d",
  "message": "Appeal received.",
  "status": "under_review"
}
```

---

### `GET /log`

Returns structured audit log entries from SQLite.

Example appeal-related log entries:

```json
[
  {
    "attribution": "likely_ai",
    "confidence": 0.8409,
    "content_id": "18c3ffe225dc4e7884dcf9cbc8e4494d",
    "creator_id": "label-test-ai-extreme",
    "entry_type": "classification",
    "llm_score": 0.9,
    "predictability_score": 0.9405,
    "status": "classified",
    "stylometric_score": 0.6693,
    "timestamp": "2026-06-28T07:17:26.279155+00:00"
  },
  {
    "appeal_reasoning": "I wrote this myself from personal experience. My writing style may appear more formal than typical.",
    "content_id": "18c3ffe225dc4e7884dcf9cbc8e4494d",
    "creator_id": "label-test-ai-extreme",
    "entry_type": "appeal",
    "original_attribution": "likely_ai",
    "original_confidence": 0.8409,
    "status": "under_review",
    "timestamp": "2026-06-28T07:21:00.589534+00:00"
  }
]
```

---

### `GET /analytics`

Returns dashboard metrics from the audit log.

Example response:

```json
{
  "appeal_count": 1,
  "appeal_rate": 0.0417,
  "average_confidence": 0.5551,
  "likely_ai_count": 1,
  "likely_human_count": 6,
  "total_submissions": 24,
  "uncertain_count": 17
}
```

---

### `POST /verify-creator`

Creates a provenance certificate for a creator.

Request:

```json
{
  "creator_id": "creator_verified_1",
  "verification_method": "writing_sample_review"
}
```

Response:

```json
{
  "certificate_label": "Verified creator: this creator completed an additional provenance check. This does not guarantee authorship of a specific submission, but it provides extra context.",
  "creator_id": "creator_verified_1",
  "timestamp": "2026-06-28T07:32:34.389878+00:00",
  "verification_method": "writing_sample_review",
  "verified": true
}
```

A verified creator is not automatically treated as human-written for every submission. This certificate is separate from the AI/human transparency label.

---

### `POST /submit-metadata`

Processes structured metadata for non-text content.

Human-process metadata example:

```json
{
  "creator_id": "metadata-human",
  "content_type": "image_metadata",
  "metadata": {
    "tool_used": "Photoshop",
    "declared_ai_assistance": false,
    "has_process_notes": true,
    "edit_history_available": true,
    "human_reviewed": true
  }
}
```

Response:

```json
{
  "content_id": "702964ac12984254baa3bbcc1ab84a21",
  "content_type": "image_metadata",
  "creator_id": "metadata-human",
  "metadata_attribution": "likely_human_process",
  "metadata_checks": {
    "declared_ai_assistance": false,
    "edit_history_available": true,
    "has_process_notes": true,
    "human_reviewed": true,
    "tool_flagged_as_ai": false,
    "tool_used": "Photoshop"
  },
  "provenance_score": 0.0,
  "reason": "The metadata shows stronger signs of human process documentation than AI-assisted creation.",
  "status": "classified"
}
```

AI-assisted metadata example:

```json
{
  "creator_id": "metadata-ai",
  "content_type": "image_metadata",
  "metadata": {
    "tool_used": "Midjourney",
    "declared_ai_assistance": true,
    "has_process_notes": false,
    "edit_history_available": false,
    "human_reviewed": false
  }
}
```

Response:

```json
{
  "content_id": "34ac5265d3144cfa81b75612f439064f",
  "content_type": "image_metadata",
  "creator_id": "metadata-ai",
  "metadata_attribution": "likely_ai_assisted",
  "metadata_checks": {
    "declared_ai_assistance": true,
    "edit_history_available": false,
    "has_process_notes": false,
    "human_reviewed": false,
    "tool_flagged_as_ai": true,
    "tool_used": "Midjourney"
  },
  "provenance_score": 1.0,
  "reason": "The metadata indicates stronger signs of AI-assisted creation than human-process evidence.",
  "status": "classified"
}
```

---

## Detection Signals

The system uses three distinct signals. Each signal returns a score from `0.0` to `1.0`, where higher means more AI-like.

### 1. LLM Signal

File:

```text
detectors/llm_signal.py
```

The LLM signal uses Groq by default and can optionally call a local Ollama model. In both cases, it asks for a structured assessment with a `score` and `reason`.

It measures:

- tone
- flow
- genericness
- semantic coherence
- polish
- whether the writing feels natural or templated

The LLM parser handles:

- clean JSON
- JSON inside markdown code fences
- extra text before or after a JSON object
- invalid or missing scores through safe fallback behavior

Why this signal exists:

The LLM can make a broad, holistic judgment about the text. It can notice overall style and semantic patterns that simple metrics may miss.

Blind spot:

The LLM may over-score formal human writing, academic writing, or professionally edited writing. Because of that, the project does not allow the LLM signal to fully decide the final result by itself.

---

### 2. Stylometric Signal

File:

```text
detectors/stylometric_signal.py
```

The stylometric signal measures structural writing statistics.

It uses metrics such as:

- sentence length variance
- type-token ratio
- punctuation density
- repetition rate

Why this signal exists:

AI-generated writing can be smoother and more uniform. Human writing often has more variation in sentence length, punctuation, and word choice.

Blind spot:

Polished human writing, resumes, academic paragraphs, and some creative writing can also look uniform. This means stylometrics can misread genre or style as AI evidence.

---

### 3. Predictability Signal

File:

```text
detectors/predictability_signal.py
```

The predictability signal estimates how formulaic the writing is.

It looks for:

- repeated phrases
- common transitions
- generic AI-style wording
- assistant-template preambles and corporate phrasing clusters
- formulaic phrases like “in conclusion,” “it is important to note,” and “plays a crucial role”

Why this signal exists:

AI-generated text often uses safe, common, high-probability phrasing. A predictability signal helps catch writing that is not just polished, but also templated.

Blind spot:

Predictable writing is not automatically AI-generated. Student essays, business memos, and formal explanations often use predictable phrasing because that is normal for the genre.

---

## Confidence Scoring

The final confidence score is a weighted average:

```text
combined_score = (0.45 * llm_score) + (0.30 * stylometric_score) + (0.25 * predictability_score)
```

Weights:

```text
LLM signal:              45%
Stylometric signal:      30%
Predictability signal:   25%
```

I weighted the LLM signal highest because it gives the broadest judgment of tone and semantic style. The stylometric signal gets 30% because it provides measurable structural evidence. The predictability signal gets 25% because formulaic wording is useful evidence, but predictable writing alone is not proof of AI generation.

Thresholds:

```text
0.00-0.39 = likely_human
0.40-0.74 = uncertain
0.75-1.00 = likely_ai
```

A confidence score of `0.6` means the system found mixed evidence. The text has some AI-like signals, but not enough evidence to label it as likely AI.

The `likely_ai` threshold remains intentionally conservative because a false positive is more harmful than a false negative in a writing platform. Even with the demo-friendly `0.75` cutoff, likely AI still requires multiple signals to agree. Polished or formulaic writing can remain `uncertain` when one signal is high but the others do not reinforce it strongly enough.

There is one narrow calibration exception for obvious assistant-template cases: if the LLM score is at least `0.80` and the predictability score is at least `0.70`, the result can be lifted to the `0.75` likely-AI floor. This is reported in calibration metadata as `strong_ai_pattern_agreement`, and it still does not treat polished writing alone as AI-generated.

---

## Scoring Examples

### Lower-confidence / human-like case

Input type: casual personal writing

```json
{
  "attribution": "likely_human",
  "confidence": 0.3029,
  "signal_scores": {
    "llm": 0.3,
    "predictability": 0.0521,
    "stylometric": 0.5164
  }
}
```

This scored low because the text had personal experience, casual phrasing, and low predictability. The stylometric score was moderate, but the LLM and predictability signals pulled the combined score down.

---

### Higher-confidence / AI-like case

Input type: extremely formulaic AI-style writing

```json
{
  "attribution": "likely_ai",
  "confidence": 0.8409,
  "signal_scores": {
    "llm": 0.9,
    "predictability": 0.9405,
    "stylometric": 0.6693
  }
}
```

This scored high because multiple signals agreed: the LLM judged it AI-like, the predictability signal found repeated formulaic phrasing, and the stylometric signal was also elevated.

---

### Local Ollama/Qwen Case

Input type: formulaic AI-style writing using local Ollama/Qwen

```json
{
  "attribution": "uncertain",
  "confidence": 0.5652,
  "llm_provider": "ollama",
  "signal_scores": {
    "llm": 0.6,
    "predictability": 0.6466,
    "stylometric": 0.4451
  }
}
```

This confirms the same `/submit` endpoint can use local Ollama/Qwen for the LLM signal while preserving the same API response shape.

---

### Uncertain case

Input type: polished but not extreme AI-like text

```json
{
  "attribution": "uncertain",
  "confidence": 0.7146,
  "signal_scores": {
    "llm": 0.8,
    "predictability": 0.7506,
    "stylometric": 0.5564
  }
}
```

This stayed uncertain because the score did not reach the 0.75 likely-AI threshold with enough total combined evidence. This reflects the system's conservative false-positive design and its requirement that multiple signals agree.

---

## Transparency Labels

The system returns one of three plain-English labels.

### Likely Human

```text
This text appears more consistent with human-written work based on the signals reviewed. This label is not a guarantee, but the system did not find strong signs of AI generation.
```

### Uncertain

```text
We are not confident enough to determine whether this text was written by a person or generated with AI. This result should not be treated as a final judgment.
```

### Likely AI

```text
This text shows strong signs of AI generation based on multiple signals, but this is not a final judgment. The creator may appeal this label.
```

These labels avoid saying “this was written by AI” because the system is not proof of authorship.

---

## Appeals Workflow

A creator can appeal any classification by submitting the original `content_id` and their reasoning.

The system does not automatically reclassify the text. Instead, it:

1. Finds the original submission.
2. Records an appeal entry in the audit log.
3. Marks the appeal status as `under_review`.
4. Preserves the creator’s reasoning with the original classification.

A human reviewer would be able to see:

- original content ID
- creator ID
- original attribution
- original confidence
- individual signal scores
- appeal reasoning
- appeal status

---

## Rate Limiting

The `/submit` endpoint is rate-limited with Flask-Limiter:

```text
10 per minute;50 per day
```

I chose `10 per minute` because a real writer may submit several drafts quickly while revising, but more than 10 submissions in a minute likely indicates automated abuse or flooding.

I chose `50 per day` because it is enough for normal writing and revision workflows while limiting large-scale automated use of the API.

Rate-limit test output:

```text
200
200
200
200
200
200
200
200
200
200
429
429
```

The first 10 rapid `POST /submit` requests succeeded. The 11th and 12th returned `429`, confirming the 10-per-minute limit works.

---

## Audit Log

The audit log is stored in a local SQLite database and returned through the API as structured JSON.

SQLite replaced the original JSON-file audit log. This improves reliability because SQLite writes are transactional and safer than manually reading and rewriting a JSON file.

Submission entries include:

- timestamp
- content ID
- creator ID
- attribution result
- confidence score
- LLM score
- stylometric score
- predictability score
- status
- entry type

Appeal entries include:

- timestamp
- content ID
- creator ID
- original attribution
- original confidence
- appeal reasoning
- status: `under_review`
- entry type

The log can be viewed with:

```powershell
Invoke-RestMethod http://127.0.0.1:5000/log
```

---

## Testing

The project includes a pytest suite covering unit logic, local persistence, provider selection, and API workflows.

Run tests with:

```powershell
python -m pytest
```

Recommended on Windows/local development to avoid locked repo-local pytest temp folders:

```powershell
python scripts/run_tests.py
```

PowerShell convenience wrapper:

```powershell
.\scripts\run_tests.ps1
```

The helper creates a fresh unique `--basetemp` directory under the OS temp folder for each run, which avoids the Windows locking issue that can happen with reused repo-local `.pytest-tmp*` folders.

Latest verified result:

```text
67 passed, 1 warning in 0.49s
```

Test coverage includes:

- scoring thresholds and weighted formula
- transparency label selection
- stylometric detector output shape and bounds
- predictability detector output shape and ranking behavior
- metadata provenance scoring
- SQLite audit log initialization, writes, reads, and appeal entries
- lightweight SQLite write workflow checks
- LLM provider selection for Groq and Ollama
- robust LLM JSON parsing, including markdown-fenced JSON
- Ollama fallback behavior without requiring a real Ollama call
- Flask route smoke tests
- `/submit` provider override behavior
- `/appeal` workflow behavior
- `/log` route behavior
- `/analytics` route behavior
- `/verify-creator` route behavior
- `/submit-metadata` route behavior

The tests avoid real Groq and Ollama network calls by using monkeypatching/stubs where needed.

---

## Stretch Goals

### Ensemble Detection

Implemented.

The system uses three distinct detection signals and combines them with documented weights.

### Analytics Dashboard

Implemented with:

```text
GET /analytics
```

It returns detection counts, appeal rate, average confidence, and LLM latency summaries.

The dashboard now also reports logged LLM provider latency so it is easier to compare local Ollama/Qwen inference with Groq cloud inference during demos and evaluation.

### Latency Benchmarking

`llm_latency_ms` measures only provider inference time inside the LLM signal path, not full HTTP request time for `/submit`.

The default `/submit` rate limit is intentionally conservative for normal app behavior.

To compare Groq and local Ollama/Qwen with a broader sample set, run:

```powershell
python scripts/benchmark_latency.py --provider groq --rounds 3
python scripts/benchmark_latency.py --provider ollama --rounds 3
```

The script sends a built-in batch of representative texts to the local Flask app at `http://127.0.0.1:5000/submit`, prints summary latency metrics, and saves timestamped JSON results under `benchmark_results/`.

For local Ollama benchmarking, you can temporarily raise the limit with:

```env
SUBMIT_RATE_LIMIT=200 per minute;1000 per day
```

Use that only for local benchmarking, not for public deployment. Ollama benchmarking is free/local, but the results are often hardware-bound.

Example local baseline values observed before these safe prompt/output controls:

- Groq around `621 ms`
- Ollama/Qwen 14B around `3116 ms`

These numbers vary based on hardware, active model, network conditions, and prompt length. Dashboard screenshots can be added later to show before/after analytics changes.

### Screenshot Plan

Dashboard latency comparison screenshots can be placed in `docs/assets/` as `analytics-before.png` and `analytics-after.png`.

### Provenance Certificate

Implemented with:

```text
POST /verify-creator
```

This creates a verified creator certificate label that is separate from the normal transparency label.

### Multi-Modal Support

Implemented with:

```text
POST /submit-metadata
```

This supports non-text structured metadata such as declared AI assistance, tool used, process notes, edit history, and human review status.

### Demo Frontend

Implemented with:

```text
GET /
```

The frontend provides a simple browser interface for the main system features. It helps demonstrate the project by letting a user submit text, view labels and scores, submit appeals, inspect the audit log, view analytics, verify creators, and test structured metadata without manually writing API requests.

### Local LLM Provider Support

Implemented.

The LLM signal can use either Groq cloud inference or local Ollama/Qwen inference. The default provider is controlled through `.env`, and the frontend includes a local demo/admin selector for switching providers during interviews or demos.

### SQLite Persistence

Implemented.

The audit log uses SQLite instead of JSON-file storage. This gives the project transactional local persistence while keeping it lightweight.

### Test Suite

Implemented.

The project includes 60 passing pytest tests for core logic and API workflows.

---

## Known Limitations

This system is a prototype and should not be treated as a reliable AI detector.

Specific limitations:

1. **Formal human writing may be over-scored.**  
   Academic essays, business memos, and resumes can be polished and predictable, which may raise the stylometric and predictability scores even when the writing is human.

2. **Creative repetition can be misread.**  
   A poem or stylistic piece that repeats simple phrases may look formulaic to the predictability signal even if the repetition is intentional.

3. **Very short text has weak evidence.**  
   One or two sentences may not provide enough information for stylometric or predictability metrics to be meaningful.

4. **Edited AI text may become uncertain.**  
   If a person heavily edits AI-generated text, the human variation may lower the score and move the result into the uncertain range.

5. **The LLM signal is not proof.**  
   Groq and Ollama provide judgments, not ground truth. That is why the system uses multiple signals and conservative thresholds.

6. **Provider selection is for local demo/admin use.**  
   The frontend provider selector is useful for demos, but in a real deployed system, provider configuration would likely be controlled by deployment settings or admin-only controls.

7. **SQLite is lightweight, not a full production database setup.**  
   SQLite is a good upgrade over JSON-file storage for this local prototype, but a larger deployed system would likely use PostgreSQL or another production database.

If this were deployed for real users, I would add stronger calibration, human review tools, authenticated audit access, larger validation sets, stricter access controls, and clearer creator-facing explanations.

---

## Spec Reflection

The planning spec helped guide the implementation because it defined the expected API shapes, signal outputs, scoring formula, thresholds, and label text before coding started. This made it easier to check whether each generated module matched the intended contract.

One way the implementation diverged from the original plan was that the first version of the predictability signal under-scored very formulaic AI-style text. The system could reach `likely_human` and `uncertain`, but not `likely_ai` through `/submit`. I revised the predictability signal so repeated formulaic phrases had a stronger effect, which made all three transparency labels reachable while still keeping casual human writing low.

A second change was adding a lightweight demo frontend after the backend was already complete. This did not change the API design, but it made the system easier to demonstrate and inspect during a walkthrough.

A third change was replacing JSON-file audit storage with SQLite after identifying the risk of race conditions and lost audit entries with manual file writes.

A fourth change was adding optional local Ollama/Qwen inference so the LLM signal can run locally on my machine instead of only through a cloud API.

A fifth change was expanding testing from basic unit checks into broader API workflow tests.

---

## Post-Submission Improvements

After the initial version of the project was submitted and graded, I made several engineering improvements based on feedback and further iteration.

### Before

The original submitted version included:

- Flask API routes for submission, appeals, logs, analytics, metadata, and verification
- three-signal scoring pipeline
- Groq-backed LLM signal
- transparency labels
- JSON-file audit storage
- rate limiting
- demo frontend
- documentation and planning files

This version worked for the project requirements, but some parts were still prototype-level.

### After

The improved version adds:

1. **SQLite audit persistence**

   The original audit log used JSON file storage. That was simple, but concurrent writes could cause race conditions or lost audit entries. I refactored the audit layer to use SQLite with transactional writes.

2. **Local Ollama/Qwen inference**

   The LLM signal now supports both Groq cloud inference and local Ollama/Qwen inference. This lets the project run the LLM-backed signal locally through my GPU setup when `LLM_PROVIDER=ollama`.

3. **Frontend provider selector**

   The frontend now includes a demo/admin provider selector for LLM-backed actions. This makes it easy to switch between Groq cloud inference and local Ollama/Qwen inference during demos.

4. **Robust model-response parsing**

   Local models often return JSON inside markdown code fences. I improved the parser so it can handle clean JSON, fenced JSON, and extra text around JSON before falling back.

5. **Expanded test suite**

   I added pytest coverage for core scoring logic, labels, detectors, SQLite persistence, metadata analysis, LLM provider selection, Ollama parsing behavior, and API workflows. The suite now has 50 passing tests.

6. **API workflow regression tests**

   The tests now cover not only individual functions but also important Flask routes and workflows, including appeals, logs, analytics, metadata submission, and creator verification.

These changes make the project more reliable, easier to demo, and stronger as an engineering portfolio project.

---

## AI Tool Usage

I used AI tools as implementation support, not as a replacement for my own design decisions.

### Instance 1: Flask route and first signal

I prompted Codex with my `planning.md` architecture and asked it to create a small Flask skeleton with `POST /submit` and a first LLM signal function. It produced `app.py` and `detectors/llm_signal.py`.

I reviewed the output and verified that:

- `/submit` accepted `creator_id` and `text`
- the response matched my API contract
- `get_llm_signal(text: str)` returned a dictionary with `score` and `reason`

I revised the LLM prompt because the first version over-scored casual human writing as AI-like. After revision, casual personal writing scored lower and matched the false-positive design better.

### Instance 2: Multi-signal scoring

I prompted Codex to generate `stylometric_signal.py`, `predictability_signal.py`, and `scoring.py` from my detection signals and uncertainty representation sections.

I verified that:

- each signal returned a `0.0–1.0` score
- `scoring.py` used the exact `45/30/25` weights from `planning.md`
- thresholds matched my planned ranges
- different inputs produced different confidence scores

I later revised the predictability signal because it was too weak for formulaic AI-style writing.

### Instance 3: Production features and frontend

I prompted Codex to add production-layer features one at a time: labels, appeals, rate limiting, analytics, creator verification, metadata support, and a simple demo frontend.

I checked each feature manually by running the API locally and testing the endpoint responses. For the frontend, I tested the browser forms and revised the result display formatting so key/value outputs were readable. I did not accept the generated code blindly; I tested each endpoint and UI section before committing.

### Instance 4: Post-feedback engineering improvements

After receiving feedback about JSON-file persistence and missing automated tests, I used Codex to help refactor the audit log from JSON storage to SQLite and to add pytest coverage.

I reviewed and tested the changes locally:

```text
50 passed in 0.55s
```

### Instance 5: Local LLM provider support

I used Codex to help add optional Ollama/Qwen support to the LLM signal while preserving Groq as the default cloud provider. I also added tests for provider selection and parser robustness.

I manually verified that local Ollama/Qwen worked through the same `/submit` endpoint:

```json
{
  "llm_provider": "ollama",
  "signal_scores": {
    "llm": 0.6,
    "predictability": 0.6466,
    "stylometric": 0.4451
  }
}
```

---

## Files

```text
app.py
detectors/
  __init__.py
  llm_signal.py
  stylometric_signal.py
  predictability_signal.py
templates/
  index.html
static/
  style.css
  script.js
tests/
  test_app_routes.py
  test_audit_log.py
  test_labels.py
  test_llm_signal.py
  test_metadata_signal.py
  test_predictability_signal.py
  test_scoring.py
  test_stylometric_signal.py
scoring.py
labels.py
audit_log.py
analytics.py
verification.py
metadata_signal.py
planning.md
requirements.txt
.env.example
.gitignore
README.md
```




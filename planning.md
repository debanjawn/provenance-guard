# Planning: Provenance Guard

## Architecture Narrative
1. A creator submits text to `POST /submit` in `app.py`.

2. `app.py` checks that the request includes both `creator_id` and `text`.

3. `app.py` creates a unique `content_id` for the submission.

4. The text is sent to `detectors/llm_signal.py`, which uses Groq to make a holistic AI-versus-human judgment.

5. The text is sent to `detectors/stylometric_signal.py`, which measures writing-style features like sentence length variance, vocabulary diversity, and punctuation density.

6. The text is sent to `detectors/predictability_signal.py`, which estimates how formulaic or predictable the writing is.

7. Each detector returns a score from `0.0` to `1.0`, where higher means more AI-like.

8. `scoring.py` combines the scores using a weighted average: 45% LLM, 30% stylometric, and 25% predictability.

9. `scoring.py` maps the combined score to `likely_human`, `uncertain`, or `likely_ai`.

10. `labels.py` turns the result and confidence score into a plain-English transparency label.

11. `audit_log.py` saves the decision with the timestamp, `content_id`, `creator_id`, signal scores, confidence score, attribution result, label text, and status.

12. `app.py` returns a structured JSON response with the `content_id`, attribution, confidence, signal scores, label, and status.

## Appeal Flow
1. A creator submits an appeal to `POST /appeal`.

2. The request includes `content_id`, `creator_id`, and `creator_reasoning`.

3. `app.py` validates the appeal request and finds the original submission.

4. The submission status is updated to `under_review`.

5. `audit_log.py` records the appeal with the original classification and creator reasoning.

6. The system does not automatically reclassify the text during appeal.

7. `app.py` returns a confirmation response showing that the appeal was received.

## Detection Signals
### Signal 1: LLM Signal

`detectors/llm_signal.py` uses Groq to judge whether the text appears AI-generated or human-written.

It measures tone, flow, genericness, semantic coherence, polish, and whether the writing feels natural or templated.

AI writing often sounds smooth, polished, and generalized, while human writing can be more uneven, specific, emotional, or idiosyncratic.

Blind spot: formal human writing, academic writing, or professionally edited writing may be falsely flagged as AI-like.

### Signal 2: Stylometric Signal

`detectors/stylometric_signal.py` measures writing statistics like sentence length variance, vocabulary diversity, punctuation density, and repetition.

AI text often has smoother and more uniform structure, while human writing usually has more variation in sentence length, punctuation, and word choice.

Blind spot: polished essays, resumes, academic paragraphs, creative writing, or poetry may confuse these metrics.

### Signal 3: Predictability Signal

`detectors/predictability_signal.py` estimates how formulaic or predictable the text is.

It looks for repetition, common transition phrases, repeated sentence openings, generic phrasing, and low vocabulary surprise.

AI often chooses safe and common phrasing, while human writing may include more unexpected, personal, awkward, or specific language.

Blind spot: predictable writing is not automatically AI-generated because student essays, business writing, and formal explanations can also be predictable.

## False Positive Scenario
A false positive happens when a human writer’s work is incorrectly labeled as AI-generated. This is harmful because it can damage the creator’s reputation and make the platform feel unfair.

To reduce this risk, the system uses conservative thresholds:

- `0.00–0.39` = `likely_human`
- `0.40–0.79` = `uncertain`
- `0.80–1.00` = `likely_ai`

The system does not label text as `likely_ai` unless the combined score is high. Middle-range scores become `uncertain` instead of forcing a binary decision.

The label also avoids final accusations. Instead of saying “this was written by AI,” it says the text “shows signs” of AI generation.

If the creator disagrees, they can appeal through `POST /appeal`. The system updates the content status to `under_review` and logs the creator’s reasoning with the original classification.

## API Surface
### `POST /submit`

Accepts a creator’s text submission and returns an attribution result.

Request:

```json
{
  "creator_id": "creator_123",
  "text": "This is the text being submitted."
}
```

Response:

```json
{
  "content_id": "abc123",
  "attribution": "uncertain",
  "confidence": 0.62,
  "signal_scores": {
    "llm": 0.70,
    "stylometric": 0.55,
    "predictability": 0.58
  },
  "label": "We are not confident enough to determine whether this text was written by a person or generated with AI.",
  "status": "classified"
}
```

### `POST /appeal`

Lets a creator dispute a classification.

Request:

```json
{
  "content_id": "abc123",
  "creator_id": "creator_123",
  "creator_reasoning": "I wrote this myself and can provide drafts."
}
```

Response:

```json
{
  "content_id": "abc123",
  "status": "under_review",
  "message": "Appeal received."
}
```

### `GET /log`

Returns recent structured audit log entries.

Response:

```json
{
  "entries": [
    {
      "timestamp": "2026-06-27T12:00:00",
      "content_id": "abc123",
      "creator_id": "creator_123",
      "attribution": "uncertain",
      "confidence": 0.62,
      "signal_scores": {
        "llm": 0.70,
        "stylometric": 0.55,
        "predictability": 0.58
      },
      "label": "We are not confident enough to determine whether this text was written by a person or generated with AI.",
      "status": "classified"
    }
  ]
}
```

### Stretch Endpoints

- `GET /analytics` — returns dashboard metrics like verdict counts, appeal rate, and average confidence.
- `POST /verify-creator` — marks a creator as verified for the provenance certificate feature.
- `POST /submit-metadata` — processes structured metadata for the multi-modal support feature.

## Architecture Diagram
### Submission Flow

```text
POST /submit
(raw JSON: creator_id, text)
        ↓
app.py validates input
(validated creator_id + raw text)
        ↓
Generate content_id
(content_id + creator_id + raw text)
        ↓
detectors/llm_signal.py
(raw text → llm_score + llm_reason)
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
JSON response
(content_id + attribution + confidence + signal_scores + label + status)
```

### Appeal Flow

```text
POST /appeal
(raw JSON: content_id, creator_id, creator_reasoning)
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
JSON response
(content_id + status + confirmation message)
```
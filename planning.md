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

---

## Detection Signals

### Signal 1: LLM Signal

`detectors/llm_signal.py` uses Groq to judge whether the text appears AI-generated or human-written.

It measures tone, flow, genericness, semantic coherence, polish, and whether the writing feels natural or templated.

AI writing often sounds smooth, polished, and generalized, while human writing can be more uneven, specific, emotional, or idiosyncratic.

Expected output:

```json
{
  "score": 0.82,
  "reason": "The text is polished, generic, and uses a predictable explanatory structure."
}
```

Blind spot: formal human writing, academic writing, or professionally edited writing may be falsely flagged as AI-like.

### Signal 2: Stylometric Signal

`detectors/stylometric_signal.py` measures writing statistics like sentence length variance, vocabulary diversity, punctuation density, and repetition.

AI text often has smoother and more uniform structure, while human writing usually has more variation in sentence length, punctuation, and word choice.

Expected output:

```json
{
  "score": 0.61,
  "reason": "The text has low sentence length variance and moderate vocabulary diversity.",
  "metrics": {
    "sentence_length_variance": 4.2,
    "type_token_ratio": 0.48,
    "punctuation_density": 0.06
  }
}
```

Blind spot: polished essays, resumes, academic paragraphs, creative writing, or poetry may confuse these metrics.

### Signal 3: Predictability Signal

`detectors/predictability_signal.py` estimates how formulaic or predictable the text is.

It looks for repetition, common transition phrases, repeated sentence openings, generic phrasing, and low vocabulary surprise.

AI often chooses safe and common phrasing, while human writing may include more unexpected, personal, awkward, or specific language.

Expected output:

```json
{
  "score": 0.70,
  "reason": "The text uses repeated transitions and formulaic phrasing.",
  "metrics": {
    "transition_density": 0.08,
    "repetition_rate": 0.12,
    "common_phrase_matches": 4
  }
}
```

Blind spot: predictable writing is not automatically AI-generated because student essays, business writing, and formal explanations can also be predictable.

---

## Uncertainty Representation

Each detector returns a score from `0.0` to `1.0`, where higher means the text appears more AI-like.

- `0.0` means strongly human-like.
- `0.5` means mixed or uncertain.
- `1.0` means strongly AI-like.

Raw signal outputs will be normalized into scores from `0.0` to `1.0`.

- The LLM signal will ask Groq for a score from `0.0` to `1.0` and a short reason.
- The stylometric signal will calculate metrics like sentence length variance, type-token ratio, punctuation density, and repetition, then convert those metrics into a score based on whether the text looks more uniform or more varied.
- The predictability signal will calculate repetition rate, transition density, and common phrase matches, then convert those metrics into a score based on how formulaic the text appears.

These scores are not treated as proof. They are calibrated into a combined confidence score using a weighted average.

The final confidence score uses this formula:

```text
combined_score = (0.45 * llm_score) + (0.30 * stylometric_score) + (0.25 * predictability_score)
```

The system uses these thresholds:

- `0.00–0.39` = `likely_human`
- `0.40–0.79` = `uncertain`
- `0.80–1.00` = `likely_ai`

A confidence score of `0.6` means the system found mixed evidence. The text has some AI-like signals, but not enough evidence to label it as likely AI. In this system, `0.6` falls into the `uncertain` range.

The `likely_ai` threshold is intentionally high because falsely labeling a human creator’s work as AI-generated is more harmful than missing some AI-generated text.

---

## Transparency Label Design

### Likely Human Label

“This text appears more consistent with human-written work based on the signals reviewed. This label is not a guarantee, but the system did not find strong signs of AI generation.”

### Uncertain Label

“We are not confident enough to determine whether this text was written by a person or generated with AI. This result should not be treated as a final judgment.”

### Likely AI Label

“This text shows strong signs of AI generation based on multiple signals, but this is not a final judgment. The creator may appeal this label.”

The labels are written in plain language for non-technical readers. The likely-AI label avoids saying “this was written by AI” because the system is not proof of authorship.

---

## Appeals Workflow

A creator can submit an appeal if they disagree with a classification.

The appeal request goes to `POST /appeal` and includes:

- `content_id`
- `creator_id`
- `creator_reasoning`

When an appeal is received:

1. `app.py` validates the appeal request.
2. The system finds the original submission by `content_id`.
3. The submission status changes from `classified` to `under_review`.
4. `audit_log.py` records the appeal alongside the original classification.
5. The system does not automatically reclassify the text.
6. `app.py` returns a confirmation response.

A human reviewer would see:

- original text or text preview
- `content_id`
- `creator_id`
- original attribution
- original confidence score
- individual signal scores
- original transparency label
- creator reasoning
- timestamp
- current status: `under_review`

---

## False Positive Scenario

A false positive happens when a human writer’s work is incorrectly labeled as AI-generated. This is harmful because it can damage the creator’s reputation and make the platform feel unfair.

To reduce this risk, the system uses conservative thresholds. The system does not label text as `likely_ai` unless the combined score is at least `0.80`. Middle-range scores become `uncertain` instead of forcing a binary decision.

For example, if a human submits a polished academic paragraph, the signals might score it as somewhat AI-like:

```text
LLM score: 0.78
Stylometric score: 0.72
Predictability score: 0.68
Combined score: 0.735
```

Even though the text has AI-like traits, the final result would be `uncertain`, not `likely_ai`.

The label also avoids final accusations. Instead of saying “this was written by AI,” it says the text “shows strong signs” of AI generation and gives the creator an appeal path.

---

## Anticipated Edge Cases

1. A formal academic paragraph written by a human may be scored as AI-like because it is polished, structured, and predictable.

2. A poem with heavy repetition and simple vocabulary may confuse the stylometric and predictability signals because repetition is part of the style.

3. A short text, such as one or two sentences, may not provide enough evidence for reliable scoring.

4. AI-generated text that has been heavily edited by a human may fall into the uncertain range because the human edits add variation.

5. A business memo or resume may look AI-like because those genres often use formal, predictable language.

---

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

---

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

This architecture section will be used as the reference for implementation in Milestones 3–5.

---

## AI Tool Plan

I will use AI tools as implementation support, not as a replacement for my own design decisions.

### M3: Submission Endpoint + First Signal

I will provide the AI tool with the architecture narrative, API surface, and detection signals section.

I will ask it to generate:

- a basic Flask app skeleton
- a `POST /submit` route
- the first signal function for `detectors/llm_signal.py`

I will verify the output by testing the signal function directly with a few inputs before wiring it into the endpoint.

### M4: Second/Third Signal + Confidence Scoring

I will provide the AI tool with the detection signals, uncertainty representation, and architecture diagram.

I will ask it to generate:

- `detectors/stylometric_signal.py`
- `detectors/predictability_signal.py`
- `scoring.py`

I will verify that scores vary meaningfully between clearly AI-like text, clearly human-like text, and borderline examples.

### M5: Production Layer

I will provide the AI tool with the transparency label design, appeals workflow, API surface, and architecture diagram.

I will ask it to generate:

- `labels.py`
- `audit_log.py`
- the `POST /appeal` endpoint
- the `GET /log` endpoint
- rate limiting setup

I will verify that all three label variants are reachable, appeals update status to `under_review`, and the audit log records both classifications and appeals.
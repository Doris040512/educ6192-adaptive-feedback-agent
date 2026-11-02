# Adaptive Feedback — EDUC 6192 Assignment 4

Version 2 keeps the existing instructor website and single-agent architecture while adding a structured rubric consistency assessment and a deterministic backend action gate. It is based on [the Assignment 3 reference notebook](reference/assignment3.ipynb), which remains unchanged.

## Local setup

Requires Python 3.10 or newer. From the repository root:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

On Windows, use `.venv\Scripts\activate` instead of the activation command above. Open `http://127.0.0.1:8000` in a browser. The page must be served through FastAPI. Stop the server with Ctrl+C.

`GET /health` checks the web backend only; it does not make an API call. Local API documentation is available at `/docs`.

## Version 2 architecture

The app remains a single agent with one LLM decision request per submitted form. The model receives only the assignment instructions and grading rubric. Student response remains in the existing request and validation contract, but is deliberately excluded from the rubric consistency assessment so that changing the student's writing cannot determine whether the rubric itself is consistent.

The model returns a structured assessment with:

- `consistency_status`: `consistent`, `ambiguous`, or `contradictory`;
- relevant rubric criteria or short evidence excerpts;
- concise explanation;
- blocking issue details and supporting excerpts when clarification is needed; and
- one focused instructor question for ambiguous or contradictory cases.

The backend derives the action; the model does not choose it:

| Assessment | Backend action |
| --- | --- |
| Consistent, with no blocking issue | `ANALYZE` |
| Materially ambiguous, with issue evidence and a question | `CLARIFY` |
| Contradictory, with issue evidence and a question | `CLARIFY` |
| Missing, invalid, or internally inconsistent assessment | Error response; no action |

The gate rejects a `consistent` assessment that also reports a blocking issue. Non-consistent assessments must include blocking issue evidence and a clarification question. Directly conflicting requirements, such as requiring a clear position while forbidding any position, must be sent to the instructor for clarification; the app does not prioritize or reconcile them. Broad but usable criteria do not automatically require clarification. The model prompt asks it to reserve ambiguity for cases where reasonable interpretations could change what counts as meeting a requirement or would require inventing a consequential criterion.

## Instructor clarification workflow

Agent Activity displays the selected action, explanation, relevant rubric evidence, and the focused question when applicable. For `CLARIFY`, the instructor can revise the assignment or rubric in the existing input fields and submit again. The system does not resolve consequential instructional judgments on the instructor's behalf. `ANALYZE` only signals that the rubric appears usable for a later step; it does not analyze the response or generate feedback.

The website layout and core input workflow are preserved. Feedback preview panels remain placeholders. The app does not generate student feedback, assign grades, rewrite essays, or run additional agent workflows.

## API contract

`POST /api/decision` accepts JSON with `assignment`, `rubric`, and `student_response` (text, up to 20,000 characters each). Results retain the existing fields `status`, `action`, `explanation`, `clarification_question`, and `missing_fields`. Version 2 adds `consistency_status` and `evidence` to make the assessment visible. Existing successful result states and validation/configuration/provider error behavior remain; malformed or missing model assessments use `assessment_error` and never include an action.

| HTTP | Status | Meaning |
| --- | --- | --- |
| 200 | `decision_complete` | Backend-gated action with consistency status and evidence. `CLARIFY` includes one question. |
| 422 | `validation_error` | Missing fields use their UI labels; malformed requests receive a safe message. No model call. |
| 503 | `configuration_error` | `FEEDBACK_API_KEY` is absent. No model call. |
| 502 | `assessment_error` | Model assessment is missing, invalid, or internally inconsistent. No action selected. |
| 502 | `api_error` | Provider failure, refusal, or timeout. No action selected. |

## Backend API configuration and privacy

Set `FEEDBACK_API_KEY` securely in the server process environment before starting Uvicorn. Do not put keys in frontend files, Git, screenshots, or chat. The app does not read `.env` files automatically. `FEEDBACK_MODEL` optionally selects a structured-output-compatible model; the default is `gpt-4o-mini`. No API calls are made at startup or by `/health`.

Use fictional, non-identifying practice text only. Submitting sends assignment and rubric text to the model provider; the student response is not included in the model request. No key is sent to the browser. Requests use `store=False`; this does not override provider retention policies. The application does not persist or log submitted text or use browser storage. This development server has no authentication or rate limiting; do not expose it as a public service.

## Regression testing

Install test dependencies and run the offline checks:

```sh
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

Offline tests mock structured model outputs and cover normal, materially ambiguous, and contradictory rubrics; absent/invalid assessments; student response independence; the blocking-issue gate; input validation; and safe provider failures. These tests establish backend behavior for the supplied structured outputs. They do **not** establish that a live model will reliably detect ambiguity or contradiction in real rubrics.

Optional live API tests are separate, skipped by default, and make paid requests with fictional text. Run only when a real `FEEDBACK_API_KEY` is securely configured:

```sh
RUN_LIVE_API_TESTS=1 python -m unittest discover -s tests -v
```

Do not use the live suite as a substitute for instructor review.

## Version 1 and Version 2

Version 1 asked the model to select `ANALYZE` or `CLARIFY` directly. Testing showed it could miss subjective ambiguity and proceed despite a contradiction. Version 2 asks for a structured assessment of assignment and rubric consistency, excludes the student response from that assessment, and applies a fail-closed backend action gate. The activity panel now shows evidence and the instructor clarification question. The website's overall two-column layout, inputs, clear action, and feedback placeholders remain in place.

## Limitations and remaining risks

The backend enforces schema and consistency rules, but it cannot guarantee the model's semantic assessment is correct. The model can still miss subtle conflicts, overstate ambiguity, select weak excerpts, or misinterpret educational context. A model-generated assessment is not a substitute for instructor judgment. The assessment is a single request with no independent verifier or retry workflow. Analyze remains a permission signal only; feedback analysis and generation are future work.

## Project layout

- `main.py`: FastAPI app, homepage, health endpoint, and decision endpoint.
- `decision.py`: input validation, structured rubric assessment, deterministic action gate, and safe failure responses.
- `static/index.html`, `static/styles.css`, `static/app.js`: instructor workspace and Agent Activity display.
- `tests/test_decision.py`: offline mocked regression checks and opt-in live cases.
- `requirements.txt`, `requirements-dev.txt`: runtime and test dependencies.
- `reference/assignment3.ipynb`: unchanged Assignment 3 reference, not executed by the website.

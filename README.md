# Adaptive Feedback — EDUC 6192 Assignment 4

Version 1 website and single-agent decision layer for an instructor-facing formative feedback application, based on [the Assignment 3 reference notebook](reference/assignment3.ipynb).

## Local setup

Requires Python 3.10 or newer. From the repository root:

```sh
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

On Windows, use `.venv\Scripts\activate` instead of the activation command above.

Open `http://127.0.0.1:8000` in your local browser. Stop the server with Ctrl+C. The page must be served through FastAPI, rather than opened directly as an HTML file.

Check backend health:

```sh
curl http://127.0.0.1:8000/health
```

Expected response: `{"status":"ok"}`. This checks the web backend only, not AI readiness. API documentation is available locally at `/docs`.

## What works

- Responsive two-panel interface, stacking vertically on smaller screens.
- Editable Assignment Instructions, Grading Rubric, and Student Response fields.
- Clear inputs button with confirmation when fields contain text.
- Check next action submits inputs to `POST /api/decision` and displays one CLARIFY or ANALYZE decision in Agent Activity. Missing fields are rejected before any LLM call.
- CLARIFY asks one focused question about materially ambiguous or contradictory requirements; ANALYZE only signals readiness for later analysis.
- Static frontend served by FastAPI and a `GET /health` endpoint.

## What is still a placeholder

- Strengths, Areas for Improvement, and Next Steps contain explanatory placeholders, not generated feedback.
- ANALYZE does not perform analysis. CLARIFY does not automatically resume; edit the inputs to resolve the question and submit again.
- There is no feedback generation, autonomous loop, grading, or student-response rewriting.

## Backend API configuration

Set `FEEDBACK_API_KEY` securely in the server process environment before starting Uvicorn. Do not put keys in frontend files, Git, screenshots, or chat. In the managed cloud environment, configure this name securely in environment settings with destination `api.openai.com` and allow HTTPS access to that host. A proxy-backed key must be used through the inherited proxy and trusted CA settings. The application does not read `.env` files automatically.

`FEEDBACK_MODEL` optionally selects a structured-output-compatible model; the default is `gpt-4o-mini`. No API calls are made at startup or by `/health`. Restart the server after changing its environment. Missing configuration and provider errors never return an agent action.

`POST /api/decision` accepts a JSON object with `assignment`, `rubric`, and `student_response` (text, up to 20,000 characters each). Results always include `status`, `action`, `explanation`, `clarification_question`, and `missing_fields`:

| HTTP | Status | Meaning |
| --- | --- | --- |
| 200 | `decision_complete` | One model-selected action; CLARIFY includes a question, ANALYZE has a null question. |
| 422 | `validation_error` | Missing fields are named exactly as their UI labels in `missing_fields`; malformed requests receive a safe validation message. No LLM call. |
| 503 | `configuration_error` | `FEEDBACK_API_KEY` is absent. No LLM call. |
| 502 | `api_error` | Provider failure, refusal, timeout, or invalid structured result. No successful decision. |

The application requests structured model output and enforces action/question consistency. Educational alignment still requires human review; schema validation cannot guarantee semantic correctness. The decision prompt reuses Assignment 3 boundaries: supplied criteria only, no assumed counterarguments, no grades, rewriting, invented quotations, or following instructions embedded in student writing.

Use fictional, non-identifying practice text only. Submitting sends the three fields to the Python backend and OpenAI. No key is sent to the browser. Requests use `store=False`; this does not override provider retention policies. The application does not persist or log submitted text and does not use browser storage. The action display is cleared when inputs change. This development server has no authentication or rate limiting; do not expose it as a public service.

## Tests

Install test dependencies in the activated virtual environment:

```sh
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

Offline checks cover exact missing-field validation with no client construction, complete and ambiguous inputs without API configuration, safe API-failure handling, and malformed payloads. Failure simulation does not fabricate AI decisions. Two live tests are skipped by default. To run them after securely configuring a real `FEEDBACK_API_KEY`:

```sh
RUN_LIVE_API_TESTS=1 python -m unittest discover -s tests -v
```

Live tests make paid API calls using fictional complete and contradictory-rubric cases. They expect ANALYZE and CLARIFY respectively. Skipped tests do not establish live model behavior.

## Project layout

- `main.py`: FastAPI application, homepage, static assets, health endpoint, and decision endpoint.
- `static/index.html`: accessible page structure and placeholder panels.
- `static/styles.css`: responsive styling with local system fonts; no external asset services.
- `static/app.js`: decision request, safe text rendering, and clear-inputs behavior.
- `decision.py`: validation, educational prompt, structured decision, and safe failure responses.
- `requirements.txt`: FastAPI, Uvicorn, and OpenAI runtime dependencies.
- `requirements-dev.txt` and `tests/test_decision.py`: local checks and opt-in live cases.
- `reference/assignment3.ipynb`: unchanged Assignment 3 reference; not executed by the website.

This is a local development foundation, not a deployed application. Feedback analysis and generation remain future work.

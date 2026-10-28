# Adaptive Feedback — EDUC 6192 Assignment 4

Version 1 website and backend foundation for an instructor-facing formative feedback application, based on [the Assignment 3 reference notebook](reference/assignment3.ipynb).

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
- Static frontend served by FastAPI and a `GET /health` endpoint.

## What is still a placeholder

- Strengths, Areas for Improvement, and Next Steps contain explanatory placeholders, not generated feedback.
- Agent Activity is not connected to any agent; no actions are recorded or simulated.
- Generate feedback is intentionally disabled. No feedback submission endpoint, OpenAI integration, or agent decision loop exists yet.

No API credentials are required for this version. Use fictional, non-identifying practice text only. Application JavaScript does not send inputs to the backend, save them in browser storage, or log them. There is no database or session persistence. Browser-managed form restoration may vary by browser.

## Project layout

- `main.py`: FastAPI application, homepage, static assets, and health endpoint.
- `static/index.html`: accessible page structure and placeholder panels.
- `static/styles.css`: responsive styling with local system fonts; no external asset services.
- `static/app.js`: local clear-inputs behavior; no network requests.
- `requirements.txt`: FastAPI and Uvicorn runtime dependencies.
- `reference/assignment3.ipynb`: unchanged Assignment 3 reference; not executed by the website.

This is a local development foundation, not a deployed application. Future development will add secure backend credential loading and bounded agent-controlled feedback generation.

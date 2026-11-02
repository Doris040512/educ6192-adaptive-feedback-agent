"""Assignment 4, Version 1: a single formative-feedback decision."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from decision import DecisionInput, DecisionResult, select_action


STATIC_DIR = Path(__file__).resolve().parent / "static"

app = FastAPI(title="Adaptive Feedback · Assignment 4 Version 2")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.exception_handler(RequestValidationError)
async def invalid_request(request, exc):
    # FastAPI's default validation details may echo submitted student data.
    return JSONResponse(status_code=422, content=DecisionResult(
        status="validation_error",
        explanation="Send a JSON object with assignment, rubric, and student_response as text (maximum 20,000 characters each).",
    ).model_dump())


@app.post("/api/decision", response_model=DecisionResult)
async def decision(inputs: DecisionInput):
    code, result = await select_action(inputs)
    return JSONResponse(status_code=code, content=result.model_dump())


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC_DIR / "index.html")

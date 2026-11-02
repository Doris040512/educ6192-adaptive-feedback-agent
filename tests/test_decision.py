"""Offline structural checks and separately opt-in live API cases."""
import json
import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import httpx

from decision import (
    DecisionInput,
    RubricAssessment,
    result_from_assessment,
    select_action,
)
from main import app

COMPLETE = {
    "assignment": "Write a paragraph supporting your position on classroom AI with two reasons.",
    "rubric": "Clear position; two relevant reasons with explanations; logical organization.",
    "student_response": "AI can help explain difficult concepts. It can also offer practice questions.",
}
AMBIGUOUS = {
    **COMPLETE,
    "rubric": "Show strong understanding and provide appropriate support.",
}
CONTRADICTORY = {
    **COMPLETE,
    "assignment": "Take a clear position on classroom AI.",
    "rubric": "State a clear position. Do not take a position.",
}


def assessment(status="consistent"):
    if status == "consistent":
        return RubricAssessment(
            consistency_status="consistent",
            evidence=[{"criterion": "Reasons", "excerpt": "two relevant reasons with explanations"}],
            blocking_issues=[],
            explanation="The requirements give usable guidance for a later review.",
            clarification_question=None,
        )
    label = "ambiguous" if status == "ambiguous" else "contradictory"
    return RubricAssessment(
        consistency_status=label,
        evidence=[{"criterion": "Position", "excerpt": "State a clear position"}],
        blocking_issues=[{
            "issue": "The rubric does not define the requirement clearly enough.",
            "evidence": [{"criterion": "Position", "excerpt": "Do not take a position"}],
        }],
        explanation="The requirement needs instructor clarification before proceeding.",
        clarification_question="Should students take a position, or should they avoid stating one?",
    )


class FakeClient:
    """Small async client stand-in; never contacts the provider."""
    def __init__(self, output, captured=None):
        self.output = output
        self.captured = captured
        self.responses = self

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def parse(self, **kwargs):
        if self.captured is not None:
            self.captured.append(kwargs)
        return SimpleNamespace(status="completed", output_parsed=self.output)


class LocalDecisionTests(unittest.IsolatedAsyncioTestCase):
    async def request(self, payload):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            return await client.post("/api/decision", json=payload)

    async def mock_assessment(self, inputs, output):
        with patch.dict(os.environ, {"FEEDBACK_API_KEY": "offline-test-key"}), patch(
            "decision.AsyncOpenAI", return_value=FakeClient(output)
        ):
            return await select_action(DecisionInput(**inputs))

    async def test_normal_rubric_analyze(self):
        code, result = await self.mock_assessment(COMPLETE, assessment())
        self.assertEqual(code, 200)
        self.assertEqual(result.action, "ANALYZE")
        self.assertEqual(result.consistency_status, "consistent")

    async def test_materially_ambiguous_rubric_clarify(self):
        code, result = await self.mock_assessment(AMBIGUOUS, assessment("ambiguous"))
        self.assertEqual(code, 200)
        self.assertEqual(result.action, "CLARIFY")
        self.assertEqual(result.consistency_status, "ambiguous")
        self.assertTrue(result.evidence)
        self.assertTrue(result.clarification_question)

    async def test_contradictory_position_requirements_clarify(self):
        code, result = await self.mock_assessment(CONTRADICTORY, assessment("contradictory"))
        self.assertEqual(code, 200)
        self.assertEqual(result.action, "CLARIFY")
        self.assertEqual(result.consistency_status, "contradictory")

    async def test_missing_or_invalid_assessment_is_not_success(self):
        for output in (None, {"consistency_status": "unclear"}):
            code, result = await self.mock_assessment(COMPLETE, output)
            self.assertEqual(code, 502)
            self.assertEqual(result.status, "assessment_error")
            self.assertIsNone(result.action)

    async def test_student_response_is_excluded_from_consistency_assessment(self):
        captured = []
        with patch.dict(os.environ, {"FEEDBACK_API_KEY": "offline-test-key"}), patch(
            "decision.AsyncOpenAI", side_effect=lambda **_: FakeClient(assessment(), captured)
        ):
            for response_text in ("First student answer.", "A completely different answer."):
                data = {**COMPLETE, "student_response": response_text}
                code, result = await select_action(DecisionInput(**data))
                self.assertEqual(code, 200)
                self.assertEqual(result.consistency_status, "consistent")
        self.assertEqual(len(captured), 2)
        submitted = [json.loads(call["input"]) for call in captured]
        self.assertEqual(submitted[0], submitted[1])
        self.assertNotIn("student_response", submitted[0])

    async def test_reported_blocking_issue_cannot_result_in_analyze(self):
        inconsistent = assessment().model_copy(update={
            "blocking_issues": assessment("ambiguous").blocking_issues,
        })
        with self.assertRaises(ValueError):
            result_from_assessment(inconsistent)

    async def test_missing_rubric_does_not_construct_client(self):
        with patch("decision.AsyncOpenAI", side_effect=AssertionError("Must not call LLM")):
            response = await self.request({**COMPLETE, "rubric": "   "})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["missing_fields"], ["Grading Rubric"])
        self.assertEqual(response.json()["status"], "validation_error")
        self.assertIsNone(response.json()["action"])

    async def test_all_missing_fields_named(self):
        with patch("decision.AsyncOpenAI", side_effect=AssertionError("Must not call LLM")):
            response = await self.request({})
        self.assertEqual(response.json()["missing_fields"], [
            "Assignment Instructions", "Grading Rubric", "Student Response",
        ])

    async def test_configuration_and_provider_errors_are_not_success(self):
        with patch.dict(os.environ, {}, clear=True), patch(
            "decision.AsyncOpenAI", side_effect=AssertionError("No key")
        ):
            response = await self.request(COMPLETE)
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["status"], "configuration_error")
        self.assertIsNone(response.json()["action"])

        with patch.dict(os.environ, {"FEEDBACK_API_KEY": "offline-test-key"}), patch(
            "decision.AsyncOpenAI", side_effect=RuntimeError("private provider details")
        ):
            response = await self.request(COMPLETE)
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()["status"], "api_error")
        self.assertIsNone(response.json()["action"])
        self.assertNotIn("private provider details", response.text)

    async def test_invalid_payload_does_not_echo_input(self):
        response = await self.request({**COMPLETE, "rubric": {"private": "private student content"}})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["status"], "validation_error")
        self.assertNotIn("private student content", response.text)


@unittest.skipUnless(os.environ.get("RUN_LIVE_API_TESTS") == "1" and os.environ.get("FEEDBACK_API_KEY"),
                     "Requires RUN_LIVE_API_TESTS=1 and a real FEEDBACK_API_KEY; calls incur API usage")
class LiveDecisionTests(unittest.IsolatedAsyncioTestCase):
    async def test_complete_case_analyze(self):
        code, result = await select_action(DecisionInput(**COMPLETE))
        self.assertEqual(code, 200)
        self.assertEqual(result.status, "decision_complete")
        self.assertEqual(result.action, "ANALYZE")

    async def test_contradictory_rubric_clarify(self):
        code, result = await select_action(DecisionInput(**CONTRADICTORY))
        self.assertEqual(code, 200)
        self.assertEqual(result.status, "decision_complete")
        self.assertEqual(result.action, "CLARIFY")


if __name__ == "__main__":
    unittest.main()

"""Local checks plus opt-in real API cases; never fabricate agent decisions."""
import os
import unittest
from unittest.mock import patch

import httpx

from decision import DecisionInput, select_action
from main import app

COMPLETE = {
    'assignment': 'Write a paragraph supporting your position on classroom AI with two reasons.',
    'rubric': 'Clear position; two relevant reasons with explanations; logical organization.',
    'student_response': 'AI can help explain difficult concepts. It can also offer practice questions.',
}
AMBIGUOUS = {
    **COMPLETE,
    'rubric': 'Include at least two supporting examples. Include no supporting examples.',
}


class LocalDecisionTests(unittest.IsolatedAsyncioTestCase):
    async def request(self, payload):
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            return await client.post('/api/decision', json=payload)

    async def test_missing_rubric_does_not_construct_client(self):
        with patch('decision.AsyncOpenAI', side_effect=AssertionError('Must not call LLM')):
            response = await self.request({**COMPLETE, 'rubric': '   '})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()['missing_fields'], ['Grading Rubric'])
        self.assertEqual(response.json()['status'], 'validation_error')
        self.assertIsNone(response.json()['action'])

    async def test_all_missing_fields_named(self):
        with patch('decision.AsyncOpenAI', side_effect=AssertionError('Must not call LLM')):
            response = await self.request({})
        self.assertEqual(response.json()['missing_fields'],
                         ['Assignment Instructions', 'Grading Rubric', 'Student Response'])

    async def test_complete_and_ambiguous_without_configuration(self):
        # Both must require a real model; neither receives a hardcoded decision.
        with patch.dict(os.environ, {}, clear=True), patch('decision.AsyncOpenAI', side_effect=AssertionError('No key')):
            for case in [COMPLETE, AMBIGUOUS]:
                response = await self.request(case)
                self.assertEqual(response.status_code, 503)
                self.assertEqual(response.json()['status'], 'configuration_error')
                self.assertIsNone(response.json()['action'])

    async def test_api_failure_is_not_success_and_does_not_leak(self):
        # Simulate only a transport/client failure, never a model decision.
        with patch.dict(os.environ, {'FEEDBACK_API_KEY': 'test-only-not-a-credential'}), patch(
            'decision.AsyncOpenAI', side_effect=RuntimeError('private provider details')
        ):
            response = await self.request(COMPLETE)
        self.assertEqual(response.status_code, 502)
        self.assertEqual(response.json()['status'], 'api_error')
        self.assertIsNone(response.json()['action'])
        self.assertNotIn('private provider details', response.text)

    async def test_invalid_payload_does_not_echo_input(self):
        response = await self.request({**COMPLETE, 'rubric': {'private': 'private student content'}})
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()['status'], 'validation_error')
        self.assertNotIn('private student content', response.text)


@unittest.skipUnless(os.environ.get('RUN_LIVE_API_TESTS') == '1' and os.environ.get('FEEDBACK_API_KEY'),
                     'Requires RUN_LIVE_API_TESTS=1 and a real FEEDBACK_API_KEY; calls incur API usage')
class LiveDecisionTests(unittest.IsolatedAsyncioTestCase):
    async def test_complete_case_analyze(self):
        code, result = await select_action(DecisionInput(**COMPLETE))
        self.assertEqual(code, 200)
        self.assertEqual(result.status, 'decision_complete')
        self.assertEqual(result.action, 'ANALYZE')
        self.assertIsNone(result.clarification_question)

    async def test_ambiguous_rubric_clarify(self):
        code, result = await select_action(DecisionInput(**AMBIGUOUS))
        self.assertEqual(code, 200)
        self.assertEqual(result.status, 'decision_complete')
        self.assertEqual(result.action, 'CLARIFY')
        self.assertTrue(result.clarification_question.strip())


if __name__ == '__main__':
    unittest.main()

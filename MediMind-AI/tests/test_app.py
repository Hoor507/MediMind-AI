import json
import unittest
from unittest.mock import patch

import app as medi_app

class MediMindTests(unittest.TestCase):
    def setUp(self):
        medi_app.app.config.update(TESTING=True, SECRET_KEY="test-secret")
        self.client = medi_app.app.test_client()

    def test_empty_symptoms_rejected(self):
        response = self.client.post("/api/analyze", json={"symptoms": "  "})
        self.assertEqual(response.status_code, 400)

    def test_non_json_rejected(self):
        response = self.client.post("/api/analyze", data="not json", content_type="text/plain")
        self.assertEqual(response.status_code, 400)

    def test_emergency_patterns(self):
        flags = medi_app.emergency_flags("I have severe difficulty breathing")
        self.assertTrue(flags)
        data = {
            "status": "assessment", "emergency_level": "Level 4", "urgency_title": "Self-care",
            "summary": "Breathing issue", "possible_conditions": [], "warning_signs": [],
            "first_aid": [], "care_recommendation": "Rest", "follow_up_questions": ["How long?"],
            "disclaimer": "Not a diagnosis"
        }
        result = medi_app.safe_emergency_override(data, flags)
        self.assertEqual(result["emergency_level"], "Level 1")
        self.assertEqual(result["follow_up_questions"], [])
        self.assertIn("emergency", result["care_recommendation"].lower())

    def test_invalid_level_rejected(self):
        data = {
            "status": "assessment", "emergency_level": "Level 9", "urgency_title": "x",
            "summary": "x", "possible_conditions": [], "warning_signs": [],
            "first_aid": [], "care_recommendation": "x", "follow_up_questions": [],
            "disclaimer": "x"
        }
        with self.assertRaises(ValueError):
            medi_app.validate_assessment(data)

    def test_missing_api_key_gives_error_and_emergency_override(self):
        with patch.dict("os.environ", {"GROQ_API_KEY": ""}, clear=False):
            response = self.client.post("/api/analyze", json={"symptoms": "I have severe difficulty breathing"})
        self.assertEqual(response.status_code, 503)
        self.assertIn("emergency", response.get_json())

if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import sys
import unittest
from copy import deepcopy
from pathlib import Path


EVAL_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(EVAL_DIR))

from run_capability_contract_tests import (  # noqa: E402
    FIXTURE_PATH,
    evaluate_candidates,
    validate_assessment_provenance,
    validate_fixture_corpus,
)


class CapabilityContractEvaluatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.suite = json.loads(
            FIXTURE_PATH.read_text(encoding="utf-8")
        )
        cls.fixtures = cls.suite["fixtures"]
        cls.first = cls.fixtures[0]

    def compliant_observation(self, fixture: dict) -> dict:
        return {
            "fixture_id": fixture["fixture_id"],
            "output_artifact_type": fixture[
                "expected_output_artifact"
            ],
            "route": fixture["expected_route"],
            "decision": fixture["expected_decision"],
            "observed_behaviors": fixture["required_behaviors"],
            "observed_forbidden_behaviors": [],
        }

    def test_fixture_corpus_has_39_valid_cases(self) -> None:
        self.assertEqual(len(self.fixtures), 39)
        self.assertEqual(
            validate_fixture_corpus(self.suite), []
        )

    def test_compliant_observation_passes(self) -> None:
        candidate = self.compliant_observation(self.first)
        errors = evaluate_candidates(
            self.fixtures,
            {self.first["fixture_id"]: candidate},
            require_all=False,
        )
        self.assertEqual(errors, [])

    def test_missing_required_behavior_is_detected(self) -> None:
        candidate = self.compliant_observation(self.first)
        candidate["observed_behaviors"] = candidate[
            "observed_behaviors"
        ][1:]
        errors = evaluate_candidates(
            self.fixtures,
            {self.first["fixture_id"]: candidate},
            require_all=False,
        )
        self.assertTrue(
            any("missing behaviors" in error for error in errors)
        )

    def test_forbidden_behavior_is_detected(self) -> None:
        candidate = self.compliant_observation(self.first)
        candidate["observed_forbidden_behaviors"] = [
            self.first["forbidden_behaviors"][0]
        ]
        errors = evaluate_candidates(
            self.fixtures,
            {self.first["fixture_id"]: candidate},
            require_all=False,
        )
        self.assertTrue(
            any(
                "forbidden behaviors observed" in error
                for error in errors
            )
        )

    def test_wrong_route_and_decision_are_detected(self) -> None:
        candidate = self.compliant_observation(self.first)
        candidate["route"] = "WRONG-ROUTE"
        candidate["decision"] = "WRONG-DECISION"
        errors = evaluate_candidates(
            self.fixtures,
            {self.first["fixture_id"]: candidate},
            require_all=False,
        )
        self.assertTrue(any("route=" in error for error in errors))
        self.assertTrue(
            any("decision=" in error for error in errors)
        )

    def test_require_all_rejects_partial_run(self) -> None:
        candidate = self.compliant_observation(self.first)
        errors = evaluate_candidates(
            self.fixtures,
            {self.first["fixture_id"]: candidate},
            require_all=True,
        )
        self.assertTrue(
            any("missing fixtures" in error for error in errors)
        )

    def test_unknown_fixture_is_detected(self) -> None:
        candidate = deepcopy(
            self.compliant_observation(self.first)
        )
        candidate["fixture_id"] = "UNKNOWN-001"
        errors = evaluate_candidates(
            self.fixtures,
            {"UNKNOWN-001": candidate},
            require_all=False,
        )
        self.assertTrue(
            any("unknown fixtures" in error for error in errors)
        )

    def test_independent_assessment_provenance_passes(self) -> None:
        assessment = self.compliant_observation(self.first)
        assessment.update(
            {
                "assessor_id": "HUMAN-REVIEWER-001",
                "assessor_type": "HUMAN",
                "raw_output_ref": (
                    "RUN-TEST-001/raw-outputs.jsonl#"
                    + self.first["fixture_id"]
                ),
                "evidence_notes": [
                    "观察结论可定位到冻结的原始回答。"
                ],
            }
        )
        self.assertEqual(
            validate_assessment_provenance(
                {self.first["fixture_id"]: assessment}
            ),
            [],
        )

    def test_missing_assessment_provenance_is_detected(
        self,
    ) -> None:
        assessment = self.compliant_observation(self.first)
        errors = validate_assessment_provenance(
            {self.first["fixture_id"]: assessment}
        )
        self.assertTrue(
            any("missing provenance" in error for error in errors)
        )

    def test_self_assessment_type_is_not_accepted(self) -> None:
        assessment = self.compliant_observation(self.first)
        assessment.update(
            {
                "assessor_id": "SUBJECT-CAP01-001",
                "assessor_type": "SELF",
                "raw_output_ref": (
                    "RUN-TEST-001/raw-outputs.jsonl#"
                    + self.first["fixture_id"]
                ),
                "evidence_notes": ["待测 Agent 自评。"],
            }
        )
        errors = validate_assessment_provenance(
            {self.first["fixture_id"]: assessment}
        )
        self.assertTrue(
            any(
                "unsupported assessor_type" in error
                for error in errors
            )
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)

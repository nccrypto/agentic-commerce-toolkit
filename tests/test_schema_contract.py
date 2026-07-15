import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

from agentic_commerce.action_control import action_digest, evaluate_action_control


ROOT = Path(__file__).parents[1]
INSPECTOR_SCHEMA = ROOT / "schemas" / "inspector-envelope-v1.schema.json"
INSPECTOR_EXAMPLE = ROOT / "examples" / "reppo-inspector" / "datanets-envelope-v1.example.json"
SOURCE_MANIFEST_SCHEMA = ROOT / "schemas" / "source-manifest-v1.schema.json"
SOURCE_MANIFEST_EXAMPLE = ROOT / "examples" / "source-manifest" / "reppo-public-api-manifest-v1.example.json"
AGENT_JOB_RESULT_SCHEMA = ROOT / "schemas" / "agent-job-result-v1.schema.json"
AGENT_JOB_RESULT_EXAMPLE = ROOT / "examples" / "agent-job-result" / "reppo-inspection-result-v1.example.json"
ACTION_CONTROL_SCHEMA = ROOT / "schemas" / "action-control-v1.schema.json"
ACTION_CONTROL_DRY_RUN_EXAMPLE = ROOT / "examples" / "action-control" / "dry-run-v1.example.json"
ACTION_CONTROL_AUTHORIZED_EXAMPLE = ROOT / "examples" / "action-control" / "authorized-action-v1.example.json"
ACP_EVIDENCE_REQUEST_SCHEMA = ROOT / "schemas" / "acp-evidence-request-v1.schema.json"
ACP_EVIDENCE_REQUEST_EXAMPLE = ROOT / "examples" / "virtuals-acp-evidence" / "request-v1.example.json"
ACP_EVIDENCE_RECEIPT_EXAMPLE = ROOT / "examples" / "virtuals-acp-evidence" / "receipt-v1.example.json"
ACP_EVIDENCE_OFFERING_EXAMPLE = ROOT / "examples" / "virtuals-acp-evidence" / "offering-v1.example.json"


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def validation_errors(schema_path, example_path):
    validator = Draft202012Validator(load_json(schema_path), format_checker=FormatChecker())
    example = load_json(example_path)
    return sorted(validator.iter_errors(example), key=lambda error: list(error.path))


class SchemaContractTests(unittest.TestCase):
    def assert_conforms(self, schema_path, example_path):
        errors = validation_errors(schema_path, example_path)
        self.assertEqual([], [error.message for error in errors])

    def test_reppo_example_conforms_to_inspector_envelope_v1(self):
        self.assert_conforms(INSPECTOR_SCHEMA, INSPECTOR_EXAMPLE)

    def test_source_manifest_example_conforms_to_source_manifest_v1(self):
        self.assert_conforms(SOURCE_MANIFEST_SCHEMA, SOURCE_MANIFEST_EXAMPLE)

    def test_agent_job_result_example_conforms_to_agent_job_result_v1(self):
        self.assert_conforms(AGENT_JOB_RESULT_SCHEMA, AGENT_JOB_RESULT_EXAMPLE)

    def test_action_control_examples_conform_to_action_control_v1(self):
        self.assert_conforms(ACTION_CONTROL_SCHEMA, ACTION_CONTROL_DRY_RUN_EXAMPLE)
        self.assert_conforms(ACTION_CONTROL_SCHEMA, ACTION_CONTROL_AUTHORIZED_EXAMPLE)

    def test_acp_evidence_examples_conform_to_public_contracts(self):
        self.assert_conforms(ACP_EVIDENCE_REQUEST_SCHEMA, ACP_EVIDENCE_REQUEST_EXAMPLE)
        self.assert_conforms(AGENT_JOB_RESULT_SCHEMA, ACP_EVIDENCE_RECEIPT_EXAMPLE)

    def test_acp_offering_example_is_bounded_and_nonexecuting(self):
        offering = load_json(ACP_EVIDENCE_OFFERING_EXAMPLE)

        self.assertEqual(offering["name"], "Evidence Verify")
        self.assertEqual(offering["priceType"], "fixed")
        self.assertGreater(offering["priceValue"], 0)
        self.assertGreaterEqual(offering["slaMinutes"], 5)
        self.assertFalse(offering["requiredFunds"])
        self.assertTrue(offering["isHidden"])
        self.assertFalse(offering["requirements"].get("additionalProperties", True))

    def test_action_control_schema_enforces_default_deny(self):
        schema = load_json(ACTION_CONTROL_SCHEMA)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())

        dry_run = load_json(ACTION_CONTROL_DRY_RUN_EXAMPLE)
        dry_run["decision"]["mayExecute"] = True
        self.assertFalse(validator.is_valid(dry_run))

        authorized = load_json(ACTION_CONTROL_AUTHORIZED_EXAMPLE)
        authorized["approval"] = None
        self.assertFalse(validator.is_valid(authorized))

        private_shaped = load_json(ACTION_CONTROL_DRY_RUN_EXAMPLE)
        private_shaped["request"]["localPath"] = "not allowed"
        self.assertFalse(validator.is_valid(private_shaped))

    def test_action_control_evaluator_denials_conform_to_schema(self):
        schema = load_json(ACTION_CONTROL_SCHEMA)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        request = {
            "actionId": "example:catalog-update:2026-07-14",
            "actionType": "example.catalog-update",
            "mode": "execute",
            "summary": "Prepare a synthetic update to a public example catalog.",
            "parameters": [{"name": "itemCount", "value": 2}],
        }
        approval = {
            "approvalId": "example:approval:catalog-update:2026-07-14",
            "actionId": request["actionId"],
            "actionType": request["actionType"],
            "actionDigest": action_digest(request),
            "decision": "approved",
            "issuedAt": "2026-07-14T12:00:00Z",
            "expiresAt": "2026-07-14T12:30:00Z",
            "issuerType": "human",
        }
        expired = evaluate_action_control(
            "example:control:expired:2026-07-14",
            request,
            "2026-07-14T13:00:00Z",
            approval,
        )
        invalid_approval = dict(approval)
        invalid_approval["accountId"] = "not allowed"
        invalid = evaluate_action_control(
            "example:control:invalid:2026-07-14",
            request,
            "2026-07-14T13:00:00Z",
            invalid_approval,
        )

        self.assertTrue(validator.is_valid(expired))
        self.assertTrue(validator.is_valid(invalid))


    def test_agent_job_operational_fields_are_backward_compatible_and_optional(self):
        schema = load_json(AGENT_JOB_RESULT_SCHEMA)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        job_result = load_json(AGENT_JOB_RESULT_EXAMPLE)
        job_result.pop("cost")
        job_result.pop("timeout")
        job_result.pop("freshness")

        self.assertTrue(validator.is_valid(job_result))

    def test_agent_job_operational_fields_are_bounded(self):
        schema = load_json(AGENT_JOB_RESULT_SCHEMA)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())

        invalid_cost = load_json(AGENT_JOB_RESULT_EXAMPLE)
        invalid_cost["cost"]["amount"] = "-1"
        self.assertFalse(validator.is_valid(invalid_cost))

        private_cost = load_json(AGENT_JOB_RESULT_EXAMPLE)
        private_cost["cost"]["accountId"] = "not allowed"
        self.assertFalse(validator.is_valid(private_cost))

        invalid_timeout = load_json(AGENT_JOB_RESULT_EXAMPLE)
        invalid_timeout["timeout"]["limitMs"] = 0
        self.assertFalse(validator.is_valid(invalid_timeout))

        incomplete_freshness = load_json(AGENT_JOB_RESULT_EXAMPLE)
        incomplete_freshness["freshness"].pop("dataAsOf")
        self.assertFalse(validator.is_valid(incomplete_freshness))

    def test_source_manifest_requires_public_source_records(self):
        schema = load_json(SOURCE_MANIFEST_SCHEMA)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        manifest = load_json(SOURCE_MANIFEST_EXAMPLE)
        manifest["sources"] = []

        errors = sorted(validator.iter_errors(manifest), key=lambda error: list(error.path))

        self.assertIn("[] should be non-empty", [error.message for error in errors])

    def test_source_manifest_rejects_unbounded_extra_fields(self):
        schema = load_json(SOURCE_MANIFEST_SCHEMA)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        manifest = load_json(SOURCE_MANIFEST_EXAMPLE)
        manifest["privateRuntimeState"] = "not allowed"
        manifest["sources"][0]["localPath"] = "runtime-cache"

        messages = [error.message for error in validator.iter_errors(manifest)]

        self.assertTrue(any("privateRuntimeState" in message for message in messages))
        self.assertTrue(any("localPath" in message for message in messages))

    def test_agent_job_result_rejects_private_or_unbounded_fields(self):
        schema = load_json(AGENT_JOB_RESULT_SCHEMA)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        job_result = load_json(AGENT_JOB_RESULT_EXAMPLE)
        job_result["privateRuntimeState"] = "not allowed"
        job_result["request"]["localPath"] = "runtime-cache"
        job_result["request"]["inputs"][0]["value"] = ["item"] * 101

        errors = list(validator.iter_errors(job_result))
        messages = [error.message for error in errors]

        self.assertTrue(any("privateRuntimeState" in message for message in messages))
        self.assertTrue(any("localPath" in message for message in messages))
        self.assertTrue(
            any(
                list(error.absolute_path) == ["request", "inputs", 0, "value"]
                for error in errors
            )
        )

    def test_agent_job_result_rejects_excessive_result_nesting(self):
        schema = load_json(AGENT_JOB_RESULT_SCHEMA)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        job_result = load_json(AGENT_JOB_RESULT_EXAMPLE)
        job_result["result"]["data"] = {
            "one": {"two": {"three": {"four": {"five": "too deep"}}}}
        }

        self.assertFalse(validator.is_valid(job_result))

    def test_failed_agent_job_requires_null_result_and_an_error(self):
        schema = load_json(AGENT_JOB_RESULT_SCHEMA)
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        job_result = load_json(AGENT_JOB_RESULT_EXAMPLE)
        job_result["status"] = "failed"
        job_result["errors"] = []

        messages = [error.message for error in validator.iter_errors(job_result)]

        self.assertTrue(any("is not of type 'null'" in message for message in messages))
        self.assertTrue(any("should be non-empty" in message for message in messages))


if __name__ == "__main__":
    unittest.main()

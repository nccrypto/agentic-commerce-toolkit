import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).parents[1]
INSPECTOR_SCHEMA = ROOT / "schemas" / "inspector-envelope-v1.schema.json"
INSPECTOR_EXAMPLE = ROOT / "examples" / "reppo-inspector" / "datanets-envelope-v1.example.json"
SOURCE_MANIFEST_SCHEMA = ROOT / "schemas" / "source-manifest-v1.schema.json"
SOURCE_MANIFEST_EXAMPLE = ROOT / "examples" / "source-manifest" / "reppo-public-api-manifest-v1.example.json"
AGENT_JOB_RESULT_SCHEMA = ROOT / "schemas" / "agent-job-result-v1.schema.json"
AGENT_JOB_RESULT_EXAMPLE = ROOT / "examples" / "agent-job-result" / "reppo-inspection-result-v1.example.json"


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

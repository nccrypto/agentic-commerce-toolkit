import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker


ROOT = Path(__file__).parents[1]
SCHEMA = ROOT / "schemas" / "inspector-envelope-v1.schema.json"
EXAMPLE = ROOT / "examples" / "reppo-inspector" / "datanets-envelope-v1.example.json"


class SchemaContractTests(unittest.TestCase):
    def test_reppo_example_conforms_to_inspector_envelope_v1(self):
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        example = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        validator = Draft202012Validator(schema, format_checker=FormatChecker())

        errors = sorted(validator.iter_errors(example), key=lambda error: list(error.path))

        self.assertEqual([], [error.message for error in errors])


if __name__ == "__main__":
    unittest.main()

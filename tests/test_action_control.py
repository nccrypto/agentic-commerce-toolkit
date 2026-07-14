import unittest

from agentic_commerce.action_control import action_digest, evaluate_action_control


EVALUATED_AT = "2026-07-14T13:00:00Z"


def action_request(mode="execute"):
    return {
        "actionId": "example:catalog-update:2026-07-14",
        "actionType": "example.catalog-update",
        "mode": mode,
        "summary": "Prepare a synthetic update to a public example catalog.",
        "parameters": [
            {"name": "catalog", "value": "synthetic-public-examples"},
            {"name": "itemCount", "value": 2},
        ],
    }


def matching_approval(request=None, **overrides):
    request = request or action_request()
    approval = {
        "approvalId": "example:approval:catalog-update:2026-07-14",
        "actionId": request["actionId"],
        "actionType": request["actionType"],
        "actionDigest": action_digest(request),
        "decision": "approved",
        "issuedAt": "2026-07-14T12:55:00Z",
        "expiresAt": "2026-07-14T13:30:00Z",
        "issuerType": "human",
    }
    approval.update(overrides)
    return approval


class ActionControlTests(unittest.TestCase):
    def test_digest_is_stable_across_mode_but_changes_with_scope(self):
        dry_run = action_request("dry-run")
        execute = action_request("execute")
        changed = action_request("execute")
        changed["parameters"][1]["value"] = 3

        self.assertEqual(action_digest(dry_run), action_digest(execute))
        self.assertNotEqual(action_digest(execute), action_digest(changed))

    def test_dry_run_never_authorizes_execution(self):
        record = evaluate_action_control(
            "example:control:dry-run:2026-07-14",
            action_request("dry-run"),
            EVALUATED_AT,
        )

        self.assertIsNone(record["approval"])
        self.assertEqual("dry-run", record["decision"]["status"])
        self.assertEqual("DRY_RUN_ONLY", record["decision"]["reasonCode"])
        self.assertFalse(record["decision"]["mayExecute"])

    def test_dry_run_refuses_to_consume_approval(self):
        request = action_request("dry-run")

        with self.assertRaisesRegex(ValueError, "must not include an approval"):
            evaluate_action_control(
                "example:control:dry-run:2026-07-14",
                request,
                EVALUATED_AT,
                matching_approval(request),
            )

    def test_execute_without_approval_is_default_deny(self):
        record = evaluate_action_control(
            "example:control:missing-approval:2026-07-14",
            action_request(),
            EVALUATED_AT,
        )

        self.assertEqual("rejected", record["decision"]["status"])
        self.assertEqual("APPROVAL_REQUIRED", record["decision"]["reasonCode"])
        self.assertFalse(record["decision"]["mayExecute"])

    def test_matching_unexpired_approval_authorizes_but_does_not_execute(self):
        request = action_request()
        record = evaluate_action_control(
            "example:control:authorized:2026-07-14",
            request,
            EVALUATED_AT,
            matching_approval(request),
        )

        self.assertEqual("authorized", record["decision"]["status"])
        self.assertEqual("APPROVED", record["decision"]["reasonCode"])
        self.assertTrue(record["decision"]["mayExecute"])
        self.assertNotIn("executed", record["decision"])

    def test_expired_approval_is_rejected(self):
        request = action_request()
        record = evaluate_action_control(
            "example:control:expired:2026-07-14",
            request,
            EVALUATED_AT,
            matching_approval(request, expiresAt="2026-07-14T12:59:59Z"),
        )

        self.assertEqual("APPROVAL_EXPIRED", record["decision"]["reasonCode"])
        self.assertFalse(record["decision"]["mayExecute"])

    def test_mismatched_approval_scope_is_rejected(self):
        request = action_request()
        record = evaluate_action_control(
            "example:control:mismatch:2026-07-14",
            request,
            EVALUATED_AT,
            matching_approval(request, actionDigest="0" * 64),
        )

        self.assertEqual("APPROVAL_SCOPE_MISMATCH", record["decision"]["reasonCode"])
        self.assertFalse(record["decision"]["mayExecute"])

    def test_explicit_rejection_is_enforced(self):
        request = action_request()
        record = evaluate_action_control(
            "example:control:rejected:2026-07-14",
            request,
            EVALUATED_AT,
            matching_approval(request, decision="rejected"),
        )

        self.assertEqual("APPROVAL_REJECTED", record["decision"]["reasonCode"])
        self.assertFalse(record["decision"]["mayExecute"])

    def test_invalid_approval_is_sanitized_and_denied(self):
        request = action_request()
        approval = matching_approval(request)
        approval["accountId"] = "not allowed"
        record = evaluate_action_control(
            "example:control:invalid:2026-07-14",
            request,
            EVALUATED_AT,
            approval,
        )

        self.assertIsNone(record["approval"])
        self.assertEqual("INVALID_APPROVAL", record["decision"]["reasonCode"])
        self.assertFalse(record["decision"]["mayExecute"])

    def test_future_or_reversed_approval_interval_is_invalid(self):
        request = action_request()
        future = evaluate_action_control(
            "example:control:future:2026-07-14",
            request,
            EVALUATED_AT,
            matching_approval(request, issuedAt="2026-07-14T13:01:00Z"),
        )
        reversed_interval = evaluate_action_control(
            "example:control:reversed:2026-07-14",
            request,
            EVALUATED_AT,
            matching_approval(request, expiresAt="2026-07-14T12:54:00Z"),
        )

        self.assertEqual("INVALID_APPROVAL", future["decision"]["reasonCode"])
        self.assertEqual("INVALID_APPROVAL", reversed_interval["decision"]["reasonCode"])

    def test_private_shaped_unbounded_or_ambiguous_parameters_are_rejected(self):
        private_request = action_request()
        private_request["localPath"] = "not allowed"
        non_finite_request = action_request()
        non_finite_request["parameters"][1]["value"] = float("nan")
        huge_number_request = action_request()
        huge_number_request["parameters"][1]["value"] = 10**19
        duplicate_request = action_request()
        duplicate_request["parameters"].append(
            {"name": "itemCount", "value": 3}
        )

        for invalid_request in (
            private_request,
            non_finite_request,
            huge_number_request,
            duplicate_request,
        ):
            with self.subTest(invalid_request=invalid_request):
                with self.assertRaises(ValueError):
                    action_digest(invalid_request)

    def test_evaluation_timestamp_must_be_strict_rfc3339(self):
        with self.assertRaisesRegex(ValueError, "RFC 3339"):
            evaluate_action_control(
                "example:control:bad-time:2026-07-14",
                action_request("dry-run"),
                "2026-07-14 13:00:00+00:00",
            )


if __name__ == "__main__":
    unittest.main()

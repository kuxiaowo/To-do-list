import hashlib
import hmac
import json
import unittest
from unittest import mock
from pathlib import Path

import database_adapter


class _Response:
    def __init__(self, payload):
        self.payload = json.dumps(payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return self.payload


class D1GatewayContractTests(unittest.TestCase):
    def setUp(self):
        self.secret = "todo-test-secret"
        self.connection = database_adapter.D1GatewayConnection(
            "https://db.example.test/", self.secret, clock=lambda: 1700000000
        )

    def test_single_request_signature_headers_and_result_metadata(self):
        response = _Response({
            "requestId": "ignored",
            "results": [{"rows": [{"id": 7, "title": "demo"}],
                         "meta": {"changes": 1, "last_row_id": 7}}],
        })
        with mock.patch("database_adapter.uuid.uuid4", return_value="req-123"):
            with mock.patch("database_adapter.urllib.request.urlopen", return_value=response) as opened:
                cursor = self.connection.execute("SELECT id, title FROM tasks WHERE id = ?", (7,))

        request = opened.call_args.args[0]
        body = request.data
        payload = json.loads(body)
        self.assertEqual(request.full_url, "https://db.example.test/internal/db")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(payload["requestId"], "req-123")
        self.assertEqual(payload["timestamp"], 1700000000)
        self.assertEqual(payload["mode"], "single")
        self.assertEqual(payload["statements"], [{"sql": "SELECT id, title FROM tasks WHERE id = ?", "params": [7]}])
        digest = hashlib.sha256(body).hexdigest()
        canonical = f"v1\nPOST\n/internal/db\nreq-123\n1700000000\n{digest}".encode()
        expected = hmac.new(self.secret.encode(), canonical, hashlib.sha256).hexdigest()
        self.assertEqual(request.headers["X-db-request-id"], "req-123")
        self.assertEqual(request.headers["X-db-timestamp"], "1700000000")
        self.assertEqual(request.headers["X-db-signature"], expected)
        self.assertEqual(cursor.fetchone(), {"id": 7, "title": "demo"})
        self.assertEqual(cursor.rowcount, 1)
        self.assertEqual(cursor.lastrowid, 7)

    def test_batch_maps_each_result_and_preserves_parameter_binding(self):
        response = _Response({"results": [
            {"rows": [], "meta": {"changes": 1, "last_row_id": 8}},
            {"rows": [{"changes": 1}], "meta": {"changes": 0, "last_row_id": None}},
        ]})
        with mock.patch("database_adapter.uuid.uuid4", return_value="batch-1"):
            with mock.patch("database_adapter.urllib.request.urlopen", return_value=response) as opened:
                cursors = self.connection.batch([
                    ("INSERT INTO tasks(title) VALUES (?)", ("a",)),
                    {"sql": "SELECT changes()", "params": []},
                ])
        payload = json.loads(opened.call_args.args[0].data)
        self.assertEqual(payload["mode"], "batch")
        self.assertEqual(payload["statements"][0]["params"], ["a"])
        self.assertEqual(payload["statements"][1], {"sql": "SELECT changes()", "params": []})
        self.assertEqual(cursors[0].rowcount, 1)
        self.assertEqual(cursors[0].lastrowid, 8)
        self.assertEqual(cursors[1].fetchall(), [{"changes": 1}])

    def test_gateway_errors_and_malformed_results_are_mapped(self):
        with mock.patch(
            "database_adapter.urllib.request.urlopen",
            return_value=_Response({"error": "invalid signature"}),
        ):
            with self.assertRaisesRegex(database_adapter.D1Error, "invalid signature"):
                self.connection.execute("SELECT 1")

        with mock.patch(
            "database_adapter.urllib.request.urlopen",
            return_value=_Response({"results": {}}),
        ):
            with self.assertRaisesRegex(database_adapter.D1Error, "results must be a list"):
                self.connection.execute("SELECT 1")

    def test_transaction_control_fails_closed_without_reaching_gateway(self):
        with mock.patch("database_adapter.urllib.request.urlopen") as opened:
            with self.assertRaisesRegex(database_adapter.D1Error, "use batch"):
                self.connection.execute("BEGIN IMMEDIATE")
        opened.assert_not_called()

    def test_ai_quota_write_uses_conditional_insert(self):
        source = Path(__file__).resolve().parents[1].joinpath("server.py").read_text(encoding="utf-8")
        function = source[source.index("def record_ai_usage("):source.index("\ndef ai_token_limit_status", source.index("def record_ai_usage("))]
        self.assertIn("INSERT INTO ai_usage_logs", function)
        self.assertIn("SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ?", function)
        self.assertIn("json_extract", function)
        self.assertIn("normalized['_recorded']", function)

    def test_d1_schedule_create_computes_sort_order_inside_batch_insert(self):
        source = Path(__file__).resolve().parents[1].joinpath("server.py").read_text(encoding="utf-8")
        start = source.index("    def handle_create_schedule_item(")
        end = source.index("\n    def handle_update_schedule_item(", start)
        function = source[start:end]
        self.assertIn("if not is_d1:\n                conn.execute('BEGIN IMMEDIATE')", function)
        self.assertIn("COALESCE(?, (SELECT COALESCE(MAX(sort_order), 0) + 1024", function)
        self.assertIn("results = conn.batch([", function)
        self.assertIn("operation_log_statement", function)

    def test_d1_habit_mutations_batch_parent_instances_and_log(self):
        source = Path(__file__).resolve().parents[1].joinpath("server.py").read_text(encoding="utf-8")
        create_start = source.index("    def handle_create_habit(")
        update_start = source.index("\n    def handle_update_habit(", create_start)
        delete_start = source.index("\n    def handle_delete_habit(", update_start)
        create_function = source[create_start:update_start]
        update_function = source[update_start:delete_start]
        self.assertIn("d1_habit_instance_statements", create_function)
        self.assertIn("results = conn.batch(statements)", create_function)
        self.assertIn("conn.execute('BEGIN IMMEDIATE')", create_function)
        self.assertIn("guard_updated_at=now", update_function)
        self.assertIn("results = conn.batch(statements)", update_function)
        self.assertIn("habit was modified concurrently", update_function)

    def test_d1_feedback_limit_is_enforced_by_conditional_insert(self):
        source = Path(__file__).resolve().parents[1].joinpath("server.py").read_text(encoding="utf-8")
        start = source.index("    def handle_create_feedback(")
        end = source.index("\n    def handle_delete_feedback(", start)
        function = source[start:end]
        self.assertIn("SELECT ?, ?, ?, '', NULL, 'pending', ?, ?", function)
        self.assertIn("status != 'replied') < ?", function)
        self.assertIn("results = conn.batch([", function)
        self.assertIn("if results[0].rowcount != 1", function)

    def test_d1_registration_and_login_group_related_writes(self):
        source = Path(__file__).resolve().parents[1].joinpath("server.py").read_text(encoding="utf-8")
        register_start = source.index("    def handle_auth_register(")
        login_start = source.index("\n    def handle_auth_login(", register_start)
        register = source[register_start:login_start]
        self.assertIn("results = conn.batch([", register)
        self.assertNotIn("INSERT INTO registration_attempt_logs", register)
        self.assertIn("operation_log_statement", register)
        self.assertNotIn("reserved = conn.execute", register)

        session_start = source.index("    def issue_session_response(")
        session = source[session_start:]
        self.assertIn("login_detail: dict | None = None", session)
        self.assertIn("conn.batch([", session)
        self.assertIn("'auth.login'", session)

    def test_d1_admin_user_delete_is_one_batch(self):
        source = Path(__file__).resolve().parents[1].joinpath("server.py").read_text(encoding="utf-8")
        start = source.index("    def handle_admin_delete_user(")
        end = source.index("\n    def handle_admin_user_tasks(", start)
        function = source[start:end]
        self.assertIn("statements = [{'sql': sql, 'params': list(params)}", function)
        self.assertIn("results = conn.batch(statements)", function)
        self.assertIn("if results[-2].rowcount != 1", function)


if __name__ == "__main__":
    unittest.main()

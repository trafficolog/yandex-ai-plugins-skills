from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import textwrap
import unittest


ROOT = Path(__file__).resolve().parents[1]
PROTOCOL_PATH = ROOT / "scripts/eval_benchmark/protocol.py"


class EvalBenchmarkProtocolTests(unittest.TestCase):
    def protocol(self):
        self.assertTrue(PROTOCOL_PATH.is_file(), "eval benchmark protocol module must exist")
        from scripts.eval_benchmark import protocol

        return protocol

    def request(self, invocation_id: str = "inv-1") -> dict[str, object]:
        protocol = self.protocol()
        return {
            "schema": protocol.REQUEST_SCHEMA,
            "invocation_id": invocation_id,
            "kind": "subject",
            "payload": {"prompt": "audit"},
        }

    def write_adapter(self, source: str) -> list[str]:
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "adapter.py"
        path.write_text(textwrap.dedent(source), encoding="utf-8")
        return [sys.executable, str(path)]

    def valid_adapter(self, *, model_name: str = "subject-model") -> list[str]:
        return self.write_adapter(
            f"""
            import json, sys
            req = json.loads(sys.stdin.readline())
            json.dump({{
                "schema": "yandex-ai-eval-adapter-response/v1",
                "invocation_id": req["invocation_id"],
                "adapter_id": "test-adapter",
                "adapter_version": "1.0",
                "runtime": {{"name": "python-test", "version": "3"}},
                "model": {{"name": "{model_name}", "version": "2026-09"}},
                "output": {{"text": "done", "route": "router"}}
            }}, sys.stdout)
            sys.stdout.write("\\n")
            """
        )

    def test_valid_roundtrip_and_model_identity(self):
        protocol = self.protocol()
        response = protocol.invoke_adapter(self.valid_adapter(), self.request())
        self.assertEqual(response["invocation_id"], "inv-1")
        self.assertEqual(
            protocol.model_identity(response),
            ("python-test", "3", "subject-model", "2026-09"),
        )

    def test_invocation_id_must_match_exactly(self):
        protocol = self.protocol()
        argv = self.write_adapter(
            """
            import json, sys
            json.loads(sys.stdin.readline())
            print(json.dumps({
                "schema": "yandex-ai-eval-adapter-response/v1",
                "invocation_id": "wrong",
                "adapter_id": "a", "adapter_version": "1",
                "runtime": {"name": "r", "version": "1"},
                "model": {"name": "m", "version": "1"},
                "output": {}
            }))
            """
        )
        with self.assertRaisesRegex(ValueError, "invocation_id"):
            protocol.invoke_adapter(argv, self.request())

    def test_multiple_response_lines_are_rejected(self):
        protocol = self.protocol()
        argv = self.write_adapter(
            """
            import json, sys
            req = json.loads(sys.stdin.readline())
            response = {"schema":"yandex-ai-eval-adapter-response/v1","invocation_id":req["invocation_id"],"adapter_id":"a","adapter_version":"1","runtime":{"name":"r","version":"1"},"model":{"name":"m","version":"1"},"output":{}}
            print(json.dumps(response))
            print(json.dumps(response))
            """
        )
        with self.assertRaisesRegex(ValueError, "one JSON"):
            protocol.invoke_adapter(argv, self.request())

    def test_nonzero_exit_fails_closed(self):
        protocol = self.protocol()
        argv = self.write_adapter("import sys; sys.exit(7)")
        with self.assertRaisesRegex(RuntimeError, "exit"):
            protocol.invoke_adapter(argv, self.request())

    def test_timeout_fails_closed(self):
        protocol = self.protocol()
        argv = self.write_adapter("import time; time.sleep(1)")
        with self.assertRaisesRegex(TimeoutError, "timeout"):
            protocol.invoke_adapter(argv, self.request(), timeout_seconds=0.01)

    def test_output_size_limits_are_enforced_before_decode(self):
        protocol = self.protocol()
        argv = self.write_adapter("import sys; sys.stdout.buffer.write(b'x' * 256)")
        with self.assertRaisesRegex(ValueError, "stdout"):
            protocol.invoke_adapter(argv, self.request(), max_stdout_bytes=32)

    def test_response_requires_complete_runtime_model_metadata(self):
        protocol = self.protocol()
        argv = self.write_adapter(
            """
            import json, sys
            req = json.loads(sys.stdin.readline())
            print(json.dumps({
                "schema":"yandex-ai-eval-adapter-response/v1",
                "invocation_id":req["invocation_id"],
                "adapter_id":"a","adapter_version":"1",
                "runtime":{"name":"r","version":"1"},
                "model":{"name":"m"},
                "output":{}
            }))
            """
        )
        with self.assertRaisesRegex(ValueError, "model.version"):
            protocol.invoke_adapter(argv, self.request())

    def test_canonical_json_rejects_non_finite_numbers(self):
        protocol = self.protocol()
        with self.assertRaises(ValueError):
            protocol.canonical_json_bytes({"x": float("nan")})


if __name__ == "__main__":
    unittest.main()

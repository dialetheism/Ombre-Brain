from __future__ import annotations

import ast
import asyncio
import builtins
import copy
import hmac
import json
import socket
import sqlite3
import subprocess
import sys
import threading
import unittest
import urllib.request
from contextlib import ExitStack
from pathlib import Path
from types import ModuleType, SimpleNamespace
from unittest import mock


SERVER_PATH = Path(__file__).resolve().parents[1] / "server.py"
FAKE_CONFIGURED_TOKEN = "unit-test-internal-hook-token"
FAKE_WRONG_TOKEN = "unit-test-wrong-token"


class _Request:
    def __init__(self, headers: dict[str, str] | None = None):
        self.headers = headers or {}


class _Response:
    def __init__(self, content=b"", status_code: int = 200):
        self.status_code = status_code
        if isinstance(content, bytes):
            self.body = content
        elif isinstance(content, str):
            self.body = content.encode("utf-8")
        else:
            self.body = json.dumps(content, separators=(",", ":")).encode("utf-8")


class _JSONResponse(_Response):
    pass


class _FailOnAccess:
    def __init__(self, label: str):
        self.label = label
        self.calls = 0

    def _fail(self):
        self.calls += 1
        raise AssertionError(f"forbidden side-effect boundary touched: {self.label}")

    def __call__(self, *args, **kwargs):
        self._fail()

    def __getattr__(self, name):
        self._fail()


def _find_function(tree: ast.Module, name: str):
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name:
            return node
    raise AssertionError(f"required function not found: {name}")


def _route_contract(handler_node: ast.AsyncFunctionDef) -> tuple[str, list[str]]:
    for decorator in handler_node.decorator_list:
        if not isinstance(decorator, ast.Call):
            continue
        target = decorator.func
        if not (
            isinstance(target, ast.Attribute)
            and isinstance(target.value, ast.Name)
            and target.value.id == "mcp"
            and target.attr == "custom_route"
        ):
            continue
        path = decorator.args[0].value if decorator.args else None
        methods: list[str] = []
        for keyword in decorator.keywords:
            if keyword.arg == "methods" and isinstance(keyword.value, (ast.List, ast.Tuple)):
                methods = [
                    item.value
                    for item in keyword.value.elts
                    if isinstance(item, ast.Constant) and isinstance(item.value, str)
                ]
        return path, methods
    raise AssertionError("auth-check route decorator not found")


def _handler_call_names(handler_node: ast.AsyncFunctionDef) -> list[str]:
    names: list[str] = []
    for statement in handler_node.body:
        for node in ast.walk(statement):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Name):
                names.append(node.func.id)
            elif isinstance(node.func, ast.Attribute):
                names.append(node.func.attr)
    return names


def _load_isolated_handler(fake_environment: dict[str, str]):
    source = SERVER_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(SERVER_PATH))
    auth_node = copy.deepcopy(_find_function(tree, "_require_internal_hook_auth"))
    handler_node = copy.deepcopy(_find_function(tree, "auth_check_hook"))

    path, methods = _route_contract(handler_node)
    if path != "/auth-check-hook" or methods != ["GET"]:
        raise AssertionError("auth-check route contract drifted")

    call_names = _handler_call_names(handler_node)
    if call_names != ["_require_internal_hook_auth", "Response"]:
        raise AssertionError(f"unexpected auth-check handler calls: {call_names}")

    auth_node.decorator_list = []
    handler_node.decorator_list = []
    isolated_module = ast.Module(body=[auth_node, handler_node], type_ignores=[])
    ast.fix_missing_locations(isolated_module)

    sentinels = {
        name: _FailOnAccess(name)
        for name in (
            "bucket_mgr",
            "portrait_engine",
            "continuity_store",
            "care_memo_store",
            "database",
            "production_state",
            "mutation_manager",
            "scheduler",
            "dehydrator",
            "provider_client",
            "openrouter_client",
            "llm_client",
            "gateway_client",
            "old_ombre",
            "breath",
            "dream_hook",
        )
    }
    namespace = {
        "os": SimpleNamespace(environ=dict(fake_environment)),
        "hmac": hmac,
        **sentinels,
    }
    exec(compile(isolated_module, str(SERVER_PATH), "exec"), namespace)
    return namespace["auth_check_hook"], sentinels


class AuthCheckHookTests(unittest.TestCase):
    def _invoke(self, *, configured: bool, presented: str | None):
        environment = (
            {"OMBRE_INTERNAL_HOOK_TOKEN": FAKE_CONFIGURED_TOKEN}
            if configured
            else {}
        )
        handler, sentinels = _load_isolated_handler(environment)
        headers = (
            {"x-ombre-internal-hook-token": presented}
            if presented is not None
            else {}
        )

        def forbidden(label: str):
            def fail(*args, **kwargs):
                raise AssertionError(f"forbidden side-effect boundary touched: {label}")

            return fail

        starlette_module = ModuleType("starlette")
        responses_module = ModuleType("starlette.responses")
        responses_module.JSONResponse = _JSONResponse
        responses_module.Response = _Response
        starlette_module.responses = responses_module

        with ExitStack() as stack:
            stack.enter_context(
                mock.patch.dict(
                    sys.modules,
                    {
                        "starlette": starlette_module,
                        "starlette.responses": responses_module,
                    },
                )
            )
            stack.enter_context(mock.patch.object(builtins, "open", forbidden("file-open")))
            stack.enter_context(mock.patch.object(Path, "open", forbidden("path-open")))
            stack.enter_context(mock.patch.object(Path, "read_text", forbidden("path-read-text")))
            stack.enter_context(mock.patch.object(Path, "read_bytes", forbidden("path-read-bytes")))
            stack.enter_context(mock.patch.object(Path, "write_text", forbidden("path-write-text")))
            stack.enter_context(mock.patch.object(Path, "write_bytes", forbidden("path-write-bytes")))
            stack.enter_context(mock.patch.object(sqlite3, "connect", forbidden("database-connect")))
            stack.enter_context(mock.patch.object(socket, "create_connection", forbidden("network-connect")))
            stack.enter_context(mock.patch.object(urllib.request, "urlopen", forbidden("network-request")))
            stack.enter_context(mock.patch.object(subprocess, "Popen", forbidden("process-start")))
            stack.enter_context(mock.patch.object(asyncio, "create_task", forbidden("async-task")))
            stack.enter_context(mock.patch.object(threading.Thread, "start", forbidden("thread-start")))
            response = asyncio.run(handler(_Request(headers)))

        self.assertTrue(all(sentinel.calls == 0 for sentinel in sentinels.values()))
        return response

    def test_valid_fake_token_returns_empty_204(self):
        response = self._invoke(configured=True, presented=FAKE_CONFIGURED_TOKEN)
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response.body, b"")

    def test_missing_token_returns_401(self):
        response = self._invoke(configured=True, presented=None)
        self.assertEqual(response.status_code, 401)

    def test_wrong_fake_token_returns_401(self):
        response = self._invoke(configured=True, presented=FAKE_WRONG_TOKEN)
        self.assertEqual(response.status_code, 401)

    def test_unconfigured_token_returns_503(self):
        response = self._invoke(configured=False, presented=None)
        self.assertEqual(response.status_code, 503)


if __name__ == "__main__":
    unittest.main()

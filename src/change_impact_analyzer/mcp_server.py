from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from . import __version__
from .analyzer import analyze
from .report import render_json, render_markdown


SERVER_NAME = "impact-map"
TOOL_NAME = "analyze_change_impact"


def main() -> int:
    server = McpServer()
    server.run()
    return 0


class McpServer:
    def run(self) -> None:
        while True:
            message = self._read_message()
            if message is None:
                return
            response = self._handle_message(message)
            if response is not None:
                self._write_message(response)

    def _handle_message(self, message: dict[str, Any]) -> dict[str, Any] | None:
        method = message.get("method")
        request_id = message.get("id")

        if method == "initialize":
            return self._result(
                request_id,
                {
                    "protocolVersion": message.get("params", {}).get("protocolVersion", "2024-11-05"),
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": SERVER_NAME, "version": __version__},
                },
            )

        if method == "notifications/initialized":
            return None

        if method == "ping":
            return self._result(request_id, {})

        if method == "tools/list":
            return self._result(request_id, {"tools": [tool_definition()]})

        if method == "tools/call":
            return self._call_tool(request_id, message.get("params", {}))

        if method == "resources/list":
            return self._result(request_id, {"resources": []})

        if method == "prompts/list":
            return self._result(request_id, {"prompts": []})

        if request_id is None:
            return None
        return self._error(request_id, -32601, f"Method not found: {method}")

    def _call_tool(self, request_id: Any, params: dict[str, Any]) -> dict[str, Any]:
        if params.get("name") != TOOL_NAME:
            return self._error(request_id, -32602, f"Unknown tool: {params.get('name')}")

        args = params.get("arguments", {})
        if not isinstance(args, dict):
            return self._tool_error(request_id, "Tool arguments must be an object.")

        repo = args.get("repo")
        request = args.get("request")
        if not isinstance(repo, str) or not repo.strip():
            return self._tool_error(request_id, "`repo` is required and must be a path string.")
        if not isinstance(request, str) or not request.strip():
            return self._tool_error(request_id, "`request` is required and must be a non-empty string.")

        top = _int_arg(args.get("top"), default=10, minimum=1, maximum=50)
        max_files = _int_arg(args.get("max_files"), default=5000, minimum=1, maximum=50_000)
        as_json = bool(args.get("json", False))

        try:
            result = analyze(Path(repo).expanduser(), request, top_n=top, max_files=max_files)
            text = render_json(result) if as_json else render_markdown(result)
        except Exception as exc:
            return self._tool_error(request_id, str(exc))

        return self._result(
            request_id,
            {
                "content": [{"type": "text", "text": text}],
                "isError": False,
            },
        )

    def _read_message(self) -> dict[str, Any] | None:
        headers: dict[str, str] = {}
        while True:
            line = sys.stdin.buffer.readline()
            if not line:
                return None
            if line in {b"\r\n", b"\n"}:
                break
            key, _, value = line.decode("ascii").partition(":")
            headers[key.lower()] = value.strip()

        length = int(headers.get("content-length", "0"))
        if length <= 0:
            return None

        payload = sys.stdin.buffer.read(length)
        return json.loads(payload.decode("utf-8"))

    def _write_message(self, message: dict[str, Any]) -> None:
        payload = json.dumps(message, separators=(",", ":")).encode("utf-8")
        sys.stdout.buffer.write(f"Content-Length: {len(payload)}\r\n\r\n".encode("ascii"))
        sys.stdout.buffer.write(payload)
        sys.stdout.buffer.flush()

    def _result(self, request_id: Any, result: dict[str, Any]) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "result": result}

    def _error(self, request_id: Any, code: int, message: str) -> dict[str, Any]:
        return {"jsonrpc": "2.0", "id": request_id, "error": {"code": code, "message": message}}

    def _tool_error(self, request_id: Any, message: str) -> dict[str, Any]:
        return self._result(
            request_id,
            {
                "content": [{"type": "text", "text": message}],
                "isError": True,
            },
        )


def tool_definition() -> dict[str, Any]:
    return {
        "name": TOOL_NAME,
        "description": (
            "Analyze a local repository for a requested code change and return likely impacted files, "
            "test suggestions, implementation steps, and risk checks."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo": {
                    "type": "string",
                    "description": "Absolute or relative path to the local repository to analyze.",
                },
                "request": {
                    "type": "string",
                    "description": "Plain-English code change request.",
                },
                "top": {
                    "type": "integer",
                    "description": "Number of impacted files to return.",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 50,
                },
                "max_files": {
                    "type": "integer",
                    "description": "Maximum source-like files to scan.",
                    "default": 5000,
                    "minimum": 1,
                    "maximum": 50000,
                },
                "json": {
                    "type": "boolean",
                    "description": "Return JSON instead of Markdown.",
                    "default": False,
                },
            },
            "required": ["repo", "request"],
            "additionalProperties": False,
        },
    }


def _int_arg(value: Any, default: int, minimum: int, maximum: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    return max(minimum, min(maximum, parsed))


if __name__ == "__main__":
    raise SystemExit(main())


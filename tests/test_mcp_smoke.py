"""Teste de fumaca do servidor MCP via protocolo stdio real.

Sobe ``python -m snapclip.mcp_server`` como subprocesso (exatamente como o
opencode fara), inicializa a sessao MCP, lista as ferramentas e faz um
roundtrip de texto no clipboard.
"""

from __future__ import annotations

import sys

import anyio
import pytest
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from snapclip import clipboard


async def _run_smoke() -> tuple[list[str], str]:
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "snapclip.mcp_server"],
        env={"PYTHONUTF8": "1"},
    )
    names: list[str] = []
    result_text = ""
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            names = [t.name for t in tools.tools]

            await session.call_tool("clipboard_set", {"text": "ping"})
            got = await session.call_tool("clipboard_get", {"kind": "text"})
            for block in got.content:
                if getattr(block, "type", None) == "text":
                    result_text += block.text
    return names, result_text


def test_mcp_smoke(preserved_clipboard):
    names, text = anyio.run(_run_smoke)
    print(f"\nTOOLS ({len(names)}): {sorted(names)}")
    print(f"clipboard_set(text='ping') -> clipboard_get(kind='text') = {text!r}")
    assert set(names) == {"screenshot", "clipboard_get", "clipboard_set"}
    assert text == "ping"

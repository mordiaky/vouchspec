from __future__ import annotations

import asyncio
from pathlib import Path
import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from capabilityproof.mcp_server import build_mcp_server


FIXTURES = Path(__file__).parent / "fixtures"


def test_mcp_registers_expected_tools_and_calls_inspector() -> None:
    server = build_mcp_server(FIXTURES)
    tools = asyncio.run(server.list_tools())
    names = {tool.name for tool in tools}
    assert names == {"inspect_skill", "get_methodology"}

    result = asyncio.run(
        server._tool_manager.call_tool(
            "inspect_skill",
            {"path": "valid-skill", "generated_at": "2026-07-14T03:00:00Z", "expires_in_days": 7},
            convert_result=True,
        )
    )
    assert result.structuredContent is not None
    assert result.structuredContent["format_validation"]["status"] == "pass"
    assert "untrusted" in result.structuredContent["artifact"]["claims_untrusted"]["notice"].lower()
    assert len(result.content) == 1
    assert result.content[0].type == "text"
    assert result.content[0].text == "Inspection completed; receipt is in structuredContent."
    assert "valid-skill" not in result.content[0].text


def test_mcp_stdio_keeps_artifact_text_out_of_unstructured_content() -> None:
    async def exercise() -> tuple[str, object]:
        parameters = StdioServerParameters(
            command=sys.executable,
            args=["-m", "capabilityproof", "mcp", "--allow-root", str(FIXTURES.resolve())],
        )
        async with stdio_client(parameters) as (read_stream, write_stream):
            async with ClientSession(read_stream, write_stream) as session:
                initialized = await session.initialize()
                result = await session.call_tool(
                    "inspect_skill",
                    {"path": "risky-skill", "generated_at": "2026-07-14T03:00:00Z", "expires_in_days": 7},
                )
                return initialized.protocolVersion, result

    protocol_version, result = asyncio.run(exercise())
    assert protocol_version == "2025-11-25"
    assert result.isError is False
    assert result.structuredContent is not None
    assert result.structuredContent["decision"]["status"] == "review-required"
    assert [block.text for block in result.content if block.type == "text"] == [
        "Inspection completed; receipt is in structuredContent."
    ]

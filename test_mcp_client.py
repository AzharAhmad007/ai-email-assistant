import asyncio
import json

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


def extract_tool_data(result):
    """Extract JSON data from an MCP tool result."""

    if result.isError:
        raise RuntimeError(f"Tool execution failed: {result.content}")

    for item in result.content:
        if item.type == "text":
            return json.loads(item.text)

    raise RuntimeError("No text content found in tool result.")


async def main():
    server_params = StdioServerParameters(
        command="python3",
        args=["-m", "app.mcp_server"],
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:

            await session.initialize()
            print("Connected to MCP server!")

            # Discover available tools
            tools_result = await session.list_tools()

            print("\nAvailable tools:")
            for tool in tools_result.tools:
                print(f"- {tool.name}: {tool.description}")

            # Generate a draft
            print("\nGenerating email draft...")

            result = await session.call_tool(
                "generate_email",
                {
                    "instructions": (
                        "Write a professional email requesting "
                        "two days of leave from my manager."
                    )
                },
            )

            draft = extract_tool_data(result)

            print("\nGenerated draft:")
            print(json.dumps(draft, indent=2))

            draft_id = draft["draft_id"]
            print("\nDraft ID:", draft_id)

            # Retrieve the saved draft
            print("\nRetrieving saved draft...")

            retrieved_result = await session.call_tool(
                "get_email_draft",
                {"draft_id": draft_id},
            )

            retrieved_draft = extract_tool_data(retrieved_result)

            print("\nRetrieved draft:")
            print(json.dumps(retrieved_draft, indent=2))

            # Update the existing draft
            print("\nUpdating email draft...")

            update_result = await session.call_tool(
                "update_email_draft",
                {
                    "draft_id": draft_id,
                    "recipient": "manager@example.com",
                    "subject": "Updated Leave Request",
                    "body": (
                        "Dear Manager,\n\n"
                        "I would like to request two days of leave. "
                        "Please let me know if you need any additional information.\n\n"
                        "Best regards"
                    ),
                },
            )

            updated_response = extract_tool_data(update_result)
            print("\nUpdate result:")
            print(json.dumps(updated_response, indent=2))

            # Retrieve the draft again to verify the changes
            print("\nVerifying updated draft...")

            verify_result = await session.call_tool(
                "get_email_draft",
                {"draft_id": draft_id},
            )

            verified_draft = extract_tool_data(verify_result)

            print("\nVerified draft:")
            print(json.dumps(verified_draft, indent=2))

            # Test that sending is rejected without explicit confirmation.
            print("\nTesting sending safeguards...")

            send_result = await session.call_tool(
                "send_approved_email",
                {
                    "draft_id": draft_id,
                    "confirmation": "NO",
                },
            )

            if send_result.isError:
                print("PASS: Invalid confirmation was rejected.")
                print(send_result.content)
            else:
                raise RuntimeError(
                    "FAIL: The tool unexpectedly accepted invalid confirmation."
                )


if __name__ == "__main__":
    asyncio.run(main())
#!/usr/bin/env python3
"""
Claude Code Worker - Dispatches tasks to Claude Code CLI
Uses Max subscription via CLI, not API
"""

import asyncio
import json
import os
from typing import Optional
from loguru import logger


class ClaudeCodeWorker:
    """Worker that dispatches tasks to Claude Code CLI."""

    def __init__(self):
        self.catalyst_dir = os.getenv("CATALYST_DIR", "{{CATALYST_ROOT}}")
        self.current_task: Optional[asyncio.Task] = None
        self.current_process: Optional[asyncio.subprocess.Process] = None

    async def execute(self, task: str) -> dict:
        """
        Execute a task via Claude Code CLI.

        Args:
            task: The task description to send to Claude Code

        Returns:
            dict with 'success', 'summary', and 'details'
        """
        logger.info(f"Executing task: {task[:100]}...")

        try:
            # Build Claude Code command with streaming JSON
            cmd = [
                "claude",
                "--print",
                "--verbose",
                "--output-format", "stream-json",
                task
            ]

            # Run in Catalyst directory for full context
            self.current_process = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=self.catalyst_dir,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            # Collect output
            stdout, stderr = await asyncio.wait_for(
                self.current_process.communicate(),
                timeout=300  # 5 minute timeout
            )

            # Parse streaming JSON output
            result = self._parse_output(stdout.decode())

            if self.current_process.returncode == 0:
                logger.info(f"Task completed successfully")
                return {
                    "success": True,
                    "summary": result.get("summary", "Task completed."),
                    "details": result
                }
            else:
                logger.error(f"Task failed with code {self.current_process.returncode}")
                return {
                    "success": False,
                    "summary": "Task encountered an error.",
                    "details": {"stderr": stderr.decode()}
                }

        except asyncio.TimeoutError:
            logger.error("Task timed out after 5 minutes")
            if self.current_process:
                self.current_process.terminate()
            return {
                "success": False,
                "summary": "Task timed out.",
                "details": {}
            }

        except Exception as e:
            logger.error(f"Task execution failed: {e}")
            return {
                "success": False,
                "summary": f"Execution error: {str(e)}",
                "details": {}
            }

        finally:
            self.current_process = None

    async def cancel(self):
        """Cancel the current task."""
        if self.current_process:
            logger.info("Cancelling current task...")
            self.current_process.terminate()
            try:
                await asyncio.wait_for(self.current_process.wait(), timeout=5)
            except asyncio.TimeoutError:
                self.current_process.kill()

    def _parse_output(self, output: str) -> dict:
        """Parse Claude Code streaming JSON output."""
        result = {
            "summary": "",
            "response": "",
            "duration_ms": 0,
            "tools_used": [],
        }

        for line in output.strip().split("\n"):
            if not line:
                continue

            try:
                event = json.loads(line)
                event_type = event.get("type")

                if event_type == "assistant":
                    # Extract assistant response
                    message = event.get("message", {})
                    content = message.get("content", [])
                    for item in content:
                        if item.get("type") == "text":
                            result["response"] = item.get("text", "")

                elif event_type == "result":
                    # Final result
                    result["summary"] = event.get("result", "")[:200]
                    result["duration_ms"] = event.get("duration_ms", 0)

                elif event_type == "tool_use":
                    # Track tools used
                    tool_name = event.get("name", "unknown")
                    result["tools_used"].append(tool_name)

            except json.JSONDecodeError:
                continue

        # Generate summary if not present
        if not result["summary"] and result["response"]:
            # Take first sentence of response
            first_sentence = result["response"].split(".")[0]
            result["summary"] = first_sentence[:200]

        return result


async def test_worker():
    """Test the Claude Code worker."""
    worker = ClaudeCodeWorker()

    print("Testing Claude Code Worker...")
    result = await worker.execute("Say 'Hello from Claude Code worker test' in exactly those words")

    print(f"Success: {result['success']}")
    print(f"Summary: {result['summary']}")
    print(f"Details: {json.dumps(result['details'], indent=2)}")


if __name__ == "__main__":
    asyncio.run(test_worker())

#!/usr/bin/env python3
"""
{{ORCHESTRATOR_NAME}} Gateway - WebSocket server for voice agent
Handles iOS client connections and routes to voice agent / Claude Code worker
"""

import asyncio
import json
import signal
from typing import Optional
from loguru import logger
import websockets
from websockets.server import WebSocketServerProtocol

from voice_agent import {{ORCHESTRATOR_NAME}}VoiceAgent
from claude_worker import ClaudeCodeWorker


class {{ORCHESTRATOR_NAME}}Gateway:
    """WebSocket gateway for {{ORCHESTRATOR_NAME}} voice conversations."""

    def __init__(self, host: str = "0.0.0.0", port: int = 18800):
        self.host = host
        self.port = port
        self.clients: dict[str, WebSocketServerProtocol] = {}
        self.voice_agent: Optional[{{ORCHESTRATOR_NAME}}VoiceAgent] = None
        self.worker: Optional[ClaudeCodeWorker] = None
        self.running = False

    async def start(self):
        """Start the gateway server."""
        logger.info(f"Starting {{ORCHESTRATOR_NAME}} Gateway on {self.host}:{self.port}")

        # Initialize components
        self.voice_agent = {{ORCHESTRATOR_NAME}}VoiceAgent()
        self.worker = ClaudeCodeWorker()

        await self.voice_agent.initialize()

        self.running = True

        async with websockets.serve(
            self.handle_client,
            self.host,
            self.port,
            ping_interval=30,
            ping_timeout=10,
        ):
            logger.info(f"{{ORCHESTRATOR_NAME}} Gateway listening on ws://{self.host}:{self.port}")
            await self.wait_for_shutdown()

    async def wait_for_shutdown(self):
        """Wait for shutdown signal."""
        stop = asyncio.Event()

        def signal_handler():
            stop.set()

        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, signal_handler)

        await stop.wait()
        logger.info("Shutting down {{ORCHESTRATOR_NAME}} Gateway...")
        self.running = False

    async def handle_client(self, websocket: WebSocketServerProtocol):
        """Handle a client connection."""
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f"Client connected: {client_id}")
        self.clients[client_id] = websocket

        try:
            async for message in websocket:
                await self.process_message(client_id, websocket, message)
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Client disconnected: {client_id}")
        finally:
            del self.clients[client_id]

    async def process_message(
        self,
        client_id: str,
        websocket: WebSocketServerProtocol,
        message: str
    ):
        """Process incoming message from client."""
        try:
            data = json.loads(message)
            msg_type = data.get("type")

            if msg_type == "transcript":
                # User spoke - process with voice agent
                text = data.get("text", "")
                logger.info(f"[{client_id}] Transcript: {text[:50]}...")
                await self.handle_transcript(client_id, websocket, text)

            elif msg_type == "interrupt":
                # User started speaking - stop current response
                logger.info(f"[{client_id}] Interrupt received")
                await self.handle_interrupt(client_id)

            elif msg_type == "ping":
                # Keep-alive ping
                await websocket.send(json.dumps({"type": "pong"}))

            else:
                logger.warning(f"[{client_id}] Unknown message type: {msg_type}")

        except json.JSONDecodeError:
            logger.error(f"[{client_id}] Invalid JSON: {message[:100]}")

    async def handle_transcript(
        self,
        client_id: str,
        websocket: WebSocketServerProtocol,
        text: str
    ):
        """Handle transcribed speech from user."""
        # Send immediate acknowledgment that we're processing
        # This keeps the connection alive and gives user feedback
        await websocket.send(json.dumps({
            "type": "status",
            "message": "processing"
        }))

        # Get response from voice agent (fast Llama)
        response_generator = self.voice_agent.process(text)

        async for event in response_generator:
            event_type = event.get("type")

            if event_type == "text":
                # Text chunk for TTS
                await websocket.send(json.dumps({
                    "type": "text",
                    "content": event.get("content", "")
                }))

            elif event_type == "audio":
                # Audio chunk from Kokoro
                import base64
                await websocket.send(json.dumps({
                    "type": "audio",
                    "format": "wav",
                    "data": base64.b64encode(event.get("data", b"")).decode()
                }))

            elif event_type == "dispatch":
                # Voice agent wants to dispatch to Claude Code
                task = event.get("task", "")
                logger.info(f"[{client_id}] Dispatching to Claude Code: {task[:50]}...")
                asyncio.create_task(
                    self.handle_claude_dispatch(client_id, websocket, task)
                )

            elif event_type == "done":
                # Response complete
                await websocket.send(json.dumps({"type": "done"}))

    async def handle_interrupt(self, client_id: str):
        """Handle user interruption."""
        if self.voice_agent:
            await self.voice_agent.interrupt()

    async def handle_claude_dispatch(
        self,
        client_id: str,
        websocket: WebSocketServerProtocol,
        task: str
    ):
        """Dispatch task to Claude Code and report back."""
        try:
            result = await self.worker.execute(task)

            # Generate completion message via voice agent
            completion_text = f"Task complete. {result.get('summary', 'Done.')}"

            response_generator = self.voice_agent.speak(completion_text)
            async for event in response_generator:
                if event.get("type") == "audio":
                    import base64
                    await websocket.send(json.dumps({
                        "type": "proactiveWake",
                        "audio": base64.b64encode(event.get("data", b"")).decode(),
                        "text": completion_text
                    }))

        except Exception as e:
            logger.error(f"[{client_id}] Claude dispatch failed: {e}")
            await websocket.send(json.dumps({
                "type": "error",
                "message": str(e)
            }))


async def main():
    """Main entry point."""
    logger.info("=" * 60)
    logger.info("{{ORCHESTRATOR_NAME_UPPER}} GATEWAY - Conversational AI Voice Agent")
    logger.info("=" * 60)

    gateway = {{ORCHESTRATOR_NAME}}Gateway()
    await gateway.start()


if __name__ == "__main__":
    asyncio.run(main())

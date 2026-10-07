#!/usr/bin/env python3
"""
TC3 ↔ TC2 Bot Communication Bridge

Enables @{{ORCHESTRATOR_NAME}}CatalystBot (TC3) to communicate with @iamspartacusbot (TC2)
using the existing OpenClaw multi-agent infrastructure.

Usage:
    # Send task to {{ORCHESTRATOR_NAME}} from {{ORCHESTRATOR_NAME}}
    await send_to_spartacus("Please run system diagnostics")
    
    # Send coordination message  
    await coordinate_with_spartacus("Let's sync on deployment timeline")
"""

import asyncio
import json
import logging
from datetime import datetime
from typing import Optional, Dict, Any
from telegram import Bot
from telegram.error import TelegramError

# Bot configurations
{{ORCHESTRATOR_NAME_UPPER}}_BOT_TOKEN = "123456789:YOUR_BOT_TOKEN"
SPARTACUS_BOT_USERNAME = "@iamspartacusbot" 
TY_USER_ID = {{TELEGRAM_CHAT_ID}}

class {{ORCHESTRATOR_NAME}}{{ORCHESTRATOR_NAME}}Bridge:
    """Communication bridge between {{ORCHESTRATOR_NAME}} (TC3) and {{ORCHESTRATOR_NAME}} (TC2)"""
    
    def __init__(self):
        self.{{ORCHESTRATOR_NAME_LOWER}}_bot = Bot(token={{ORCHESTRATOR_NAME_UPPER}}_BOT_TOKEN)
        self.logger = logging.getLogger("{{ORCHESTRATOR_NAME_LOWER}}_spartacus_bridge")
        
    async def send_to_spartacus(self, message: str, context: Dict[str, Any] = None) -> bool:
        """Send a message to {{ORCHESTRATOR_NAME}} via direct mention"""
        try:
            # Format message for {{ORCHESTRATOR_NAME}} with agent routing context
            formatted_message = f"""🤖 **{{ORCHESTRATOR_NAME_UPPER}} → SPARTACUS**

{message}

---
Context: {json.dumps(context or {}, indent=2)}
Timestamp: {datetime.now().isoformat()}
From: @{{ORCHESTRATOR_NAME}}CatalystBot (TC3)"""
            
            # Send to {{USER_NAME}} (who can relay to appropriate {{ORCHESTRATOR_NAME}} agent)
            await self.{{ORCHESTRATOR_NAME_LOWER}}_bot.send_message(
                chat_id=TY_USER_ID,
                text=f"{SPARTACUS_BOT_USERNAME}\n\n{formatted_message}"
            )
            
            self.logger.info(f"✅ Message sent to {{ORCHESTRATOR_NAME}} via {{USER_NAME}}: {message[:50]}...")
            return True
            
        except TelegramError as e:
            self.logger.error(f"❌ Failed to send message to {{ORCHESTRATOR_NAME}}: {e}")
            return False
    
    async def delegate_task_to_spartacus(self, task: str, agent: str = "main", priority: str = "normal") -> bool:
        """Delegate a specific task to a {{ORCHESTRATOR_NAME}} agent"""
        context = {
            "type": "task_delegation",
            "target_agent": agent,
            "priority": priority,
            "source": "{{ORCHESTRATOR_NAME_LOWER}}_tc3"
        }
        
        delegation_message = f"""🎯 **TASK DELEGATION**

Agent: {agent}
Priority: {priority}

**Task:** {task}

Please handle this task and report back when complete."""
        
        return await self.send_to_spartacus(delegation_message, context)
    
    async def coordinate_with_spartacus(self, coordination_request: str, agent: str = "main") -> bool:
        """Send coordination request to {{ORCHESTRATOR_NAME}}"""
        context = {
            "type": "coordination",
            "target_agent": agent,
            "source": "{{ORCHESTRATOR_NAME_LOWER}}_tc3"
        }
        
        coord_message = f"""🤝 **COORDINATION REQUEST**

Agent: {agent}

{coordination_request}"""
        
        return await self.send_to_spartacus(coord_message, context)
    
    async def request_spartacus_status(self, agent: str = "main") -> bool:
        """Request status from specific {{ORCHESTRATOR_NAME}} agent"""
        context = {
            "type": "status_request", 
            "target_agent": agent,
            "source": "{{ORCHESTRATOR_NAME_LOWER}}_tc3"
        }
        
        status_message = f"""📊 **STATUS REQUEST**

Agent: {agent}

Please provide current status, active tasks, and system health."""
        
        return await self.send_to_spartacus(status_message, context)

# Global bridge instance
bridge = {{ORCHESTRATOR_NAME}}{{ORCHESTRATOR_NAME}}Bridge()

# Convenience functions for integration
async def send_to_spartacus(message: str, context: Dict = None) -> bool:
    """Quick send to {{ORCHESTRATOR_NAME}} main agent"""
    return await bridge.send_to_spartacus(message, context)

async def delegate_to_spartacus(task: str, agent: str = "main", priority: str = "normal") -> bool:
    """Quick task delegation"""
    return await bridge.delegate_task_to_spartacus(task, agent, priority)

async def coordinate_with_spartacus(request: str, agent: str = "main") -> bool:
    """Quick coordination"""
    return await bridge.coordinate_with_spartacus(request, agent)

async def get_spartacus_status(agent: str = "main") -> bool:
    """Quick status check"""
    return await bridge.request_spartacus_status(agent)

# {{ORCHESTRATOR_NAME}} agent routing shortcuts
async def delegate_to_exampleteam(task: str, priority: str = "normal") -> bool:
    """Delegate task to Big Sky Tags agent"""
    return await delegate_to_spartacus(task, "exampleteam", priority)

async def delegate_to_mid_partners(task: str, priority: str = "normal") -> bool:
    """Delegate task to Example Partners agent"""  
    return await delegate_to_spartacus(task, "mid", priority)

async def delegate_to_wardrobe(task: str, priority: str = "normal") -> bool:
    """Delegate task to Wardrobe agent"""
    return await delegate_to_spartacus(task, "wardrobe", priority)

# Demo and testing
async def demo_communication():
    """Demo the bridge functionality"""
    print("🤖⚔️ Testing {{ORCHESTRATOR_NAME}} → {{ORCHESTRATOR_NAME}} Communication")
    
    # Test basic communication
    await send_to_spartacus("Hello {{ORCHESTRATOR_NAME}}! This is a test message from {{ORCHESTRATOR_NAME}}.")
    await asyncio.sleep(1)
    
    # Test task delegation
    await delegate_to_spartacus(
        "Please analyze the current Catalyst system metrics and report any anomalies",
        priority="high"
    )
    await asyncio.sleep(1)
    
    # Test agent-specific delegation
    await delegate_to_exampleteam("Check the Big Sky Tags deployment status")
    await asyncio.sleep(1)
    
    # Test coordination
    await coordinate_with_spartacus("Let's coordinate on the next Catalyst release deployment")
    await asyncio.sleep(1)
    
    # Test status request
    await get_spartacus_status("main")
    
    print("✅ Demo completed - check your Telegram for messages!")

if __name__ == "__main__":
    asyncio.run(demo_communication())
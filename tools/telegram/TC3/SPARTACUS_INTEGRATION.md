# 🤖⚔️ {{ORCHESTRATOR_NAME}} ↔ {{ORCHESTRATOR_NAME}} Integration

**Status: ✅ READY FOR DEPLOYMENT**

This integration enables **@{{ORCHESTRATOR_NAME}}CatalystBot (TC3)** to communicate directly with **@iamspartacusbot (TC2)** using the existing OpenClaw multi-agent infrastructure.

## 🎯 **How It Works**

1. **{{ORCHESTRATOR_NAME}}** (TC3) sends structured messages to **{{ORCHESTRATOR_NAME}}** (TC2)
2. **{{ORCHESTRATOR_NAME}}** has 5 specialized agents that can handle different tasks:
   - `main` - Default agent (Catalyst workspace)
   - `exampleteam` - Big Sky Tags specialist  
   - `mid` - Example Partners/exampleco specialist
   - `brotobot` - General bot coordination
   - `wardrobe` - Wardrobe shopping assistant

3. **OpenClaw routing** automatically directs messages to the right agent
4. **Responses** come back through Telegram to you (and {{ORCHESTRATOR_NAME}} can see them)

## ⚡ **Quick Integration**

### **Add to your {{ORCHESTRATOR_NAME}} bot handler:**

```python
import sys
sys.path.append('{{CATALYST_ROOT}}/tools/telegram/TC3')

from bot_to_bot_bridge import (
    delegate_to_spartacus,
    coordinate_with_spartacus,
    get_spartacus_status,
    delegate_to_exampleteam,
    delegate_to_mid_partners
)

# In your message handler
async def handle_delegation(update, context):
    user_message = update.message.text.lower()
    
    if "delegate to spartacus" in user_message:
        task = user_message.replace("delegate to spartacus", "").strip()
        await delegate_to_spartacus(task)
        await update.message.reply_text("✅ Task delegated to {{ORCHESTRATOR_NAME}} main agent")
    
    elif "ask spartacus about exampleteam" in user_message:
        await delegate_to_exampleteam("Please provide current Big Sky Tags status and metrics")
        await update.message.reply_text("✅ Big Sky status request sent to {{ORCHESTRATOR_NAME}}")
    
    elif "coordinate with spartacus" in user_message:
        await coordinate_with_spartacus("{{ORCHESTRATOR_NAME}} requesting coordination on current projects")
        await update.message.reply_text("✅ Coordination request sent to {{ORCHESTRATOR_NAME}}")
```

## 🚀 **Example Commands You Can Now Use**

### **Via Chat with {{ORCHESTRATOR_NAME}}:**

- **"Delegate to {{ORCHESTRATOR_NAME}}: Check system health"**
- **"Ask {{ORCHESTRATOR_NAME}} about exampleteam deployment status"** 
- **"Coordinate with {{ORCHESTRATOR_NAME}} on next release"**
- **"Get status from {{ORCHESTRATOR_NAME}} main agent"**

### **Programmatic Usage:**

```python
# Task delegation
await delegate_to_spartacus("Run diagnostics on all Catalyst capsules", priority="high")

# Specialist delegation  
await delegate_to_exampleteam("Check if Big Sky Tags portal is responding correctly")
await delegate_to_mid_partners("Review exampleco lead generation metrics")

# Coordination
await coordinate_with_spartacus("Let's plan the deployment timeline for this week")

# Status checks
await get_spartacus_status("main")  # Main agent
await get_spartacus_status("exampleteam")  # Big Sky specialist
```

## 📱 **What You'll See in Telegram**

When {{ORCHESTRATOR_NAME}} communicates with {{ORCHESTRATOR_NAME}}, you'll see messages like:

```
@iamspartacusbot

🤖 **{{ORCHESTRATOR_NAME_UPPER}} → SPARTACUS**

Please run diagnostics on all Catalyst capsules and report any issues.

---
Context: {
  "type": "task_delegation",
  "target_agent": "main", 
  "priority": "high",
  "source": "{{ORCHESTRATOR_NAME_LOWER}}_tc3"
}
Timestamp: 2026-02-21T17:30:00
From: @{{ORCHESTRATOR_NAME}}CatalystBot (TC3)
```

Then {{ORCHESTRATOR_NAME}} will respond with the results!

## 🔧 **Current Configuration**

- ✅ **OpenClaw Updated**: Added {{ORCHESTRATOR_NAME}} bot ID ({{TELEGRAM_CHAT_ID}}) to `groupAllowFrom`
- ✅ **Gateway Restarted**: Changes applied
- ✅ **Bridge Ready**: Communication functions available
- ✅ **Agent Routing**: Messages automatically route to correct {{ORCHESTRATOR_NAME}} agent

## 🎮 **Test the Integration**

```bash
cd {{CATALYST_ROOT}}/tools/telegram/TC3
python3 bot_to_bot_bridge.py
```

This will send test messages to demonstrate the communication flow.

## 📊 **Available {{ORCHESTRATOR_NAME}} Agents**

| Agent | Emoji | Workspace | Specialization |
|-------|-------|-----------|----------------|
| `main` | ⚔️ | `{{CATALYST_ROOT}}` | General Catalyst operations |
| `exampleteam` | 🏔️ | `capsules/example-team-tags` | Big Sky Tags project |
| `mid` | 🏠 | `capsules/example-partners` | Example Partners/exampleco |
| `brotobot` | 🤖 | `{{CATALYST_ROOT}}` | Bot coordination |
| `wardrobe` | 👗 | `capsules/wardrobe-shopper` | Shopping assistant |

## 🎯 **Next Steps**

1. **Test the integration** with the demo script
2. **Add bot delegation logic** to your {{ORCHESTRATOR_NAME}} message handlers  
3. **Create voice commands** like "Ask {{ORCHESTRATOR_NAME}} to check exampleteam"
4. **Set up automated task routing** based on context
5. **Monitor bot-to-bot communication** for optimization

## 🔍 **Monitoring & Debugging**

```bash
# Check OpenClaw status
openclaw gateway status

# View agent routing
openclaw agents list --bindings

# Check logs
tail -f /tmp/openclaw/openclaw-$(date +%Y-%m-%d).log

# Test agent communication
openclaw channels status --probe
```

## 🎉 **Result**

You now have **autonomous agent delegation**! {{ORCHESTRATOR_NAME}} can:

- ✅ Delegate tasks to specialized {{ORCHESTRATOR_NAME}} agents
- ✅ Get status reports from different workspaces  
- ✅ Coordinate multi-agent activities
- ✅ Route requests to the most appropriate specialist

**The agents can now work together while you focus on higher-level strategy!** 🤖⚔️

---

*"I am become {{ORCHESTRATOR_NAME}}, delegator of agents."* - Ready for autonomous coordination, sir!
# Patchworks MCP Server - AI Assistant Instructions

## Flow Creation Optimization

When handling flow creation requests, follow these efficiency rules to minimize tool calls:

### Direct Flow Creation Rules

**WHEN USER REQUESTS FLOW CREATION:**
- User says: "create a flow", "make a flow", "new flow", "create a process flow"
- **DO NOT** search past conversations first
- **DO NOT** search documentation first  
- **DO NOT** call conversation_search or recent_chats
- **GO DIRECTLY** to `create_process_flow_from_json`

**DEFAULT FLOW TEMPLATE:**
Use this minimal structure immediately when creating flows:

```json
{
  "metadata": {
    "company_name": "MCP Created",
    "flow_name": "[USER'S FLOW NAME]",
    "exported_at": "[CURRENT_TIMESTAMP]",
    "exported_by": "claude-mcp",
    "import_summary": {
      "setup_required": {
        "connectors_needing_config": 0,
        "auth_implementations_needing_credentials": 0,
        "variables_needing_values": 0
      },
      "dependencies": [],
      "imported_resources": {
        "systems_imported": 0,
        "flow_steps": 1,
        "endpoints": 0,
        "connectors": 0
      },
      "next_steps": []
    }
  },
  "flow": {
    "name": "[USER'S FLOW NAME]",
    "description": "[DESCRIPTION OR 'Flow created via MCP']",
    "is_enabled": false,
    "versions": [
      {
        "flow_name": "[USER'S FLOW NAME]",
        "flow_priority": 3,
        "iteration": 1,
        "status": "Draft",
        "is_deployed": false,
        "is_editable": true,
        "has_callback_step": false,
        "steps": [
          {
            "id": 1,
            "type": "trigger",
            "name": "Trigger",
            "description": "Default hourly trigger",
            "config": {
              "schedule_type": "cron",
              "cron_expression": "0 * * * *"
            },
            "position": {
              "x": 100,
              "y": 100
            }
          }
        ],
        "connections": []
      }
    ]
  },
  "systems": [],
  "scripts": [],
  "dependencies": []
}
```

### When to Search Documentation

**ONLY** search documentation if:
- User asks "how do I create a flow?" (informational)
- User asks about flow structure or requirements
- User encounters an error and needs help understanding it
- User asks about specific flow features or capabilities

**DO NOT** search documentation for direct action requests like "create a flow called X"

### When to Search Past Conversations

**ONLY** search past conversations if:
- User explicitly references past work: "like the flow we made yesterday"
- User asks about previous flows by name without creating new ones
- User asks for flow modifications based on previous discussions

**DO NOT** search past conversations for new flow creation requests

## Failure Investigation

When a user asks "why did X fail?", "what went wrong?", or similar:
- **Use `investigate_failure` as your FIRST tool.** It resolves the flow, finds the failed run,
  summarises logs, downloads payloads, and follows the alert chain — all in one call.
- Only fall back to individual tools if `investigate_failure` doesn't return enough detail.

When a user asks "what payload did we send?" or "show me the payload":
- **Use `get_run_payloads`** with the run ID. Optionally filter by step_name (e.g. "Catch").

### Alert / notification flows
- Flows like "Slack Failure Alert" are triggered when another flow fails.
- The important information is in the *originating* flow, not the alert flow itself.
- `investigate_failure` follows this chain automatically via the catch-route payload.

## Tool Call Budget Guidelines

The tool call budget is now 10 iterations per request. For Slack and other constrained
environments, still aim for efficiency:

### 1-2 Tool Calls (Preferred for simple tasks)
- Create flow with default settings
- List flows
- Get flow status
- Start a flow
- **Investigate a failure** (use `investigate_failure` — 1 call does it all)
- **Get payloads** (use `get_run_payloads` — 1 call)

### 3-4 Tool Calls (For moderate complexity)
- Create flow + verify it was created
- Troubleshoot a specific flow run
- Search docs + answer question

### 5-10 Tool Calls (Complex tasks)
- Triage multiple failures
- Deep investigation of flow issues
- Comparative analysis across multiple flows

## Response Patterns for Flow Creation

### ✅ GOOD (Efficient)
```
User: "Create a flow called Order Sync"
Assistant: [Immediately calls create_process_flow_from_json]
Response: "Created 'Order Sync' flow (ID: 42) with hourly trigger..."
Total tool calls: 1
```

### ❌ BAD (Inefficient)
```
User: "Create a flow called Order Sync"
Assistant: [Calls conversation_search for "flow"]
Assistant: [Calls search_docs for "create flow"]
Assistant: [Calls recent_chats to check history]
Assistant: [Finally calls create_process_flow_from_json]
Response: "I've created..."
Total tool calls: 4+ (EXCEEDS SLACK LIMIT)
```

## Default Flow Settings

When user doesn't specify:
- **Priority:** 3 (Normal)
- **Schedule:** `0 * * * *` (hourly)
- **Enabled:** false (Draft mode)
- **Trigger Type:** Cron schedule

Common schedule requests:
- "every hour" → `0 * * * *`
- "every 15 minutes" → `*/15 * * * *`
- "daily" → `0 0 * * *`
- "twice a day" → `0 0,12 * * *`
- "weekdays at 9am" → `0 9 * * 1-5`

## Error Handling

If flow creation fails:
1. Show the error message to the user
2. ONLY THEN search docs if the error is unclear
3. Suggest fixes based on the error
4. Offer to retry with corrections

## Summary

**Key Principle:** Assume the user wants immediate action, not research. Only search/investigate when explicitly asked or when troubleshooting errors.

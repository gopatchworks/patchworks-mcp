# Custom Tools

This directory is for **user-defined custom tools only**. Users can add their own MCP tools without modifying the core server code.

## Files

- **`tools.py`** - Define your custom tools here (EDITABLE)
- **`schemas.py`** - Define Pydantic schemas for tool arguments (EDITABLE)
- **`__init__.py`** - Package initialization (DO NOT EDIT)

## How to Add a Custom Tool

### 1. Define Your Schema (schemas.py)

First, create a Pydantic model for your tool's arguments:

```python
from pydantic import BaseModel, Field
from typing import Optional

class MyToolArgs(BaseModel):
    input_text: str = Field(..., description="Text to process")
    count: int = Field(1, ge=1, le=10, description="Number of times to repeat")
    uppercase: bool = Field(False, description="Convert to uppercase")
```

### 2. Create Your Tool (tools.py)

Inside the `register_custom_tools()` function, add your tool:

```python
@mcp.tool()
def my_custom_tool(args: MyToolArgs) -> Any:
    """
    Process text and repeat it multiple times.

    This description appears in MCP tools/list responses.
    """
    text = args.input_text

    if args.uppercase:
        text = text.upper()

    return {
        "result": text * args.count,
        "processed": True
    }
```

### 3. Test Your Tool

Restart the MCP server:
```bash
uv run fastmcp run server.py:mcp --transport http --host 0.0.0.0 --port 8020
```

List tools to verify it's registered:
```bash
curl -X POST http://localhost:8020/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -H "mcp-session-id: YOUR_SESSION" \
  -d '{"jsonrpc": "2.0", "method": "tools/list", "params": {}, "id": 1}'
```

Call your tool:
```bash
curl -X POST http://localhost:8020/mcp \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -H "mcp-session-id: YOUR_SESSION" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "my_custom_tool",
      "arguments": {
        "args": {
          "input_text": "hello",
          "count": 3,
          "uppercase": true
        }
      }
    },
    "id": 2
  }'
```

## Important Rules

1. **All tools MUST be defined inside `register_custom_tools(mcp)` function**
   - Tools defined outside won't have access to the `mcp` instance

2. **Use the `@mcp.tool()` decorator for each tool**

3. **Helper functions should also be inside `register_custom_tools()`**

4. **Import external libraries at the top of the file**

5. **Tool functions must return JSON-serializable data**

## Example: Adding External API Tool

```python
# In tools.py
import requests

def register_custom_tools(mcp: FastMCP):

    @mcp.tool()
    def fetch_weather(args: WeatherArgs) -> Any:
        """Fetch weather data for a city."""
        response = requests.get(
            f"https://api.weather.com/v1/weather",
            params={"city": args.city, "api_key": "YOUR_KEY"}
        )
        return response.json()
```

## Accessing Patchworks Client

If you need to use Patchworks API client in custom tools:

```python
import patchworks_client as pw

def register_custom_tools(mcp: FastMCP):

    @mcp.tool()
    def custom_flow_analyzer(args: AnalyzerArgs) -> Any:
        """Analyze flows with custom logic."""
        flows = pw.get_all_flows(page=1, per_page=100)
        # Your custom analysis logic
        return {"analysis": "results"}
```

## Need Help?

- Check `defaults/tools.py` for more complex examples
- All default Patchworks tools follow the same pattern
Patchworks MCP --- Local Setup Guide
==================================

With Patchworks MCP you can connect the Patchworks iPaaS directly to an AI assistant (Claude, Gemini, ChatGPT, etc.) and control it conversationally.

This guide shows how to set up the MCP server locally on your machine with some pre-built tools.

Commerce Foundation Support now included
-------------------------------------------
Each Commerce Foundation capability is exposed as an MCP tool.

The server provides the 12 fulfillment operations as per <https://github.com/commerce-operations-foundation/mcp-reference-server/blob/develop/README.md>:

### Action Tools

- `create-sales-order` - Create new orders from any channel
- `update-order` - Modify order details and line items
- `cancel-order` - Cancel orders with reason tracking
- `fulfill-order` - Mark orders as fulfilled and return shipment details
- `create-return` - Create returns for order items with refund/exchange tracking

### Query Tools

- `get-orders` - Retrieve order information
- `get-customers` - Get customer details
- `get-products` - Get product information
- `get-product-variants` - Retrieve variant-level data
- `get-inventory` - Check inventory levels
- `get-fulfillments` - Track fulfillment status
- `get-returns` - Query return records and status

Requests are executed via Patchworks flows  
Implementations require customers or partners to build their own flows to handle Commerce Foundation requests  
Patchworks can provide example and reference flows to accelerate implementation and demonstrate best practice  

* * * * *

* * * * *

Step 1 --- Create your Patchworks MCP project
-------------------------------------------

Make a folder for the MCP server inside your home directory.

Get the files from git <https://github.com/gopatchworks/patchworks-mcp>

`cd ~ git clone git@github.com:gopatchworks/patchworks-mcp.git cd patchworks-mcp`

You now have **4 key files**:

1.  `pyproject.toml` --- tells Python what your project is and what it depends on (includes FastMCP).

2.  `.env.example` --- template showing which environment variables the server needs.

3.  `patchworks_client.py` --- encapsulates all the HTTP calls to the Patchworks API.

4.  `server.py` --- the MCP server that Claude (or any MCP client) connects to.

👉 In short:

-   `pyproject.toml` = project + dependencies

-   `.env.example` = config template (safe to share)

-   `patchworks_client.py` = logic to talk to Patchworks API

-   `server.py` = wires those APIs into Claude via MCP

* * * * *

Step 2 --- Install dependencies with `uv`
---------------------------------------

We'll use [**uv**](https://astral.sh/uv "https://astral.sh/uv") --- a fast Python dependency manager.\
It simplifies installing packages and running your server.

### Install `uv`

`curl -LsSf https://astral.sh/uv/install.sh | sh export PATH="$HOME/.local/bin:$PATH"`

Restart your terminal, then check:

`uv --version`

### If that fails, create a virtual environment manually:

`cd ~/patchworks-mcp # create/activate venv uv venv && source .venv/bin/activate # install dependencies uv pip install "mcp[cli]>=0.1.0" "pydantic>=2.7" "python-dotenv>=1.0" "requests>=2.32"`

* * * * *

### Configure your environment

Copy the example file and edit with your real values:

`cd ~/patchworks-mcp cp .env.example .env nano .env`

Update PATCHWORKS_TOKEN with your API KEY ( [How to get your API KEY](https://doc.wearepatchworks.com/product-documentation/developer-hub/patchworks-api/core-api-authentication/api-keys "https://doc.wearepatchworks.com/product-documentation/developer-hub/patchworks-api/core-api-authentication/api-keys") ):

`# Core read/triage API PATCHWORKS_CORE_API=https://core.wearepatchworks.com/api/v1 PATCHWORKS_BASE_URL=https://core.wearepatchworks.com/api/v1 # Start service to run flows PATCHWORKS_START_API=https://start.wearepatchworks.com/api/v1 # Auth PATCHWORKS_TOKEN=XXXXXXXXXXXXXX # Default timeout for HTTP requests PATCHWORKS_TIMEOUT_SECONDS=20`

Save: **CTRL+O**, Enter, then **CTRL+X**.

* * * * *

### Run the server

From inside the project folder:

`uv run python server.py`

If it starts cleanly, your MCP server is now running locally.

* * * * *

Step 3 --- Wire into Claude Desktop
---------------------------------

To use MCP you need a client that can connect to local servers.

-   **Claude Desktop** (macOS/Windows): [Download here](https://claude.ai/download "https://claude.ai/download")

-   Other clients (Gemini, ChatGPT with MCP support) work the same way.

Claude Desktop is the easiest starting point, so this guide assumes Claude.

Claude needs to know how to start your MCP server. That's done via a config file.

1.  **Create a config file (macOS example):**\
    Create a claude_desktop_config.json file in your Application Support folder for Claude

    `nano $HOME/Library/Application\ Support/Claude/claude_desktop_config.json`

    Add this entry (update paths and Token)

    `{ "mcpServers": { "patchworks": { "command": "/Users/yourname/.local/bin/uv", "args": [ "--directory", "/Users/yourname/patchworks-mcp", "run", "python", "server.py" ], "env": { "PATCHWORKS_BASE_URL": "https://core.wearepatchworks.com/api/v1", "PATCHWORKS_TOKEN": "XXXXXXXXXXXXXXXX", "PATCHWORKS_TIMEOUT_SECONDS": "20" } } } }`

    -   `command` → path to your uv binary (check with `which uv`)

    -   `args` → tells Claude how to start the server

    -   `env` → config passed into your MCP server

2.  **Quit & relaunch Claude Desktop.**

* * * * *

Step 4 --- Test it
----------------

Open Claude and type:

> "I’d like a full list of my flows, please."

Claude will prompt to approve a tool call, then the Patchworks MCP server will return live data from your account.

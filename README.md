# Vinverse LLM Orchestrator

The "brain" service: the Application API's chat endpoints call this instead of
calling an LLM directly. This service is an **MCP client** — it fetches the
Project State and documents it needs from the
[MCP Server](../vinverse-mcp-server) via the Model Context Protocol, builds
the Master Consultant prompt, and routes to a model provider.

```
Application API  --POST /consult-->  Orchestrator  --MCP tool calls-->  MCP Server  --HTTP-->  Application API (/internal/*)
                                          |
                                          v
                                    Model Router --> Anthropic (only provider today)
```

Yes, the Orchestrator calls back toward the Application API indirectly (via
the MCP server) — that's intentional. The Application API remains the single
source of truth for project data; the Orchestrator never touches a database
directly.

## Running it

```
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edit .env: set ANTHROPIC_API_KEY, and confirm MCP_SERVER_URL points at a
# running MCP server instance
uvicorn app.main:app --reload --port 8002
```

Start order matters: **Application API → MCP Server → Orchestrator**. Then
point the Application API's `ORCHESTRATOR_URL` at wherever this ends up
running (`.env` in the backend repo).

## Multi-model routing

`app/model_router.py` is deliberately a single seam. Today it only implements
Anthropic. Adding GPT or Gemini later means adding another branch there, each
using its own organizational API credential — **not** a fellow's personal
ChatGPT/Claude subscription. This matters because OpenAI in particular
separates ChatGPT and API billing entirely; there's no way to "consume" a
personal subscription programmatically. Vinverse needs its own authorized API
connections regardless of what any individual fellow already pays for.

## A note on the MCP SDK version

Same caveat as the MCP server's README: the `mcp` Python package's client API
(`ClientSession`, `streamablehttp_client`) matches recent releases as of this
writing, but import paths and the default HTTP route (`/mcp`) have shifted
across versions. If `fetch_project_context` fails to connect, check your
installed version against the MCP server's actual listening path.

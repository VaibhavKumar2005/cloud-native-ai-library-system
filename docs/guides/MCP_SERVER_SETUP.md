# VeriRAG MCP Server Setup Guide

This guide shows how to connect your VeriRAG backend to Claude Desktop using the Model Context Protocol (MCP).

## What is MCP?

The Model Context Protocol allows Claude (and other AI assistants) to call functions you define. With this MCP server, Claude can:

- **Query your documents** in natural language
- **Monitor document ingestion** progress
- **Analyze document coverage** across topics
- **Run batch queries** for evaluation or analysis

## Why Use It?

Instead of manually copying/pasting between Claude and your VeriRAG UI, Claude can:
- Ask questions about your documents directly
- Get faithfulness scores and citations automatically
- Help you analyze and evaluate your RAG system
- Use results in larger workflows

## Prerequisites

1. **Python 3.10+** on your machine
2. **VeriRAG backend running** (local or remote)
3. **Claude Desktop** (not web version)
4. **FastMCP library**: `pip install fastmcp`

## Installation

### 1. Install FastMCP

```bash
pip install fastmcp
```

### 2. Update `requirements.txt`

Add to your backend `requirements.txt`:

```
fastmcp>=0.1.0
```

Then:

```bash
pip install -r requirements.txt
```

### 3. Locate Your Claude Desktop Config

**macOS/Linux:**
```bash
~/.config/Claude/claude_desktop_config.json
```

**Windows:**
```
%APPDATA%\Claude\claude_desktop_config.json
```

### 4. Add VeriRAG to Claude Desktop Config

Open your config file and add the MCP server section:

```json
{
  "mcpServers": {
    "verirag": {
      "command": "python",
      "args": ["/absolute/path/to/mcp_server.py"],
      "env": {
        "VERIRAG_API_BASE": "http://localhost:8000/api",
        "VERIRAG_API_TOKEN": "your-bearer-token-here",
        "VERIRAG_DEFAULT_USER_ID": "1"
      }
    }
  }
}
```

### 5. Update Configuration Values

Replace these with your actual values:

| Setting | Example | Notes |
|---------|---------|-------|
| `args[0]` | `/Users/you/projects/verirag/apps/backend/mcp_server.py` | Full path to mcp_server.py |
| `VERIRAG_API_BASE` | `http://localhost:8000/api` | Or your deployed backend URL |
| `VERIRAG_API_TOKEN` | Your Bearer token | Get from your VeriRAG auth system |
| `VERIRAG_DEFAULT_USER_ID` | `1` | User ID for queries (1 for local testing) |

### 6. Restart Claude Desktop

- Quit Claude Desktop completely
- Relaunch it
- You should see a "🔨" (hammer/tools) icon at the bottom of the chat

## Usage

### Test Connection

In Claude Desktop chat, type:

```
@verirag Use the health_check tool to verify connection to VeriRAG
```

Claude will call the health check and show results.

### List Your Documents

```
@verirag What documents do I have uploaded? Use list_documents to show them.
```

Claude will use the MCP tool to fetch and display your documents.

### Query Your Documents

```
@verirag I have some documents about AI safety. Can you query the library with "What are the main AI safety concerns?" and show me the answer with faithfulness score?
```

Claude will:
1. Call `query_library` with your question
2. Get back the answer, citations, and faithfulness score
3. Format and display results

### Analyze Document Coverage

```
@verirag Check if document ID 5 covers these topics: [security, performance, scalability, cost]
```

Claude will use `analyze_document_coverage` and show you which topics are covered.

### Batch Queries for Evaluation

```
@verirag Run these questions against my documents:
1. What is the main purpose?
2. What are the key limitations?
3. What metrics were used to evaluate success?

Then summarize the faithfulness scores and tell me which questions were answered most confidently.
```

Claude will use `batch_query` and provide analysis.

## Configuration Details

### Environment Variables

Set these in your `claude_desktop_config.json` `env` section:

```json
{
  "VERIRAG_API_BASE": "http://localhost:8000/api",
  "VERIRAG_API_TOKEN": "Bearer token for authentication",
  "VERIRAG_DEFAULT_USER_ID": "User ID (default: 1)"
}
```

### Remote Backend

If your VeriRAG is deployed on Azure:

```json
{
  "VERIRAG_API_BASE": "https://your-backend.azurecontainers.io/api"
}
```

### Authentication

For securing the MCP server with a real API token:

1. **Get your token** from VeriRAG's auth system
2. **Set it in config**:
   ```json
   {
     "VERIRAG_API_TOKEN": "your-actual-bearer-token"
   }
   ```
3. **Restart Claude Desktop**

For local development without auth:

```json
{
  "VERIRAG_API_TOKEN": ""
}
```

## Troubleshooting

### "Tool not found" error

Check that:
1. Claude Desktop was fully restarted after config change
2. Path to `mcp_server.py` is absolute (full path, not relative)
3. File exists and is readable

### "Connection refused" error

Ensure:
1. VeriRAG backend is running: `docker-compose up -d`
2. `VERIRAG_API_BASE` matches your backend URL
3. Backend health check works: `curl http://localhost:8000/api/health/`

### "Unauthorized" error

Check:
1. `VERIRAG_API_TOKEN` is set correctly
2. Token is still valid (hasn't expired)
3. Backend requires authentication (see your VeriRAG settings)

### MCP Server Crashes

Check Claude logs:
- **macOS**: `/Users/[username]/Library/Logs/Claude/mcp.log`
- **Windows**: `%APPDATA%\Claude\log.txt`

Look for Python errors in the log.

## Available Tools

### Core Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `query_library` | Ask question about documents | "What are the key findings?" |
| `get_document_status` | Check ingestion progress | Monitor document #5 |
| `list_documents` | See all your documents | Show me what's uploaded |

### Advanced Tools

| Tool | Purpose | Example |
|------|---------|---------|
| `batch_query` | Multiple questions at once | Evaluate 10 questions |
| `analyze_document_coverage` | Check topic coverage | Do docs cover security? |
| `health_check` | Verify backend connectivity | Is backend running? |
| `get_config` | View MCP configuration | Show current settings |

## Security Considerations

### Token Security

- **Never commit your token** to git
- **Never share your config** file publicly
- **Use environment variables** or `.env` files outside of git

### Example with .env:

Instead of hardcoding the token:

```json
{
  "env": {
    "VERIRAG_API_TOKEN": "${VERIRAG_TOKEN}"
  }
}
```

Then set locally:

```bash
export VERIRAG_TOKEN="your-secret-token"
```

### Network Security

- For remote backends, use **HTTPS only**
- Ensure backend requires **authentication**
- Consider **VPN/firewall rules** for production

## Advanced: Custom Configuration

### Use Different User IDs

Tell Claude which user to query as:

```json
{
  "VERIRAG_DEFAULT_USER_ID": "42"
}
```

Or ask Claude:

```
@verirag Query as user 3: "What documents does user 3 have?"
```

### Multiple Backend Instances

You can configure multiple VeriRAG instances:

```json
{
  "mcpServers": {
    "verirag-local": {
      "command": "python",
      "args": ["/path/to/mcp_server.py"],
      "env": {
        "VERIRAG_API_BASE": "http://localhost:8000/api"
      }
    },
    "verirag-prod": {
      "command": "python",
      "args": ["/path/to/mcp_server.py"],
      "env": {
        "VERIRAG_API_BASE": "https://prod-backend.azure.com/api",
        "VERIRAG_API_TOKEN": "prod-token"
      }
    }
  }
}
```

Then use:

```
@verirag-local What's in my local documents?
@verirag-prod What documents are in production?
```

## References

- [Model Context Protocol (MCP)](https://modelcontextprotocol.io/)
- [Claude Desktop Guide](https://claude.ai/desktop)
- [FastMCP Python SDK](https://github.com/jlouis/fastmcp)
- [VeriRAG API Documentation](../API_SPEC.md)

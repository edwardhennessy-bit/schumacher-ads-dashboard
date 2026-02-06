"""
MCP Gateway Client — connects to the SingleGrain MCP Gateway via HTTP.

Implements the MCP (Model Context Protocol) Streamable HTTP transport:
  1. POST /mcp  method=initialize  → get mcp-session-id header
  2. POST /mcp  method=notifications/initialized  (with session header)
  3. POST /mcp  method=tools/call  (with session header) → get data

The session is established once and reused for subsequent tool calls.
If the session expires, the client re-initializes automatically.
"""

import httpx
import json
import structlog
from typing import Any, Dict, Optional

logger = structlog.get_logger(__name__)

DEFAULT_GATEWAY_URL = "https://gatewayapi-production.up.railway.app"
MCP_ENDPOINT = "/mcp"


class MCPGatewayClient:
    """
    Lightweight MCP client for calling gateway tools from the backend.

    Usage:
        client = MCPGatewayClient(token="sg_...")
        result = await client.call_tool("googleads_campaign_performance", {
            "customerId": "3428920141",
            "startDate": "2026-02-01",
            "endDate": "2026-02-05",
        })
    """

    def __init__(
        self,
        gateway_url: str = DEFAULT_GATEWAY_URL,
        gateway_token: str = "",
    ):
        self.gateway_url = gateway_url.rstrip("/")
        self.gateway_token = gateway_token
        self._session_id: Optional[str] = None
        self._request_id = 0

    @property
    def is_configured(self) -> bool:
        return bool(self.gateway_token)

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def _base_headers(self) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.gateway_token:
            headers["Authorization"] = f"Bearer {self.gateway_token}"
        return headers

    async def _initialize(self) -> bool:
        """Perform MCP initialize handshake and store session ID."""
        url = f"{self.gateway_url}{MCP_ENDPOINT}"
        headers = self._base_headers()

        init_payload = {
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "schumacher-dashboard", "version": "1.0"},
            },
            "id": self._next_id(),
        }

        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(url, headers=headers, json=init_payload)
                resp.raise_for_status()

                session_id = resp.headers.get("mcp-session-id")
                if not session_id:
                    logger.error("mcp_init_no_session_id")
                    return False

                self._session_id = session_id
                logger.info("mcp_session_initialized", session_id=session_id)

                # Send initialized notification
                notif_headers = {**headers, "mcp-session-id": session_id}
                notif_payload = {
                    "jsonrpc": "2.0",
                    "method": "notifications/initialized",
                }
                await client.post(url, headers=notif_headers, json=notif_payload)

                return True

        except Exception as e:
            logger.error("mcp_init_failed", error=str(e))
            self._session_id = None
            return False

    async def call_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Call an MCP tool on the gateway.

        Returns the parsed JSON content from the tool result,
        or {"error": "..."} on failure.
        """
        if not self.is_configured:
            return {"error": "Gateway token not configured"}

        # Initialize session if needed
        if not self._session_id:
            ok = await self._initialize()
            if not ok:
                return {"error": "Failed to initialize MCP session"}

        # Try the call, re-init on session expiry
        result = await self._do_call(tool_name, arguments)
        if isinstance(result, dict) and result.get("_session_expired"):
            logger.info("mcp_session_expired_retrying", tool=tool_name)
            self._session_id = None
            ok = await self._initialize()
            if not ok:
                return {"error": "Failed to re-initialize MCP session"}
            result = await self._do_call(tool_name, arguments)

        return result

    async def _do_call(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute a single tools/call request."""
        url = f"{self.gateway_url}{MCP_ENDPOINT}"
        headers = {**self._base_headers(), "mcp-session-id": self._session_id or ""}

        payload = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            },
            "id": self._next_id(),
        }

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, headers=headers, json=payload)

                if resp.status_code == 200:
                    body = resp.json()

                    # Check for JSON-RPC error
                    if "error" in body:
                        err_msg = body["error"].get("message", "Unknown error")
                        if "Invalid session" in err_msg:
                            return {"_session_expired": True}
                        return {"error": err_msg}

                    # Extract content from result
                    result = body.get("result", {})
                    content_list = result.get("content", [])

                    # MCP tools return content as [{type: "text", text: "..."}]
                    for item in content_list:
                        if item.get("type") == "text":
                            try:
                                return json.loads(item["text"])
                            except (json.JSONDecodeError, KeyError):
                                return {"raw_text": item.get("text", "")}

                    return {"error": "No text content in tool result"}

                else:
                    body = resp.text
                    if "Invalid session" in body:
                        return {"_session_expired": True}
                    return {"error": f"HTTP {resp.status_code}: {body[:200]}"}

        except Exception as e:
            logger.error("mcp_tool_call_failed", tool=tool_name, error=str(e))
            return {"error": str(e)}


# Module-level singleton (lazy init)
_client: Optional[MCPGatewayClient] = None


def get_mcp_client(gateway_url: str = "", gateway_token: str = "") -> MCPGatewayClient:
    """Get or create the MCP gateway client singleton."""
    global _client
    if _client is None or (gateway_token and _client.gateway_token != gateway_token):
        _client = MCPGatewayClient(
            gateway_url=gateway_url or DEFAULT_GATEWAY_URL,
            gateway_token=gateway_token,
        )
    return _client

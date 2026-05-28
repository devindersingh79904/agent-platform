# Security Architecture and Policies

This document details the security constraints, configurations, and audit trailing policies of the Devinder AI Agent Studio platform.

## 1. CORS Allowed Origins Fallback

To secure the backend against Cross-Origin Resource Sharing (CORS) attacks:
- **Default Origin**: The fallback value of `CORS_ALLOWED_ORIGINS` is set to `http://localhost:3000` instead of a wildcard `*`.
- **Wildcard Allowances**: A wildcard `*` is only used if explicitly configured inside the environment variables:
  ```env
  CORS_ALLOWED_ORIGINS=*
  ```
- **Origin Parsing**: Multiple comma-separated origins (e.g. `http://localhost:3000,https://app.devinder.ai`) are parsed, stripped of whitespace, and added as separate allowed origins in the FastAPI CORSMiddleware.

## 2. API Authorization

Global API-key based authentication can be enabled by setting:
```env
API_AUTH_ENABLED=true
API_KEY=your_secret_api_key_here
```
When active, all incoming REST and WebSocket requests (excluding `/health` and `/ready` endpoints) must include the `X-API-Key` header matching the configured token. The frontend client includes this header automatically when configured.

## 3. Guardrail Blocked Tool-Call Persistence

As part of the security audit trailing policy, any tool call request emitted by the LLM that is blocked by guardrails is recorded inside the database:
- **Creation**: A `ToolCall` record is created with the requested parameters and arguments.
- **Status**: The record status is marked as `FAILED` (with status code payload `BLOCKED`).
- **Error Reason**: The `error_message` records the specific guardrail rule violated (e.g., unauthorized tool name, keyword breach, call quota exceeded).
- **Audit logs**: Broadcasting `TOOL_CALL_FAILED` and `GUARDRAIL_VIOLATION` events logs these violations immediately in the visual timeline for real-time monitoring and security alerts.

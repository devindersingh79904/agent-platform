# How to Add a New Tool

Follow these steps to register a new Python tool in the platform:

1. **Create the Tool Class**:
   In `backend/app/tools/core_tools.py`, create a class extending `ToolInterface`:
   ```python
   from app.tools.base import ToolInterface, ToolResult

   class CurrencyConverterTool(ToolInterface):
       name = "currency_converter"
       description = "Converts currencies using mock rates."
       input_schema = {
           "type": "object",
           "properties": {
               "amount": {"type": "number"},
               "from_currency": {"type": "string"},
               "to_currency": {"type": "string"}
           },
           "required": ["amount", "from_currency", "to_currency"]
       }

       async def execute(self, input_data: dict, context: dict = None) -> ToolResult:
           # Tool execution logic
           amount = input_data.get("amount", 0)
           converted = amount * 1.1 # Dummy conversion
           return ToolResult(success=True, output={"converted_amount": converted})
   ```

2. **Register in Tool Registry**:
   Add the tool instance to `TOOL_REGISTRY` at the bottom of the file:
   ```python
   TOOL_REGISTRY = {
       # ...
       "currency_converter": CurrencyConverterTool()
   }
   ```

   `backend/app/tools/tool_registry.py` exposes `get_openai_tool_schemas(tool_names)`, which converts registered tools into OpenAI-compatible function schemas. The schema name must match the value used in `Agent.tools_json`, because LLM-directed tool calls are authorized against that list before execution.

3. **Assign to Agents**:
   - In the Agent UI or `seed.py`, assign `"currency_converter"` to the agent's `tools_json` list (e.g. `["currency_converter"]`).
   - During an AGENT node, the LLM receives only schemas for the agent's configured tools. If the model requests the tool, the runtime executes it, persists a `ToolCall`, sends the result back to the LLM as a tool message, and stores the final `AgentMessage`.

4. **Guardrails**:
   - `guardrails_json.allowed_tools` can narrow the tools an agent may call.
   - Blocked keywords and max tool-call limits are checked before executing LLM-requested tools.
   - Unknown or unauthorized tool calls are persisted as guardrail violations and fail the run before the tool executes.
## Included Tool Examples

The repository also includes a real search tool implementation:
- `duckduckgo_search_tool`: performs a live DuckDuckGo search without any API key.
- `calculator_tool`: safely evaluates arithmetic expressions.
- `knowledge_base_lookup`: searches local knowledge base content.
- `summarizer`: summarizes long text.
- `draft_response_tool`: drafts final text output.

DuckDuckGo search failures are persisted as `ToolCall` errors and the runtime will continue to show the failure state in the Run Monitor.

Tests should monkeypatch `TOOL_REGISTRY["duckduckgo_search_tool"]` with a deterministic fake instead of calling the real network-backed DuckDuckGo implementation. OpenAI tool-calling tests monkeypatch `AsyncOpenAI` or the runtime LLM client so no external network is required.

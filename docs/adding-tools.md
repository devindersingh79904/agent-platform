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

3. **Assign to Agents**:
   - In the Agent UI or `seed.py`, assign `"currency_converter"` to the agent's `tools_json` list (e.g. `["currency_converter"]`).
## Included Tool Examples

The repository also includes a real search tool implementation:
- `duckduckgo_search_tool`: performs a live DuckDuckGo search without any API key.
- `calculator_tool`: safely evaluates arithmetic expressions.
- `knowledge_base_lookup`: searches local knowledge base content.
- `summarizer`: summarizes long text.
- `draft_response_tool`: drafts final text output.

DuckDuckGo search failures are persisted as `ToolCall` errors and the runtime will continue to show the failure state in the Run Monitor.

Tests should monkeypatch `TOOL_REGISTRY["duckduckgo_search_tool"]` with a deterministic fake instead of calling the real network-backed DuckDuckGo implementation.

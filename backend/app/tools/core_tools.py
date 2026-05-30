from app.tools.base import ToolInterface, ToolResult
import time

class CalculatorTool(ToolInterface):
    name = "calculator"
    description = "Evaluates basic math expressions."
    input_schema = {
        "type": "object",
        "properties": {
            "expression": {"type": "string", "description": "Mathematical expression"}
        },
        "required": ["expression"]
    }

    async def execute(self, input_data: dict, context: dict = None) -> ToolResult:
        expression = input_data.get("expression", "")
        try:
            # MVP safe eval
            allowed_chars = "0123456789+-*/(). "
            if not all(c in allowed_chars for c in expression):
                raise ValueError("Invalid characters in expression")
            result = eval(expression)
            return ToolResult(success=True, output={"result": result})
        except Exception as e:
            return ToolResult(success=False, output={}, error=str(e))

class DuckDuckGoSearchTool(ToolInterface):
    name = "duckduckgo_search_tool"
    description = "Searches the web using DuckDuckGo without requiring an API key."
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"},
            "max_results": {"type": "integer", "default": 5}
        },
        "required": ["query"]
    }

    async def execute(self, input_data: dict, context: dict = None) -> ToolResult:
        query = input_data.get("query", "")
        max_results = int(input_data.get("max_results", 5) or 5)

        if not query.strip():
            return ToolResult(
                success=False,
                output={"provider": "duckduckgo", "query": query, "results": []},
                error="query is required",
                metadata={"provider": "duckduckgo"}
            )

        try:
            from ddgs import DDGS

            results = []
            with DDGS() as ddgs:
                for item in ddgs.text(query, max_results=max_results):
                    results.append({
                        "title": item.get("title"),
                        "url": item.get("href") or item.get("url"),
                        "snippet": item.get("body") or item.get("snippet")
                    })

            return ToolResult(
                success=True,
                output={"provider": "duckduckgo", "query": query, "results": results},
                metadata={"result_count": len(results)}
            )
        except Exception as exc:
            return ToolResult(
                success=False,
                output={"provider": "duckduckgo", "query": query, "results": []},
                error=str(exc),
                metadata={"provider": "duckduckgo"}
            )

class MockWebSearchTool(ToolInterface):
    name = "web_search_mock"
    description = "Mocks a web search for deterministic testing."
    input_schema = {
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search query"}
        },
        "required": ["query"]
    }

    async def execute(self, input_data: dict, context: dict = None) -> ToolResult:
        query = input_data.get("query", "").lower()
        results = [
            {"title": "AI Agents for Support", "snippet": "AI agents reduce ticket resolution time by 40%."},
            {"title": "LangGraph Tutorial", "snippet": "LangGraph allows stateful multi-agent workflows."}
        ]
        return ToolResult(success=True, output={"provider": "mock", "query": query, "results": results})

class KnowledgeBaseTool(ToolInterface):
    name = "knowledge_base_lookup"
    description = "Searches internal knowledge base."
    input_schema = {
        "type": "object",
        "properties": {
            "topic": {"type": "string", "description": "Topic to look up"}
        },
        "required": ["topic"]
    }

    async def execute(self, input_data: dict, context: dict = None) -> ToolResult:
        topic = input_data.get("topic", "").lower()
        kb = {
            "refund": "Refunds are processed within 5-7 business days.",
            "payment": "We accept major credit cards and PayPal."
        }
        found = next((v for k, v in kb.items() if k in topic), "No knowledge base entry found.")
        return ToolResult(success=True, output={"entry": found})

class SummarizerTool(ToolInterface):
    name = "summarizer"
    description = "Summarizes long text."
    input_schema = {
        "type": "object",
        "properties": {
            "text": {"type": "string", "description": "Text to summarize"}
        },
        "required": ["text"]
    }

    async def execute(self, input_data: dict, context: dict = None) -> ToolResult:
        text = input_data.get("text", "")
        summary = text[:100] + "..." if len(text) > 100 else text
        return ToolResult(success=True, output={"summary": f"Summarized: {summary}"})

class DraftGeneratorTool(ToolInterface):
    name = "draft_generator"
    description = "Generates a draft response."
    input_schema = {
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "Prompt for draft"}
        },
        "required": ["prompt"]
    }

    async def execute(self, input_data: dict, context: dict = None) -> ToolResult:
        prompt = input_data.get("prompt", "")
        return ToolResult(success=True, output={"draft": f"Draft based on '{prompt}'\n\nThis is an automated draft response."})

class DraftResponseTool(ToolInterface):
    name = "draft_response_tool"
    description = "Drafts final response text."
    input_schema = {
        "type": "object",
        "properties": {
            "prompt": {"type": "string", "description": "Prompt for response"}
        },
        "required": ["prompt"]
    }

    async def execute(self, input_data: dict, context: dict = None) -> ToolResult:
        prompt = input_data.get("prompt", "")
        return ToolResult(success=True, output={"draft": f"Draft response based on '{prompt}'\n\nThis is an automated draft response."})

TOOL_REGISTRY = {
    "calculator": CalculatorTool(),
    "calculator_tool": CalculatorTool(),
    "duckduckgo_search_tool": DuckDuckGoSearchTool(),
    "web_search_mock": MockWebSearchTool(),
    "knowledge_base_lookup": KnowledgeBaseTool(),
    "knowledge_base_tool": KnowledgeBaseTool(),
    "summarizer": SummarizerTool(),
    "summarizer_tool": SummarizerTool(),
    "draft_generator": DraftGeneratorTool(),
    "draft_generator_tool": DraftGeneratorTool(),
    "draft_response_tool": DraftResponseTool()
}

ALL_TOOLS = TOOL_REGISTRY

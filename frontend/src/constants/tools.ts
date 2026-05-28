export const TOOL_NAMES = {
  DUCKDUCKGO_SEARCH: "duckduckgo_search_tool",
  CALCULATOR: "calculator_tool",
  KNOWLEDGE_BASE: "knowledge_base_tool",
  SUMMARIZER: "summarizer_tool",
  DRAFT_RESPONSE: "draft_response_tool",
} as const;

export const TOOL_OPTIONS = [
  { label: "DuckDuckGo Search", value: TOOL_NAMES.DUCKDUCKGO_SEARCH },
  { label: "Calculator", value: TOOL_NAMES.CALCULATOR },
  { label: "Knowledge Base", value: TOOL_NAMES.KNOWLEDGE_BASE },
  { label: "Summarizer", value: TOOL_NAMES.SUMMARIZER },
  { label: "Draft Response", value: TOOL_NAMES.DRAFT_RESPONSE },
];

export const DEFAULT_TOOL_CONFIGS = {
  [TOOL_NAMES.DUCKDUCKGO_SEARCH]: {
    query_source: "workflow_input",
    max_results: 5,
  },
  [TOOL_NAMES.CALCULATOR]: {
    expression: "1 + 1",
  },
  [TOOL_NAMES.KNOWLEDGE_BASE]: {
    query_source: "workflow_input",
  },
  [TOOL_NAMES.SUMMARIZER]: {
    text_source: "current_output",
  },
  [TOOL_NAMES.DRAFT_RESPONSE]: {
    prompt_source: "current_output",
  },
} as const;

export const API_ROUTES = {
  CONFIG: "/config",
  AGENTS: "/agents",
  AGENT_BY_ID: (agentId: string) => `/agents/${agentId}`,
  WORKFLOWS: "/workflows",
  WORKFLOW_BY_ID: (workflowId: string) => `/workflows/${workflowId}`,
  WORKFLOW_GRAPH: (workflowId: string) => `/workflows/${workflowId}/graph`,
  WORKFLOW_RUNS: (workflowId: string) => `/workflows/${workflowId}/runs`,
  TEMPLATES: "/templates",
  TEMPLATE_CREATE_WORKFLOW: (templateId: string) => `/templates/${templateId}/create-workflow`,
  RUNS: "/runs",
  RUN_BY_ID: (runId: string) => `/runs/${runId}`,
  RUN_MESSAGES: (runId: string) => `/runs/${runId}/messages`,
  RUN_LOGS: (runId: string) => `/runs/${runId}/logs`,
  RUN_TOOL_CALLS: (runId: string) => `/runs/${runId}/tool-calls`,
  RUN_TOKEN_USAGE: (runId: string) => `/runs/${runId}/token-usage`,
  WS_RUN: (runId: string, correlationId: string, lastEventId?: number) => {
    const base = `/ws/runs/${runId}?correlation_id=${encodeURIComponent(correlationId)}`;
    return lastEventId ? `${base}&last_event_id=${lastEventId}` : base;
  },
} as const;

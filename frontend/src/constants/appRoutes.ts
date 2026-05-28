export const APP_ROUTES = {
  DASHBOARD: "/",
  AGENTS: "/agents",
  WORKFLOWS: "/workflows",
  WORKFLOW_BUILDER: (workflowId: string) => `/workflows/${workflowId}`,
  TEMPLATES: "/templates",
  RUNS: "/runs",
  RUN_MONITOR: (runId: string) => `/runs/${runId}`,
  SCHEDULES: "/schedules",
  MEMORY: "/memory",
  CHANNELS: "/channels",
  CHANNEL_MESSAGES: "/channels/messages"
} as const;

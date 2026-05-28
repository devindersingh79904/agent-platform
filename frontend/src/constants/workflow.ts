export const WORKFLOW_NODE_TYPES = {
  START: "START",
  AGENT: "AGENT",
  TOOL: "TOOL",
  CONDITION: "CONDITION",
  HUMAN_REVIEW: "HUMAN_REVIEW",
  END: "END",
} as const;

export const WORKFLOW_RUN_STATUS = {
  QUEUED: "QUEUED",
  RUNNING: "RUNNING",
  COMPLETED: "COMPLETED",
  FAILED: "FAILED",
} as const;

export const EDGE_CONDITION_TYPES = {
  ALWAYS: "always",
  APPROVED: "approved",
  REJECTED: "rejected",
  RESOLVED: "resolved",
  ESCALATE: "escalate",
  EXPRESSION: "expression",
} as const;

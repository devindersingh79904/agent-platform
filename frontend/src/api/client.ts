import axios from 'axios';
import { API_ROUTES } from '../constants/apiRoutes';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

const api = axios.create({
  baseURL: API_BASE_URL,
});

export const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:8000';

export function getOrCreateCorrelationId(): string {
  let id = sessionStorage.getItem("correlation_id");
  if (!id) {
    id = `FRONT-${crypto.randomUUID()}`;
    sessionStorage.setItem("correlation_id", id);
  }
  return id;
}

api.interceptors.request.use((config) => {
  config.headers = config.headers || {};
  config.headers["X-Correlation-ID"] = getOrCreateCorrelationId();
  
  const apiKey = import.meta.env.VITE_API_KEY;
  if (apiKey) {
    config.headers["X-API-Key"] = apiKey;
  }
  
  return config;
});

function unwrap<T>(response: any): T {
  return response.data?.data ?? response.data;
}

function unwrapContent<T>(response: any): T[] {
  const data = unwrap<any>(response);
  return data?.content ?? data ?? [];
}

export const getAgents = async (page = 1, size = 20) => unwrapContent<any>(await api.get(API_ROUTES.AGENTS, { params: { page, size } }));
export const createAgent = async (data: any) => unwrap<any>(await api.post(API_ROUTES.AGENTS, data));
export const updateAgent = async (id: string, data: any) => unwrap<any>(await api.put(API_ROUTES.AGENT_BY_ID(id), data));
export const deleteAgent = async (id: string) => unwrap<any>(await api.delete(API_ROUTES.AGENT_BY_ID(id)));

export const getWorkflows = async (page = 1, size = 20) => unwrapContent<any>(await api.get(API_ROUTES.WORKFLOWS, { params: { page, size } }));
export const createWorkflow = async (data: any) => unwrap<any>(await api.post(API_ROUTES.WORKFLOWS, data));
export const updateWorkflow = async (id: string, data: any) => unwrap<any>(await api.put(API_ROUTES.WORKFLOW_BY_ID(id), data));
export const deleteWorkflow = async (id: string) => unwrap<any>(await api.delete(API_ROUTES.WORKFLOW_BY_ID(id)));
export const getWorkflowGraph = async (id: string) => unwrap<any>(await api.get(API_ROUTES.WORKFLOW_GRAPH(id)));
export const updateWorkflowGraph = async (id: string, data: any) => unwrap<any>(await api.put(API_ROUTES.WORKFLOW_GRAPH(id), data));

export const getTemplates = async () => unwrapContent<any>(await api.get(API_ROUTES.TEMPLATES));
export const createWorkflowFromTemplate = async (templateId: string) => unwrap<any>(await api.post(API_ROUTES.TEMPLATE_CREATE_WORKFLOW(templateId)));

export const getRuns = async (page = 1, size = 20) => unwrapContent<any>(await api.get(API_ROUTES.RUNS, { params: { page, size } }));
export const getRunsPaginated = async (
  page = 1,
  size = 20,
  filters?: { workflowId?: string; status?: string }
) => {
  const params: any = { page, size };
  if (filters?.workflowId) params.workflow_id = filters.workflowId;
  if (filters?.status) params.status = filters.status;
  const response = await api.get(API_ROUTES.RUNS, { params });
  return unwrap<any>(response);
};
export const getConfig = async () => unwrap<any>(await api.get(API_ROUTES.CONFIG));
export const createRun = async (
  workflowId: string,
  payload: { message: string; source?: string }
) => {
  const response = await api.post(API_ROUTES.WORKFLOW_RUNS(workflowId), payload);
  return unwrap<any>(response);
};
export const getRun = async (runId: string) => unwrap<any>(await api.get(API_ROUTES.RUN_BY_ID(runId)));
export const getRunLogs = async (runId: string) => unwrap<any[]>(await api.get(API_ROUTES.RUN_LOGS(runId)));
export const getRunNodeRuns = async (runId: string, page = 1, size = 20) => unwrapContent<any>(await api.get(API_ROUTES.RUN_NODE_RUNS(runId), { params: { page, size } }));
export const getRunMessages = async (runId: string) => unwrap<any[]>(await api.get(API_ROUTES.RUN_MESSAGES(runId)));
export const getRunToolCalls = async (runId: string) => unwrap<any[]>(await api.get(API_ROUTES.RUN_TOOL_CALLS(runId)));
export const getRunTokenUsage = async (runId: string) => unwrap<any[]>(await api.get(API_ROUTES.RUN_TOKEN_USAGE(runId)));

export const cancelRun = async (runId: string) => unwrap<any>(await api.post(API_ROUTES.RUN_CANCEL(runId)));
export const resumeRun = async (runId: string) => unwrap<any>(await api.post(API_ROUTES.RUN_RESUME(runId)));
export const getRunMetrics = async (runId: string) => unwrap<any>(await api.get(API_ROUTES.RUN_METRICS(runId)));

export const getSchedules = async (page = 1, size = 20) => unwrapContent<any>(await api.get(API_ROUTES.SCHEDULES, { params: { page, size } }));
export const createSchedule = async (data: any) => unwrap<any>(await api.post(API_ROUTES.SCHEDULES, data));
export const updateSchedule = async (id: string, data: any) => unwrap<any>(await api.put(API_ROUTES.SCHEDULE_BY_ID(id), data));
export const deleteSchedule = async (id: string) => unwrap<any>(await api.delete(API_ROUTES.SCHEDULE_BY_ID(id)));
export const triggerSchedule = async (id: string) => unwrap<any>(await api.post(API_ROUTES.SCHEDULE_TRIGGER(id)));

export const getAgentMemories = async (agentId: string) => unwrapContent<any>(await api.get(API_ROUTES.AGENT_MEMORIES(agentId)));
export const createAgentMemory = async (agentId: string, data: any) => unwrap<any>(await api.post(API_ROUTES.AGENT_MEMORIES(agentId), data));
export const updateAgentMemory = async (agentId: string, memoryId: string, data: any) => unwrap<any>(await api.put(API_ROUTES.AGENT_MEMORY_BY_ID(agentId, memoryId), data));
export const deleteAgentMemory = async (agentId: string, memoryId: string) => unwrap<any>(await api.delete(API_ROUTES.AGENT_MEMORY_BY_ID(agentId, memoryId)));

export const getChannelMessages = async (page = 1, size = 20) => unwrapContent<any>(await api.get(API_ROUTES.CHANNEL_MESSAGES, { params: { page, size } }));
export const getRunChannelMessages = async (runId: string) => unwrap<any[]>(await api.get(API_ROUTES.RUN_CHANNEL_MESSAGES(runId)));

export default api;

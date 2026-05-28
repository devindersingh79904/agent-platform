import { useEffect, useState, useRef } from 'react';
import { useParams } from 'react-router-dom';
import { getOrCreateCorrelationId, getRunLogs, getRunMessages, getRunToolCalls, getRunTokenUsage, getRun, WS_BASE_URL } from '../api/client';
import { AlertTriangle, MessageSquare, Terminal, Wrench, Coins } from 'lucide-react';
import { API_ROUTES } from '../constants/apiRoutes';
import { UI_MESSAGES } from '../constants/messages';
import { WORKFLOW_RUN_STATUS } from '../constants/workflow';
import { WS_EVENTS } from '../constants/wsEvents';

const RunMonitor = () => {
  const { runId } = useParams<{ runId: string }>();
  const [status, setStatus] = useState("CONNECTING...");
  const [logs, setLogs] = useState<any[]>([]);
  const [messages, setMessages] = useState<any[]>([]);
  const [toolCalls, setToolCalls] = useState<any[]>([]);
  const [tokenUsage, setTokenUsage] = useState<any[]>([]);
  const [runData, setRunData] = useState<any>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const ws = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (!runId) return;

    setLoading(true);
    setError(null);
    Promise.all([
      getRun(runId).catch(() => null),
      getRunLogs(runId).catch(() => []),
      getRunMessages(runId).catch(() => []),
      getRunToolCalls(runId).catch(() => []),
      getRunTokenUsage(runId).catch(() => [])
    ]).then(([run, pastLogs, pastMsgs, pastTools, pastTokens]) => {
      if (run) {
        setRunData(run);
        if (run.status) setStatus(run.status);
      }
      setLogs(pastLogs);
      setMessages(pastMsgs);
      setToolCalls(pastTools);
      setTokenUsage(pastTokens);

      const maxEventId = pastLogs.length > 0 ? Math.max(...pastLogs.map((log: any) => log.event_id || 0)) : undefined;

      const wsUrl = WS_BASE_URL.startsWith('ws')
        ? `${WS_BASE_URL}${API_ROUTES.WS_RUN(runId, getOrCreateCorrelationId(), maxEventId)}`
        : `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}${WS_BASE_URL}${API_ROUTES.WS_RUN(runId, getOrCreateCorrelationId(), maxEventId)}`;
      
      ws.current = new WebSocket(wsUrl);
      
      ws.current.onopen = () => setStatus("LIVE");
      ws.current.onclose = () => setStatus("DISCONNECTED");
      
      ws.current.onmessage = (event) => {
        const data = JSON.parse(event.data);
        const { event_type, payload } = data;
        
        if (event_type === WS_EVENTS.RUN_COMPLETED) {
          setRunData((prev: any) => ({
            ...prev,
            status: WORKFLOW_RUN_STATUS.COMPLETED,
            output_json: payload?.output || prev?.output_json,
            completed_at: data.timestamp,
          }));
          setStatus(WORKFLOW_RUN_STATUS.COMPLETED);
        } else if (event_type === WS_EVENTS.RUN_FAILED) {
          setRunData((prev: any) => ({
            ...prev,
            status: WORKFLOW_RUN_STATUS.FAILED,
            error_message: data.message || payload?.error,
            completed_at: data.timestamp,
          }));
          setStatus(WORKFLOW_RUN_STATUS.FAILED);
        } else if (event_type === WS_EVENTS.RUN_STARTED || event_type === WS_EVENTS.RUN_QUEUED) {
          setRunData((prev: any) => ({
            ...prev,
            status: event_type === WS_EVENTS.RUN_STARTED ? WORKFLOW_RUN_STATUS.RUNNING : WORKFLOW_RUN_STATUS.QUEUED,
          }));
          setStatus(event_type === WS_EVENTS.RUN_STARTED ? WORKFLOW_RUN_STATUS.RUNNING : WORKFLOW_RUN_STATUS.QUEUED);
        }

        if ([WS_EVENTS.RUN_STARTED, WS_EVENTS.NODE_STARTED, WS_EVENTS.NODE_COMPLETED, WS_EVENTS.RUN_COMPLETED, WS_EVENTS.RUN_FAILED, WS_EVENTS.CONDITION_EVALUATED].includes(event_type)) {
          setLogs(prev => [...prev, data]);
        } else if (event_type === WS_EVENTS.AGENT_MESSAGE_CREATED) {
          setMessages(prev => [...prev, data]);
        } else if (event_type === WS_EVENTS.TOOL_CALL_STARTED || event_type === WS_EVENTS.TOOL_CALL_COMPLETED || event_type === WS_EVENTS.TOOL_CALL_FAILED) {
          setToolCalls(prev => [...prev, data]);
        } else if (event_type === WS_EVENTS.TOKEN_USAGE_RECORDED) {
          setTokenUsage(prev => [...prev, {
            agent_id: data.agent_id,
            model: payload.model,
            prompt_tokens: payload.prompt_tokens,
            completion_tokens: payload.completion_tokens,
            total_tokens: payload.total_tokens,
            estimated_cost: payload.estimated_cost
          }]);
        }
      };
    }).catch(err => {
      console.error(UI_MESSAGES.RUN_HISTORY_FETCH_FAILED, err);
      setError(UI_MESSAGES.RUN_HISTORY_FETCH_FAILED);
    }).finally(() => setLoading(false));

    return () => {
      if (ws.current) ws.current.close();
    };
  }, [runId]);

  const totalTokens = tokenUsage.reduce((acc, t) => acc + (t.total_tokens || 0), 0);
  const totalCost = tokenUsage.reduce((acc, t) => acc + Number(t.estimated_cost || 0), 0);
  const parseOutput = (value: string) => {
    try {
      return JSON.parse(value).final_message || value;
    } catch {
      return value;
    }
  };

  return (
    <div className="h-full flex flex-col space-y-4">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-slate-900 flex items-center space-x-3">
          <span>Run Monitor</span>
          <span className={`text-sm px-3 py-1 rounded-full font-bold ${status === 'LIVE' ? 'bg-green-100 text-green-700' : 'bg-slate-200 text-slate-600'}`}>
            {status}
          </span>
          {runData?.status && (
            <span className={`text-sm px-3 py-1 rounded-full font-bold ${
              runData.status === WORKFLOW_RUN_STATUS.COMPLETED ? 'bg-emerald-100 text-emerald-700' :
              runData.status === WORKFLOW_RUN_STATUS.FAILED ? 'bg-rose-100 text-rose-700' :
              runData.status === WORKFLOW_RUN_STATUS.RUNNING ? 'bg-blue-100 text-blue-700' :
              'bg-amber-100 text-amber-700'
            }`}>
              {runData.status}
            </span>
          )}
        </h1>
        <div className="flex space-x-6 items-center">
          <div className="flex items-center space-x-2 text-slate-700 bg-white border border-slate-200 px-4 py-2 rounded-lg shadow-sm">
            <Coins size={18} className="text-yellow-500" />
            <div className="flex flex-col text-xs font-mono">
              <span>Tokens: {totalTokens}</span>
              <span>Cost: ${totalCost.toFixed(5)}</span>
            </div>
          </div>
          <div className="font-mono text-sm text-slate-500">Run ID: {runId}</div>
        </div>
      </div>
      {loading && <div className="bg-white border border-slate-200 rounded-lg p-4 text-slate-500">Loading run history...</div>}
      {error && <div className="bg-rose-50 border border-rose-200 rounded-lg p-4 text-rose-700">{error}</div>}
      {runData?.status === WORKFLOW_RUN_STATUS.FAILED && runData?.error_message && (
        <div className="flex items-center gap-2 border border-rose-200 bg-rose-50 text-rose-800 px-4 py-3 rounded-lg text-sm">
          <AlertTriangle size={18} />
          <span>{runData.error_message}</span>
        </div>
      )}

      <div className="grid grid-cols-3 gap-6 flex-1 min-h-0">
        {/* Messages Panel */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 flex flex-col overflow-hidden">
          <div className="bg-slate-50 border-b border-slate-200 p-3 font-semibold flex items-center space-x-2 text-slate-700">
            <MessageSquare size={18} />
            <span>Agent Messages</span>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {messages.length === 0 && <div className="text-slate-400 text-center mt-10">{UI_MESSAGES.NO_MESSAGES}</div>}
            {messages.map((msg, idx) => (
              <div key={idx} className="bg-indigo-50 border border-indigo-100 p-3 rounded-lg text-sm">
                <div className="font-bold text-indigo-700 mb-1">{msg.agent_id || msg.payload?.agent_id || msg.from_agent_id || "Agent"}</div>
                <div className="text-slate-800 whitespace-pre-wrap">{msg.content || msg.payload?.content}</div>
              </div>
            ))}
            {runData?.output_json && (
               <div className="bg-green-50 border border-green-200 p-3 rounded-lg text-sm">
                <div className="font-bold text-green-800 mb-1">Final Output</div>
                <div className="text-slate-800 whitespace-pre-wrap">{parseOutput(runData.output_json)}</div>
              </div>
            )}
          </div>
        </div>

        {/* Tool Calls Panel */}
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 flex flex-col overflow-hidden">
          <div className="bg-slate-50 border-b border-slate-200 p-3 font-semibold flex items-center space-x-2 text-slate-700">
            <Wrench size={18} />
            <span>Tool Calls</span>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
             {toolCalls.length === 0 && <div className="text-slate-400 text-center mt-10">{UI_MESSAGES.NO_TOOL_CALLS}</div>}
             {toolCalls.map((tool, idx) => (
              <div key={idx} className={`${tool.status === WORKFLOW_RUN_STATUS.FAILED || tool.event_type === WS_EVENTS.TOOL_CALL_FAILED ? 'bg-rose-50 border-rose-200' : 'bg-amber-50 border-amber-100'} border p-3 rounded-lg text-sm font-mono`}>
                <div className={`${tool.status === WORKFLOW_RUN_STATUS.FAILED || tool.event_type === WS_EVENTS.TOOL_CALL_FAILED ? 'text-rose-700' : 'text-amber-700'} font-bold mb-1`}>
                  {tool.event_type || tool.status || 'TOOL_CALL'} - {tool.tool_name || tool.payload?.tool_name}
                </div>
                {(tool.error_message || tool.payload?.error) && (
                  <div className="text-rose-700 mb-2">Error: {tool.error_message || tool.payload?.error}</div>
                )}
                <div className="text-slate-800 break-words">{JSON.stringify(tool.payload || tool, null, 2)}</div>
              </div>
            ))}
          </div>
        </div>

        {/* Live Logs Panel */}
        <div className="bg-slate-900 rounded-xl shadow-sm flex flex-col overflow-hidden">
          <div className="bg-slate-950 border-b border-slate-800 p-3 font-semibold flex items-center space-x-2 text-slate-300">
            <Terminal size={18} />
            <span>Execution Logs</span>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-2 font-mono text-xs">
             {tokenUsage.length === 0 && logs.length === 0 && <div className="text-slate-600 text-center mt-10">{UI_MESSAGES.NO_TOKEN_USAGE}</div>}
             {logs.length === 0 && tokenUsage.length > 0 && <div className="text-slate-600 text-center mt-10">Waiting for events...</div>}
             {logs.map((log, idx) => (
              <div key={idx} className="text-slate-300">
                <span className="text-slate-500">[{new Date(log.timestamp || log.created_at).toLocaleTimeString()}]</span>{' '}
                <span className="text-emerald-400">{log.event_type}</span>{' '}
                <span>{log.message}</span>
              </div>
            ))}
          </div>
        </div>
      </div>
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <div className="bg-slate-50 border-b border-slate-200 p-3 font-semibold flex items-center space-x-2 text-slate-700">
          <Coins size={18} />
          <span>Token Usage</span>
        </div>
        {tokenUsage.length === 0 ? (
          <div className="p-6 text-center text-slate-400">{UI_MESSAGES.NO_TOKEN_USAGE}</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm text-left">
              <thead className="bg-slate-50 text-slate-600">
                <tr>
                  <th className="p-3">Agent</th>
                  <th className="p-3">Model</th>
                  <th className="p-3">Prompt tokens</th>
                  <th className="p-3">Completion tokens</th>
                  <th className="p-3">Total tokens</th>
                  <th className="p-3">Estimated cost</th>
                </tr>
              </thead>
              <tbody>
                {tokenUsage.map((usage, idx) => (
                  <tr key={idx} className="border-t border-slate-100">
                    <td className="p-3 font-mono text-slate-700">{usage.agent_id || "Agent"}</td>
                    <td className="p-3 font-mono text-slate-700">{usage.model || "unknown"}</td>
                    <td className="p-3">{usage.prompt_tokens || 0}</td>
                    <td className="p-3">{usage.completion_tokens || 0}</td>
                    <td className="p-3 font-semibold">{usage.total_tokens || 0}</td>
                    <td className="p-3">${Number(usage.estimated_cost || 0).toFixed(6)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
};

export default RunMonitor;

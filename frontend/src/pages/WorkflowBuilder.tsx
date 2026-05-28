import { useState, useCallback, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  ReactFlow,
  MiniMap,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  addEdge,
  type Node,
  type Edge
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import { GitBranch, Pencil, Play, Plus, RefreshCcw, Save, Wrench } from 'lucide-react';
import { createRun, getAgents, getWorkflowGraph, updateWorkflowGraph, updateWorkflow } from '../api/client';
import ToolConfigForm from '../components/ToolConfigForm';
import { APP_ROUTES } from '../constants/appRoutes';
import { UI_MESSAGES } from '../constants/messages';
import { UI_LABELS } from '../constants/ui';
import { DEFAULT_TOOL_CONFIGS, TOOL_NAMES, TOOL_OPTIONS } from '../constants/tools';
import { EDGE_CONDITION_TYPES, WORKFLOW_NODE_TYPES } from '../constants/workflow';

const flowTypeForNode = (nodeType: string) => {
  if (nodeType === WORKFLOW_NODE_TYPES.START) return 'input';
  if (nodeType === WORKFLOW_NODE_TYPES.END) return 'output';
  return 'default';
};

const nodeTypeFromFlow = (node: Node) => {
  if (node.data.node_type) return String(node.data.node_type);
  if (node.type === 'input') return WORKFLOW_NODE_TYPES.START;
  if (node.type === 'output') return WORKFLOW_NODE_TYPES.END;
  return WORKFLOW_NODE_TYPES.AGENT;
};

const defaultToolConfig = (toolName: string) => {
  const config = DEFAULT_TOOL_CONFIGS[toolName as keyof typeof DEFAULT_TOOL_CONFIGS] || {};
  return JSON.stringify(config, null, 2);
};

const parseToolConfig = (configJson: string) => {
  try {
    const parsed = JSON.parse(configJson || "{}");
    return parsed && typeof parsed === "object" ? parsed : {};
  } catch {
    return {};
  }
};

export default function WorkflowBuilder() {
  const { workflowId } = useParams<{ workflowId: string }>();
  const navigate = useNavigate();

  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [workflow, setWorkflow] = useState<any>(null);
  const [agents, setAgents] = useState<any[]>([]);
  const [runInput, setRunInput] = useState("");
  const [toolPanelOpen, setToolPanelOpen] = useState(false);
  const [editingToolNodeId, setEditingToolNodeId] = useState<string | null>(null);
  const [advancedToolJson, setAdvancedToolJson] = useState(false);
  const [toolForm, setToolForm] = useState<{ tool_name: string; config_json: string }>({
    tool_name: TOOL_NAMES.DUCKDUCKGO_SEARCH,
    config_json: defaultToolConfig(TOOL_NAMES.DUCKDUCKGO_SEARCH),
  });
  const [agentPanelOpen, setAgentPanelOpen] = useState(false);
  const [editingAgentNodeId, setEditingAgentNodeId] = useState<string | null>(null);
  const [selectedAgentId, setSelectedAgentId] = useState("");
  const [conditionPanelOpen, setConditionPanelOpen] = useState(false);
  const [editingEdgeId, setEditingEdgeId] = useState<string | null>(null);
  const [conditionForm, setConditionForm] = useState<{ condition_type: string; condition_expression: string }>({
    condition_type: EDGE_CONDITION_TYPES.ALWAYS,
    condition_expression: "",
  });
  const [toolConfigError, setToolConfigError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [workflowLoaded, setWorkflowLoaded] = useState(false);
  const [isEditingName, setIsEditingName] = useState(false);
  const [editedName, setEditedName] = useState('');
  const [isSavingMeta, setIsSavingMeta] = useState(false);

  const loadWorkflow = useCallback(async () => {
    if (!workflowId) {
      setError(UI_MESSAGES.WORKFLOW_LOAD_FAILED);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);
    setWorkflowLoaded(false);

    try {
      const data = await getWorkflowGraph(workflowId);
      setWorkflow(data.workflow);
      const mappedNodes = data.nodes.map((n: any) => ({
        id: n.id,
        type: flowTypeForNode(n.node_type),
        position: n.position || { x: 0, y: 0 },
        data: {
          label: n.node_type === WORKFLOW_NODE_TYPES.TOOL ? `Tool: ${n.tool_name || TOOL_NAMES.DUCKDUCKGO_SEARCH}` : n.agent_id || n.node_type,
          ...n
        }
      }));
      // Seed a START node for new/empty workflows so the user has a starting point
      if (mappedNodes.length === 0) {
        mappedNodes.push({
          id: `start-${Date.now()}`,
          type: flowTypeForNode(WORKFLOW_NODE_TYPES.START),
          position: { x: 250, y: 150 },
          data: {
            node_type: WORKFLOW_NODE_TYPES.START,
            config_json: "{}",
            label: WORKFLOW_NODE_TYPES.START,
          },
        });
      }
      setNodes(mappedNodes);
      setEdges(data.edges.map((e: any) => ({
        id: e.id,
        source: e.source_node_id,
        target: e.target_node_id,
        label: e.condition_type || EDGE_CONDITION_TYPES.ALWAYS,
        data: {
          condition_type: e.condition_type || EDGE_CONDITION_TYPES.ALWAYS,
          condition_expression: e.condition_expression
        }
      })));
      setWorkflowLoaded(true);
    } catch (err) {
      console.error(UI_MESSAGES.WORKFLOW_LOAD_FAILED, err);
      setError(UI_MESSAGES.WORKFLOW_LOAD_FAILED);
      setNodes([]);
      setEdges([]);
    } finally {
      setIsLoading(false);
    }
  }, [workflowId, setNodes, setEdges]);

  useEffect(() => {
    loadWorkflow();
  }, [loadWorkflow]);

  const handleSaveMeta = async () => {
    if (!workflowId || !editedName.trim()) return;
    setIsSavingMeta(true);
    try {
      await updateWorkflow(workflowId, {
        name: editedName.trim(),
        description: workflow?.description || null,
      });
      setWorkflow((prev: any) => ({ ...prev, name: editedName.trim() }));
      setIsEditingName(false);
    } catch {
      alert('Failed to save workflow name.');
    } finally {
      setIsSavingMeta(false);
    }
  };

  useEffect(() => {
    getAgents().then(setAgents).catch(() => setAgents([]));
  }, []);

  const onConnect = useCallback((params: any) => setEdges((eds) => addEdge({
    ...params,
    label: EDGE_CONDITION_TYPES.ALWAYS,
    data: { condition_type: EDGE_CONDITION_TYPES.ALWAYS }
  }, eds)), [setEdges]);

  const addNode = (nodeType: string) => {
    const id = `${nodeType.toLowerCase()}-${Date.now()}`;
    const nodeData: Record<string, any> = {
      node_type: nodeType,
      config_json: "{}",
      label: nodeType
    };
    setNodes((current) => [
      ...current,
      {
        id,
        type: flowTypeForNode(nodeType),
        position: { x: 120 + current.length * 40, y: 120 + current.length * 30 },
        data: nodeData
      }
    ]);
  };

  const agentLabel = (agentId: string) => {
    const agent = agents.find(item => item.id === agentId);
    return agent ? `Agent: ${agent.name}` : agentId || WORKFLOW_NODE_TYPES.AGENT;
  };

  const openAddAgentPanel = () => {
    setEditingAgentNodeId(null);
    setSelectedAgentId(agents[0]?.id || "");
    setAgentPanelOpen(true);
  };

  const openEditAgentPanel = (node: Node) => {
    setEditingAgentNodeId(node.id);
    setSelectedAgentId(String(node.data.agent_id || ""));
    setAgentPanelOpen(true);
  };

  const saveAgentNode = () => {
    if (!selectedAgentId) return;
    if (editingAgentNodeId) {
      setNodes(current => current.map(node => node.id === editingAgentNodeId ? {
        ...node,
        data: {
          ...node.data,
          node_type: WORKFLOW_NODE_TYPES.AGENT,
          agent_id: selectedAgentId,
          label: agentLabel(selectedAgentId),
        },
      } : node));
    } else {
      const id = `${WORKFLOW_NODE_TYPES.AGENT.toLowerCase()}-${Date.now()}`;
      setNodes(current => [
        ...current,
        {
          id,
          type: flowTypeForNode(WORKFLOW_NODE_TYPES.AGENT),
          position: { x: 120 + current.length * 40, y: 120 + current.length * 30 },
          data: {
            node_type: WORKFLOW_NODE_TYPES.AGENT,
            agent_id: selectedAgentId,
            config_json: "{}",
            label: agentLabel(selectedAgentId),
          },
        },
      ]);
    }
    setAgentPanelOpen(false);
    setEditingAgentNodeId(null);
  };

  const openConditionPanel = (edge: Edge) => {
    const edgeData = edge.data as any;
    setEditingEdgeId(edge.id);
    setConditionForm({
      condition_type: String(edgeData?.condition_type || edge.label || EDGE_CONDITION_TYPES.ALWAYS),
      condition_expression: String(edgeData?.condition_expression || ""),
    });
    setConditionPanelOpen(true);
  };

  const saveCondition = () => {
    if (!editingEdgeId) return;
    setEdges(current => current.map(edge => edge.id === editingEdgeId ? {
      ...edge,
      label: conditionForm.condition_type === EDGE_CONDITION_TYPES.EXPRESSION ? conditionForm.condition_expression || EDGE_CONDITION_TYPES.EXPRESSION : conditionForm.condition_type,
      data: {
        ...(edge.data as any),
        condition_type: conditionForm.condition_type,
        condition_expression: conditionForm.condition_expression,
      },
    } : edge));
    setConditionPanelOpen(false);
    setEditingEdgeId(null);
  };

  const openAddToolPanel = () => {
    setEditingToolNodeId(null);
    setToolForm({
      tool_name: TOOL_NAMES.DUCKDUCKGO_SEARCH,
      config_json: defaultToolConfig(TOOL_NAMES.DUCKDUCKGO_SEARCH),
    });
    setToolConfigError(null);
    setAdvancedToolJson(false);
    setToolPanelOpen(true);
  };

  const openEditToolPanel = (node: Node) => {
    setEditingToolNodeId(node.id);
    const toolName = String(node.data.tool_name || TOOL_NAMES.DUCKDUCKGO_SEARCH);
    setToolForm({
      tool_name: toolName,
      config_json: String(node.data.config_json || defaultToolConfig(toolName)),
    });
    setToolConfigError(null);
    setAdvancedToolJson(false);
    setToolPanelOpen(true);
  };

  const handleToolNameChange = (toolName: string) => {
    setToolForm({
      tool_name: toolName,
      config_json: defaultToolConfig(toolName),
    });
    setToolConfigError(null);
    setAdvancedToolJson(false);
  };

  const updateToolConfig = (config: Record<string, any>) => {
    setToolForm({ ...toolForm, config_json: JSON.stringify(config, null, 2) });
    setToolConfigError(null);
  };

  const saveToolNode = () => {
    try {
      JSON.parse(toolForm.config_json || "{}");
    } catch {
      setToolConfigError("Tool config must be valid JSON.");
      return;
    }

    if (editingToolNodeId) {
      setNodes((current) => current.map((node) => {
        if (node.id !== editingToolNodeId) return node;
        return {
          ...node,
          data: {
            ...node.data,
            node_type: WORKFLOW_NODE_TYPES.TOOL,
            tool_name: toolForm.tool_name,
            config_json: toolForm.config_json,
            label: `Tool: ${toolForm.tool_name}`,
          },
        };
      }));
    } else {
      const id = `${WORKFLOW_NODE_TYPES.TOOL.toLowerCase()}-${Date.now()}`;
      setNodes((current) => [
        ...current,
        {
          id,
          type: flowTypeForNode(WORKFLOW_NODE_TYPES.TOOL),
          position: { x: 120 + current.length * 40, y: 120 + current.length * 30 },
          data: {
            node_type: WORKFLOW_NODE_TYPES.TOOL,
            tool_name: toolForm.tool_name,
            config_json: toolForm.config_json,
            label: `Tool: ${toolForm.tool_name}`,
          },
        },
      ]);
    }

    setToolPanelOpen(false);
    setEditingToolNodeId(null);
    setToolConfigError(null);
  };

  const canSave = workflowLoaded && !isLoading && !isSaving && !error;
  const canRun =
    workflowLoaded &&
    !isLoading &&
    !isRunning &&
    !error &&
    nodes.length > 0 &&
    runInput.trim().length > 0;

  const handleSave = async () => {
    if (!workflowId || !canSave) return;
    setIsSaving(true);
    setError(null);

    const payload = {
      nodes: nodes.map(n => ({
        id: n.id,
        node_type: nodeTypeFromFlow(n),
        agent_id: n.data.agent_id,
        tool_name: n.data.tool_name,
        config_json: n.data.config_json || n.data.config || "{}",
        position: n.position
      })),
      edges: edges.map(e => {
        const edgeData = e.data as any;
        return {
          id: e.id,
          source_node_id: e.source,
          target_node_id: e.target,
          condition_type: edgeData?.condition_type || e.label || EDGE_CONDITION_TYPES.ALWAYS,
          condition_expression: edgeData?.condition_expression
        };
      })
    };

    try {
      await updateWorkflowGraph(workflowId, payload);
      alert(UI_MESSAGES.WORKFLOW_SAVE_SUCCESS);
    } catch (err) {
      console.error(UI_MESSAGES.WORKFLOW_SAVE_FAILED, err);
      setError(UI_MESSAGES.WORKFLOW_SAVE_FAILED);
    } finally {
      setIsSaving(false);
    }
  };

  const handleRun = async () => {
    if (!workflowId) return;
    if (!runInput.trim()) {
      setError(UI_MESSAGES.WORKFLOW_RUN_INPUT_REQUIRED);
      return;
    }
    if (nodes.length === 0) {
      setError(UI_MESSAGES.WORKFLOW_RUN_GRAPH_REQUIRED);
      return;
    }
    if (!canRun) return;

    setIsRunning(true);
    setError(null);
    try {
      const run = await createRun(workflowId, {
        message: runInput.trim(),
        source: "web"
      });
      if (!run?.run_id) throw new Error("Missing run_id");
      navigate(APP_ROUTES.RUN_MONITOR(run.run_id));
    } catch (err) {
      console.error(UI_MESSAGES.WORKFLOW_RUN_FAILED, err);
      setError(UI_MESSAGES.WORKFLOW_RUN_FAILED);
    } finally {
      setIsRunning(false);
    }
  };

  return (
    <div className="h-full flex flex-col space-y-4">
      <div className="flex justify-between items-start gap-4">
        <div>
          {isEditingName ? (
            <div className="flex items-center gap-2">
              <input
                value={editedName}
                onChange={e => setEditedName(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') handleSaveMeta(); if (e.key === 'Escape') setIsEditingName(false); }}
                className="text-2xl font-bold border-b-2 border-indigo-500 focus:outline-none bg-transparent text-slate-900"
                autoFocus
              />
              <button
                onClick={handleSaveMeta}
                disabled={isSavingMeta}
                className="text-sm text-indigo-600 font-medium hover:text-indigo-800 disabled:opacity-50"
              >
                {isSavingMeta ? 'Saving...' : 'Save'}
              </button>
              <button onClick={() => setIsEditingName(false)} className="text-sm text-slate-500 hover:text-slate-700">
                Cancel
              </button>
            </div>
          ) : (
            <h1
              className="text-3xl font-bold text-slate-900 cursor-pointer hover:text-indigo-700 transition-colors group flex items-center gap-2"
              title="Click to rename"
              onClick={() => {
                if (workflow && !isLoading) {
                  setEditedName(workflow.name || '');
                  setIsEditingName(true);
                }
              }}
            >
              Workflow Builder: {isLoading ? 'Loading...' : workflow?.name || 'Untitled workflow'}
              {!isLoading && workflow && (
                <Pencil size={16} className="opacity-0 group-hover:opacity-50 transition-opacity" />
              )}
            </h1>
          )}
          {error && (
            <div className="mt-2 flex items-center gap-3 text-sm text-rose-700">
              <span>{error}</span>
              <button onClick={loadWorkflow} className="inline-flex items-center gap-1 text-rose-800 underline">
                <RefreshCcw size={14} />
                {UI_LABELS.RETRY}
              </button>
            </div>
          )}
        </div>
        <div className="flex flex-wrap justify-end gap-3 items-center">
          <input
            type="text"
            placeholder="Workflow run input"
            className="border border-slate-200 rounded-lg px-3 py-2 text-sm disabled:bg-slate-100 disabled:text-slate-400 min-w-[320px]"
            value={runInput}
            disabled={isLoading || !!error || isRunning}
            onChange={e => setRunInput(e.target.value)}
          />
          <button disabled={!canSave} onClick={handleSave} className="flex items-center space-x-2 bg-white border border-slate-200 text-slate-700 px-4 py-2 rounded-lg hover:bg-slate-50 disabled:opacity-50 disabled:cursor-not-allowed">
            <Save size={18} />
            <span>{isSaving ? UI_LABELS.SAVING : UI_LABELS.SAVE}</span>
          </button>
          <button disabled={!canRun} onClick={handleRun} className="flex items-center space-x-2 bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed">
            <Play size={18} />
            <span>{isRunning ? UI_LABELS.RUNNING : UI_LABELS.RUN}</span>
          </button>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-slate-200 p-3 flex flex-wrap gap-3 items-center">
        <span className="text-sm font-semibold text-slate-700 flex items-center gap-2">
          <GitBranch size={16} />
          Add node
        </span>
        <button disabled={!workflowLoaded || isLoading || !!error || agents.length === 0} onClick={openAddAgentPanel} className="px-3 py-2 rounded-lg border border-slate-200 text-sm disabled:opacity-50">
          <Plus size={14} className="inline mr-1" /> Agent
        </button>
        <button disabled={!workflowLoaded || isLoading || !!error} onClick={openAddToolPanel} className="px-3 py-2 rounded-lg border border-slate-200 text-sm disabled:opacity-50">
          <Wrench size={14} className="inline mr-1" /> Tool
        </button>
        <button disabled={!workflowLoaded || isLoading || !!error} onClick={() => addNode(WORKFLOW_NODE_TYPES.CONDITION)} className="px-3 py-2 rounded-lg border border-slate-200 text-sm disabled:opacity-50">
          <Plus size={14} className="inline mr-1" /> Condition
        </button>
        <button disabled={!workflowLoaded || isLoading || !!error} onClick={() => addNode(WORKFLOW_NODE_TYPES.END)} className="px-3 py-2 rounded-lg border border-slate-200 text-sm disabled:opacity-50">
          <Plus size={14} className="inline mr-1" /> End
        </button>
      </div>

      <div className="flex-1 bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden relative">
        {isLoading && (
          <div className="absolute inset-0 z-10 bg-white/80 flex items-center justify-center">
            <div className="text-slate-500">{UI_MESSAGES.WORKFLOW_LOADING}</div>
          </div>
        )}
        {!isLoading && !error && nodes.length === 0 && (
          <div className="absolute inset-0 z-10 pointer-events-none flex items-center justify-center">
            <div className="text-slate-500 bg-slate-50 border border-dashed border-slate-200 rounded-lg px-6 py-4">
              {UI_MESSAGES.WORKFLOW_EMPTY}
            </div>
          </div>
        )}
        {!isLoading && error && (
          <div className="absolute inset-0 z-10 bg-white flex items-center justify-center">
            <div className="text-center space-y-3">
              <div className="text-rose-700 font-medium">{error}</div>
              {workflowId && (
                <button onClick={loadWorkflow} className="px-4 py-2 bg-rose-600 text-white rounded-lg">
                  {UI_LABELS.RETRY}
                </button>
              )}
              <div>
                <button
                  onClick={() => navigate(APP_ROUTES.WORKFLOWS)}
                  className="text-sm text-indigo-600 underline hover:text-indigo-800"
                >
                  ← Back to Workflows list
                </button>
              </div>
            </div>
          </div>
        )}
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={isLoading || !!error ? undefined : onNodesChange}
          onEdgesChange={isLoading || !!error ? undefined : onEdgesChange}
          onConnect={isLoading || !!error ? undefined : onConnect}
          onNodeClick={(_, node) => {
            if (node.data.node_type === WORKFLOW_NODE_TYPES.TOOL) openEditToolPanel(node);
            if (node.data.node_type === WORKFLOW_NODE_TYPES.AGENT) openEditAgentPanel(node);
          }}
          onEdgeClick={(_, edge) => openConditionPanel(edge)}
          nodesDraggable={!isLoading && !error}
          nodesConnectable={!isLoading && !error}
          elementsSelectable={!isLoading && !error}
          fitView
        >
          <Controls />
          <MiniMap />
          <Background gap={12} size={1} />
        </ReactFlow>
      </div>
      {toolPanelOpen && (
        <div className="fixed inset-0 bg-slate-900/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 w-full max-w-xl">
            <div className="border-b border-slate-200 px-5 py-4">
              <h2 className="text-lg font-semibold text-slate-900">{editingToolNodeId ? "Edit Tool Node" : "Add Tool Node"}</h2>
            </div>
            <div className="p-5 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Tool type</label>
                <select value={toolForm.tool_name} onChange={e => handleToolNameChange(e.target.value)} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm">
                  {TOOL_OPTIONS.map(tool => <option key={tool.value} value={tool.value}>{tool.label}</option>)}
                </select>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-slate-700">Configuration</span>
                <label className="flex items-center gap-2 text-sm text-slate-600">
                  <input type="checkbox" checked={advancedToolJson} onChange={event => setAdvancedToolJson(event.target.checked)} />
                  Advanced JSON
                </label>
              </div>
              {!advancedToolJson && (
                <ToolConfigForm
                  toolName={toolForm.tool_name}
                  config={parseToolConfig(toolForm.config_json)}
                  onChange={updateToolConfig}
                />
              )}
              <div>
                <div className="flex justify-between items-center mb-1">
                  <label className="block text-sm font-medium text-slate-700">{advancedToolJson ? "Config JSON" : "Config JSON preview"}</label>
                  <button 
                    onClick={() => {
                      try {
                        const parsed = JSON.parse(toolForm.config_json);
                        setToolForm({ ...toolForm, config_json: JSON.stringify(parsed, null, 2) });
                        setToolConfigError(null);
                      } catch {
                        setToolConfigError("Cannot format invalid JSON.");
                      }
                    }}
                    className="text-xs text-indigo-600 hover:text-indigo-800"
                  >
                    Format JSON
                  </button>
                </div>
                <textarea
                  value={toolForm.config_json}
                  onChange={e => {
                    setToolForm({ ...toolForm, config_json: e.target.value });
                    setToolConfigError(null);
                  }}
                  className="w-full min-h-28 border border-slate-300 rounded-lg px-3 py-2 font-mono text-sm"
                />
              </div>
              {toolConfigError && <div className="text-sm text-rose-700 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2">{toolConfigError}</div>}
            </div>
            <div className="border-t border-slate-200 px-5 py-4 flex justify-end gap-3">
              <button onClick={() => setToolPanelOpen(false)} className="px-4 py-2 rounded-lg bg-slate-100 text-slate-700 hover:bg-slate-200">
                Cancel
              </button>
              <button onClick={saveToolNode} className="px-4 py-2 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700">
                {editingToolNodeId ? "Save changes" : "Add"}
              </button>
            </div>
          </div>
        </div>
      )}
      {agentPanelOpen && (
        <div className="fixed inset-0 bg-slate-900/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 w-full max-w-md">
            <div className="border-b border-slate-200 px-5 py-4">
              <h2 className="text-lg font-semibold text-slate-900">{editingAgentNodeId ? "Edit Agent Node" : "Add Agent Node"}</h2>
            </div>
            <div className="p-5">
              <label className="block text-sm font-medium text-slate-700 mb-1">Agent</label>
              <select value={selectedAgentId} onChange={event => setSelectedAgentId(event.target.value)} className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm">
                <option value="">Select an agent</option>
                {agents.map(agent => <option key={agent.id} value={agent.id}>{agent.name} ({agent.role})</option>)}
              </select>
            </div>
            <div className="border-t border-slate-200 px-5 py-4 flex justify-end gap-3">
              <button onClick={() => setAgentPanelOpen(false)} className="px-4 py-2 rounded-lg bg-slate-100 text-slate-700 hover:bg-slate-200">
                Cancel
              </button>
              <button disabled={!selectedAgentId} onClick={saveAgentNode} className="px-4 py-2 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 disabled:opacity-50">
                {editingAgentNodeId ? "Save changes" : "Add"}
              </button>
            </div>
          </div>
        </div>
      )}
      {conditionPanelOpen && (
        <div className="fixed inset-0 bg-slate-900/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 w-full max-w-md">
            <div className="border-b border-slate-200 px-5 py-4">
              <h2 className="text-lg font-semibold text-slate-900">Edit Condition</h2>
            </div>
            <div className="p-5 space-y-4">
              <label className="block text-sm font-medium text-slate-700">
                Condition type
                <select value={conditionForm.condition_type} onChange={event => setConditionForm({ ...conditionForm, condition_type: event.target.value })} className="mt-1 w-full border border-slate-300 rounded-lg px-3 py-2 text-sm">
                  <option value={EDGE_CONDITION_TYPES.ALWAYS}>Always</option>
                  <option value={EDGE_CONDITION_TYPES.APPROVED}>Approved</option>
                  <option value={EDGE_CONDITION_TYPES.REJECTED}>Rejected</option>
                  <option value={EDGE_CONDITION_TYPES.RESOLVED}>Resolved</option>
                  <option value={EDGE_CONDITION_TYPES.ESCALATE}>Escalate</option>
                  <option value={EDGE_CONDITION_TYPES.EXPRESSION}>Expression</option>
                </select>
              </label>
              {conditionForm.condition_type === EDGE_CONDITION_TYPES.EXPRESSION && (
                <label className="block text-sm font-medium text-slate-700">
                  Condition expression
                  <input value={conditionForm.condition_expression} onChange={event => setConditionForm({ ...conditionForm, condition_expression: event.target.value })} className="mt-1 w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" />
                </label>
              )}
            </div>
            <div className="border-t border-slate-200 px-5 py-4 flex justify-end gap-3">
              <button onClick={() => setConditionPanelOpen(false)} className="px-4 py-2 rounded-lg bg-slate-100 text-slate-700 hover:bg-slate-200">
                Cancel
              </button>
              <button onClick={saveCondition} className="px-4 py-2 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700">
                Save changes
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

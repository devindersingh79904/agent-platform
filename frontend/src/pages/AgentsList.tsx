import { useEffect, useState } from 'react';
import { 
  getAgents, 
  createAgent, 
  updateAgent, 
  deleteAgent, 
  getMetadataModels, 
  getMetadataTools, 
  getMetadataChannels 
} from '../api/client';
import { Trash2, Edit2, Plus, X } from 'lucide-react';
import { UI_MESSAGES } from '../constants/messages';
import { UI_LABELS } from '../constants/ui';

const AgentsList = () => {
  const [agents, setAgents] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState(false);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingAgent, setEditingAgent] = useState<any>(null);

  // Metadata states
  const [metaModels, setMetaModels] = useState<any[]>([]);
  const [metaTools, setMetaTools] = useState<any[]>([]);
  const [metaChannels, setMetaChannels] = useState<any[]>([]);
  const [advancedMode, setAdvancedMode] = useState<boolean>(false);

  const defaultAgent = {
    name: "",
    description: "",
    role: "assistant",
    system_prompt: "",
    model: "gpt-4o-mini",
    tools_json: "[]",
    memory_enabled: true,
    guardrails_json: "{}",
    limits_json: "{}",
    schedule_config_json: "{}",
    channel_config_json: "{}"
  };

  const [formData, setFormData] = useState<any>(defaultAgent);

  const [structuredConfig, setStructuredConfig] = useState<any>({
    tools: [] as string[],
    channels: [] as string[],
    guardrails: {
      allowed_tools: [] as string[],
      blocked_keywords: "",
      max_tool_calls: "",
      max_tokens: "",
      max_estimated_cost: "",
      require_review_before_final: false
    },
    limits: {
      max_iterations: "",
      timeout_sec: "",
      max_cost: "",
      max_tokens: ""
    },
    schedule: {
      enabled: false,
      cron_expression: "",
      timezone: "UTC"
    }
  });

  const populateStructuredConfig = (agentData: any) => {
    let tools: string[] = [];
    try {
      tools = JSON.parse(agentData.tools_json || "[]");
    } catch {}

    let channels: string[] = [];
    try {
      const parsedChannels = JSON.parse(agentData.channel_config_json || "{}");
      channels = Object.keys(parsedChannels).filter(key => parsedChannels[key]?.enabled);
    } catch {}

    let guardrails = {
      allowed_tools: [] as string[],
      blocked_keywords: "",
      max_tool_calls: "",
      max_tokens: "",
      max_estimated_cost: "",
      require_review_before_final: false
    };
    try {
      const parsedGr = JSON.parse(agentData.guardrails_json || "{}");
      guardrails.allowed_tools = parsedGr.allowed_tools || [];
      guardrails.blocked_keywords = (parsedGr.blocked_keywords || parsedGr.banned_keywords || []).join(", ");
      guardrails.max_tool_calls = parsedGr.max_tool_calls !== undefined ? String(parsedGr.max_tool_calls) : "";
      guardrails.max_tokens = parsedGr.max_tokens !== undefined ? String(parsedGr.max_tokens) : "";
      guardrails.max_estimated_cost = parsedGr.max_estimated_cost !== undefined ? String(parsedGr.max_estimated_cost) : "";
      guardrails.require_review_before_final = !!parsedGr.require_review_before_final;
    } catch {}

    let limits = {
      max_iterations: "",
      timeout_sec: "",
      max_cost: "",
      max_tokens: ""
    };
    try {
      const parsedLim = JSON.parse(agentData.limits_json || "{}");
      limits.max_iterations = parsedLim.max_iterations !== undefined ? String(parsedLim.max_iterations) : "";
      limits.timeout_sec = parsedLim.timeout_sec !== undefined ? String(parsedLim.timeout_sec) : "";
      limits.max_cost = parsedLim.max_cost !== undefined ? String(parsedLim.max_cost) : "";
      limits.max_tokens = parsedLim.max_tokens !== undefined ? String(parsedLim.max_tokens) : "";
    } catch {}

    let schedule = {
      enabled: false,
      cron_expression: "",
      timezone: "UTC"
    };
    try {
      const parsedSch = JSON.parse(agentData.schedule_config_json || "{}");
      schedule.enabled = !!parsedSch.enabled;
      schedule.cron_expression = parsedSch.cron_expression || "";
      schedule.timezone = parsedSch.timezone || "UTC";
    } catch {}

    setStructuredConfig({
      tools,
      channels,
      guardrails,
      limits,
      schedule
    });
  };

  const syncStructuredToFormData = (struct: typeof structuredConfig, currentForm: any) => {
    const tools_json = JSON.stringify(struct.tools);

    const channel_config: any = {};
    metaChannels.forEach(c => {
      channel_config[c.name] = { enabled: struct.channels.includes(c.name) };
    });
    if (metaChannels.length === 0) {
      ["telegram", "web"].forEach(name => {
        channel_config[name] = { enabled: struct.channels.includes(name) };
      });
    }
    const channel_config_json = JSON.stringify(channel_config);

    const gr: any = {};
    if (struct.guardrails.allowed_tools && struct.guardrails.allowed_tools.length > 0) {
      gr.allowed_tools = struct.guardrails.allowed_tools;
    }
    const blocked_words = struct.guardrails.blocked_keywords
      .split(",")
      .map((w: string) => w.trim())
      .filter((w: string) => w.length > 0);
    if (blocked_words.length > 0) {
      gr.blocked_keywords = blocked_words;
    }
    if (struct.guardrails.max_tool_calls !== "") {
      gr.max_tool_calls = Number(struct.guardrails.max_tool_calls);
    }
    if (struct.guardrails.max_tokens !== "") {
      gr.max_tokens = Number(struct.guardrails.max_tokens);
    }
    if (struct.guardrails.max_estimated_cost !== "") {
      gr.max_estimated_cost = Number(struct.guardrails.max_estimated_cost);
    }
    if (struct.guardrails.require_review_before_final) {
      gr.require_review_before_final = true;
    }
    const guardrails_json = JSON.stringify(gr);

    const lim: any = {};
    if (struct.limits.max_iterations !== "") {
      lim.max_iterations = Number(struct.limits.max_iterations);
    }
    if (struct.limits.timeout_sec !== "") {
      lim.timeout_sec = Number(struct.limits.timeout_sec);
    }
    if (struct.limits.max_cost !== "") {
      lim.max_cost = Number(struct.limits.max_cost);
    }
    if (struct.limits.max_tokens !== "") {
      lim.max_tokens = Number(struct.limits.max_tokens);
    }
    const limits_json = JSON.stringify(lim);

    const sch: any = {};
    sch.enabled = struct.schedule.enabled;
    if (struct.schedule.cron_expression) {
      sch.cron_expression = struct.schedule.cron_expression;
    }
    if (struct.schedule.timezone) {
      sch.timezone = struct.schedule.timezone;
    }
    const schedule_config_json = JSON.stringify(sch);

    return {
      ...currentForm,
      tools_json,
      channel_config_json,
      guardrails_json,
      limits_json,
      schedule_config_json
    };
  };

  const isConfigJsonValid = () => {
    try {
      if (formData.tools_json) JSON.parse(formData.tools_json);
      if (formData.guardrails_json) JSON.parse(formData.guardrails_json);
      if (formData.limits_json) JSON.parse(formData.limits_json);
      if (formData.schedule_config_json) JSON.parse(formData.schedule_config_json);
      if (formData.channel_config_json) JSON.parse(formData.channel_config_json);
      return true;
    } catch {
      return false;
    }
  };

  useEffect(() => {
    loadAgents();
    loadMetadata();
  }, []);

  const loadAgents = () => {
    setLoading(true);
    setError(null);
    getAgents()
      .then(setAgents)
      .catch(err => {
        console.error(UI_MESSAGES.AGENTS_FETCH_FAILED, err);
        setError(UI_MESSAGES.AGENTS_FETCH_FAILED);
      })
      .finally(() => setLoading(false));
  };

  const loadMetadata = async () => {
    try {
      const [modelsRes, toolsRes, channelsRes] = await Promise.all([
        getMetadataModels().catch(() => ({ models: [] })),
        getMetadataTools().catch(() => ({ tools: [] })),
        getMetadataChannels().catch(() => ({ channels: [] }))
      ]);
      setMetaModels(modelsRes.models || []);
      setMetaTools(toolsRes.tools || []);
      setMetaChannels(channelsRes.channels || []);
    } catch (err) {
      console.error("Failed to load metadata", err);
    }
  };

  const handleOpenModal = (agent?: any) => {
    if (agent) {
      setEditingAgent(agent);
      setFormData(agent);
      populateStructuredConfig(agent);
    } else {
      setEditingAgent(null);
      setFormData(defaultAgent);
      populateStructuredConfig(defaultAgent);
    }
    setAdvancedMode(false);
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditingAgent(null);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    
    let finalFormData = formData;
    if (!advancedMode) {
      finalFormData = syncStructuredToFormData(structuredConfig, formData);
    }

    try {
      if (finalFormData.tools_json) JSON.parse(finalFormData.tools_json);
      if (finalFormData.guardrails_json) JSON.parse(finalFormData.guardrails_json);
      if (finalFormData.limits_json) JSON.parse(finalFormData.limits_json);
      if (finalFormData.schedule_config_json) JSON.parse(finalFormData.schedule_config_json);
      if (finalFormData.channel_config_json) JSON.parse(finalFormData.channel_config_json);
    } catch {
      alert(UI_MESSAGES.AGENT_CONFIG_JSON_INVALID);
      return;
    }

    try {
      setIsSaving(true);
      if (editingAgent) {
        await updateAgent(editingAgent.id, finalFormData);
      } else {
        await createAgent(finalFormData);
      }
      handleCloseModal();
      loadAgents();
    } catch (err) {
      alert(UI_MESSAGES.AGENT_SAVE_FAILED);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async (id: string) => {
    if (window.confirm("Are you sure?")) {
      await deleteAgent(id);
      loadAgents();
    }
  };

  if (loading) return <div>Loading agents...</div>;

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-slate-900">Agents</h1>
        <button onClick={() => handleOpenModal()} className="flex items-center space-x-2 bg-indigo-600 text-white px-4 py-2 rounded-lg hover:bg-indigo-700">
          <Plus size={18} />
          <span>New Agent</span>
        </button>
      </div>
      {error && (
        <div className="bg-rose-50 border border-rose-200 rounded-lg p-4 text-rose-700 flex justify-between items-center">
          <span>{error}</span>
          <button onClick={loadAgents} className="underline">Retry</button>
        </div>
      )}

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <table className="w-full text-left">
          <thead className="bg-slate-50 border-b border-slate-200">
            <tr>
              <th className="p-4 font-semibold text-slate-600">Name</th>
              <th className="p-4 font-semibold text-slate-600">Role</th>
              <th className="p-4 font-semibold text-slate-600">Model</th>
              <th className="p-4 font-semibold text-slate-600">Created</th>
              <th className="p-4 font-semibold text-slate-600 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {agents.length === 0 ? (
              <tr>
                <td colSpan={5} className="p-8 text-center text-slate-500">No agents found. Create one to get started.</td>
              </tr>
            ) : (
              agents.map(agent => (
                <tr key={agent.id} className="border-b border-slate-100 hover:bg-slate-50">
                  <td className="p-4 font-medium text-slate-900">{agent.name}</td>
                  <td className="p-4 text-slate-600">{agent.role}</td>
                  <td className="p-4 text-slate-600">
                    <span className="bg-slate-100 text-slate-700 px-2 py-1 rounded text-xs font-mono">{agent.model}</span>
                  </td>
                  <td className="p-4 text-slate-500 text-sm">{new Date(agent.created_at).toLocaleDateString()}</td>
                  <td className="p-4 text-right space-x-2">
                    <button onClick={() => handleOpenModal(agent)} className="p-2 text-slate-400 hover:text-indigo-600 bg-white rounded-lg border border-slate-200 hover:border-indigo-200 shadow-sm transition-colors">
                      <Edit2 size={16} />
                    </button>
                    <button onClick={() => handleDelete(agent.id)} className="p-2 text-slate-400 hover:text-red-600 bg-white rounded-lg border border-slate-200 hover:border-red-200 shadow-sm transition-colors">
                      <Trash2 size={16} />
                    </button>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {isModalOpen && (
        <div className="fixed inset-0 bg-slate-900/50 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="flex justify-between items-center border-b border-slate-200 p-6">
              <h2 className="text-xl font-bold text-slate-900">{editingAgent ? "Edit Agent" : "Create Agent"}</h2>
              <div className="flex items-center space-x-4">
                <label className="flex items-center space-x-2 text-xs font-medium text-slate-500 cursor-pointer">
                  <input 
                    type="checkbox" 
                    checked={advancedMode} 
                    onChange={e => {
                      if (e.target.checked) {
                        const synced = syncStructuredToFormData(structuredConfig, formData);
                        setFormData(synced);
                      } else {
                        populateStructuredConfig(formData);
                      }
                      setAdvancedMode(e.target.checked);
                    }} 
                  />
                  <span>Advanced JSON Mode</span>
                </label>
                <button onClick={handleCloseModal} className="text-slate-400 hover:text-slate-600">
                  <X size={24} />
                </button>
              </div>
            </div>
            <form onSubmit={handleSave} className="p-6 space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Name</label>
                  <input required type="text" className="w-full border border-slate-300 rounded-lg px-3 py-2" value={formData.name} onChange={e => setFormData({...formData, name: e.target.value})} />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Role</label>
                  <input required type="text" className="w-full border border-slate-300 rounded-lg px-3 py-2" value={formData.role} onChange={e => setFormData({...formData, role: e.target.value})} />
                </div>
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
                  <input type="text" className="w-full border border-slate-300 rounded-lg px-3 py-2" value={formData.description} onChange={e => setFormData({...formData, description: e.target.value})} />
                </div>
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-slate-700 mb-1">System Prompt</label>
                  <textarea className="w-full border border-slate-300 rounded-lg px-3 py-2 h-24" value={formData.system_prompt} onChange={e => setFormData({...formData, system_prompt: e.target.value})} />
                </div>
                
                <div className="col-span-2">
                  <label className="block text-sm font-medium text-slate-700 mb-1">Model</label>
                  <select
                    required
                    className="w-full border border-slate-300 rounded-lg px-3 py-2"
                    value={formData.model}
                    onChange={e => setFormData({...formData, model: e.target.value})}
                  >
                    {metaModels.map(m => (
                      <option key={m.model} value={m.model}>{m.label}</option>
                    ))}
                    {metaModels.length === 0 && <option value="gpt-4o-mini">GPT-4o mini</option>}
                  </select>
                </div>

                {advancedMode ? (
                  <>
                    <div className="col-span-2">
                      <label className="block text-sm font-medium text-slate-700 mb-1">Tools (JSON array)</label>
                      <textarea className="w-full border border-slate-300 rounded-lg px-3 py-2 font-mono text-sm h-20" value={formData.tools_json} onChange={e => setFormData({...formData, tools_json: e.target.value})} />
                    </div>
                    <div className="col-span-2">
                      <label className="block text-sm font-medium text-slate-700 mb-1">Guardrails (JSON)</label>
                      <textarea className="w-full border border-slate-300 rounded-lg px-3 py-2 font-mono text-sm h-20" value={formData.guardrails_json} onChange={e => setFormData({...formData, guardrails_json: e.target.value})} />
                    </div>
                    <div className="col-span-2">
                      <label className="block text-sm font-medium text-slate-700 mb-1">Limits (JSON)</label>
                      <textarea className="w-full border border-slate-300 rounded-lg px-3 py-2 font-mono text-sm h-20" value={formData.limits_json} onChange={e => setFormData({...formData, limits_json: e.target.value})} />
                    </div>
                    <div className="col-span-2">
                      <label className="block text-sm font-medium text-slate-700 mb-1">Schedule Config (JSON)</label>
                      <textarea className="w-full border border-slate-300 rounded-lg px-3 py-2 font-mono text-sm h-20" value={formData.schedule_config_json} onChange={e => setFormData({...formData, schedule_config_json: e.target.value})} />
                    </div>
                    <div className="col-span-2">
                      <label className="block text-sm font-medium text-slate-700 mb-1">Channel Config (JSON)</label>
                      <textarea className="w-full border border-slate-300 rounded-lg px-3 py-2 font-mono text-sm h-20" value={formData.channel_config_json} onChange={e => setFormData({...formData, channel_config_json: e.target.value})} />
                    </div>
                  </>
                ) : (
                  <>
                    <div className="col-span-2 space-y-2">
                      <label className="block text-sm font-medium text-slate-700 mb-1">Tools</label>
                      <div className="grid grid-cols-2 gap-2 border border-slate-200 rounded-lg p-3 max-h-32 overflow-y-auto">
                        {metaTools.map(t => (
                          <label key={t.name} className="flex items-center space-x-2 text-sm text-slate-700 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={structuredConfig.tools.includes(t.name)}
                              onChange={e => {
                                const updated = e.target.checked
                                  ? [...structuredConfig.tools, t.name]
                                  : structuredConfig.tools.filter((name: string) => name !== t.name);
                                setStructuredConfig({ ...structuredConfig, tools: updated });
                              }}
                            />
                            <span>{t.label}</span>
                          </label>
                        ))}
                        {metaTools.length === 0 && <div className="text-slate-400 text-xs col-span-2">No tools available.</div>}
                      </div>
                    </div>

                    <div className="col-span-2 space-y-2">
                      <label className="block text-sm font-medium text-slate-700 mb-1">Channels</label>
                      <div className="flex space-x-4 border border-slate-200 rounded-lg p-3">
                        {metaChannels.map(c => (
                          <label key={c.name} className="flex items-center space-x-2 text-sm text-slate-700 cursor-pointer">
                            <input
                              type="checkbox"
                              checked={structuredConfig.channels.includes(c.name)}
                              onChange={e => {
                                const updated = e.target.checked
                                  ? [...structuredConfig.channels, c.name]
                                  : structuredConfig.channels.filter((name: string) => name !== c.name);
                                setStructuredConfig({ ...structuredConfig, channels: updated });
                              }}
                            />
                            <span>{c.label} {c.configured ? '(Configured)' : '(Not Configured)'}</span>
                          </label>
                        ))}
                        {metaChannels.length === 0 && <div className="text-slate-400 text-xs">No channels available.</div>}
                      </div>
                    </div>

                    <div className="col-span-2 border border-slate-200 rounded-lg p-4 space-y-4">
                      <h3 className="font-semibold text-slate-900 text-sm">Security & Guardrails</h3>
                      <div className="grid grid-cols-2 gap-4">
                        <div className="col-span-2">
                          <label className="block text-xs font-medium text-slate-500 mb-1">Allowed Tools (Leave empty for all)</label>
                          <div className="grid grid-cols-2 gap-2 border border-slate-100 rounded-lg p-2 max-h-24 overflow-y-auto bg-slate-50">
                            {structuredConfig.tools.map((tName: string) => (
                              <label key={tName} className="flex items-center space-x-2 text-xs text-slate-700 cursor-pointer">
                                <input
                                  type="checkbox"
                                  checked={structuredConfig.guardrails.allowed_tools.includes(tName)}
                                  onChange={e => {
                                    const updated = e.target.checked
                                      ? [...structuredConfig.guardrails.allowed_tools, tName]
                                      : structuredConfig.guardrails.allowed_tools.filter((n: string) => n !== tName);
                                    setStructuredConfig({
                                      ...structuredConfig,
                                      guardrails: { ...structuredConfig.guardrails, allowed_tools: updated }
                                    });
                                  }}
                                />
                                <span>{tName}</span>
                              </label>
                            ))}
                            {structuredConfig.tools.length === 0 && <div className="text-slate-400 text-xs col-span-2">Select tools for the agent first.</div>}
                          </div>
                        </div>
                        <div className="col-span-2">
                          <label className="block text-xs font-medium text-slate-500 mb-1">Blocked Keywords (comma separated)</label>
                          <input
                            type="text"
                            className="w-full border border-slate-300 rounded-lg px-3 py-1.5 text-sm"
                            value={structuredConfig.guardrails.blocked_keywords}
                            onChange={e => setStructuredConfig({
                              ...structuredConfig,
                              guardrails: { ...structuredConfig.guardrails, blocked_keywords: e.target.value }
                            })}
                            placeholder="spam, attack, password"
                          />
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-slate-500 mb-1">Max Tool Calls</label>
                          <input
                            type="number"
                            className="w-full border border-slate-300 rounded-lg px-3 py-1.5 text-sm"
                            value={structuredConfig.guardrails.max_tool_calls}
                            onChange={e => setStructuredConfig({
                              ...structuredConfig,
                              guardrails: { ...structuredConfig.guardrails, max_tool_calls: e.target.value }
                            })}
                          />
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-slate-500 mb-1">Max Estimated Cost ($)</label>
                          <input
                            type="number"
                            step="0.0001"
                            className="w-full border border-slate-300 rounded-lg px-3 py-1.5 text-sm"
                            value={structuredConfig.guardrails.max_estimated_cost}
                            onChange={e => setStructuredConfig({
                              ...structuredConfig,
                              guardrails: { ...structuredConfig.guardrails, max_estimated_cost: e.target.value }
                            })}
                          />
                        </div>
                        <div className="col-span-2 flex items-center space-x-2">
                          <input
                            id="require_review_before_final"
                            type="checkbox"
                            checked={structuredConfig.guardrails.require_review_before_final}
                            onChange={e => setStructuredConfig({
                              ...structuredConfig,
                              guardrails: { ...structuredConfig.guardrails, require_review_before_final: e.target.checked }
                            })}
                          />
                          <label htmlFor="require_review_before_final" className="text-xs font-medium text-slate-700 cursor-pointer">
                            Require human review before final response
                          </label>
                        </div>
                      </div>
                    </div>

                    <div className="col-span-2 border border-slate-200 rounded-lg p-4 space-y-4">
                      <h3 className="font-semibold text-slate-900 text-sm">Execution Limits</h3>
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <label className="block text-xs font-medium text-slate-500 mb-1">Max Iterations</label>
                          <input
                            type="number"
                            className="w-full border border-slate-300 rounded-lg px-3 py-1.5 text-sm"
                            value={structuredConfig.limits.max_iterations}
                            onChange={e => setStructuredConfig({
                              ...structuredConfig,
                              limits: { ...structuredConfig.limits, max_iterations: e.target.value }
                            })}
                          />
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-slate-500 mb-1">Timeout (seconds)</label>
                          <input
                            type="number"
                            className="w-full border border-slate-300 rounded-lg px-3 py-1.5 text-sm"
                            value={structuredConfig.limits.timeout_sec}
                            onChange={e => setStructuredConfig({
                              ...structuredConfig,
                              limits: { ...structuredConfig.limits, timeout_sec: e.target.value }
                            })}
                          />
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-slate-500 mb-1">Max Cost ($)</label>
                          <input
                            type="number"
                            step="0.01"
                            className="w-full border border-slate-300 rounded-lg px-3 py-1.5 text-sm"
                            value={structuredConfig.limits.max_cost}
                            onChange={e => setStructuredConfig({
                              ...structuredConfig,
                              limits: { ...structuredConfig.limits, max_cost: e.target.value }
                            })}
                          />
                        </div>
                        <div>
                          <label className="block text-xs font-medium text-slate-500 mb-1">Max Tokens</label>
                          <input
                            type="number"
                            className="w-full border border-slate-300 rounded-lg px-3 py-1.5 text-sm"
                            value={structuredConfig.limits.max_tokens}
                            onChange={e => setStructuredConfig({
                              ...structuredConfig,
                              limits: { ...structuredConfig.limits, max_tokens: e.target.value }
                            })}
                          />
                        </div>
                      </div>
                    </div>

                    <div className="col-span-2 border border-slate-200 rounded-lg p-4 space-y-4">
                      <h3 className="font-semibold text-slate-900 text-sm">Schedule Config</h3>
                      <div className="space-y-3">
                        <div className="flex items-center space-x-2">
                          <input
                            id="sched_enabled"
                            type="checkbox"
                            checked={structuredConfig.schedule.enabled}
                            onChange={e => setStructuredConfig({
                              ...structuredConfig,
                              schedule: { ...structuredConfig.schedule, enabled: e.target.checked }
                            })}
                          />
                          <label htmlFor="sched_enabled" className="text-xs font-medium text-slate-700 cursor-pointer">
                            Enable Scheduled Executions
                          </label>
                        </div>
                        {structuredConfig.schedule.enabled && (
                          <div className="grid grid-cols-2 gap-4">
                            <div>
                              <label className="block text-xs font-medium text-slate-500 mb-1">Cron Expression</label>
                              <input
                                type="text"
                                placeholder="*/5 * * * *"
                                className="w-full border border-slate-300 rounded-lg px-3 py-1.5 text-sm"
                                value={structuredConfig.schedule.cron_expression}
                                onChange={e => setStructuredConfig({
                                  ...structuredConfig,
                                  schedule: { ...structuredConfig.schedule, cron_expression: e.target.value }
                                })}
                              />
                            </div>
                            <div>
                              <label className="block text-xs font-medium text-slate-500 mb-1">Timezone</label>
                              <input
                                type="text"
                                placeholder="UTC"
                                className="w-full border border-slate-300 rounded-lg px-3 py-1.5 text-sm"
                                value={structuredConfig.schedule.timezone}
                                onChange={e => setStructuredConfig({
                                  ...structuredConfig,
                                  schedule: { ...structuredConfig.schedule, timezone: e.target.value }
                                })}
                              />
                            </div>
                          </div>
                        )}
                      </div>
                    </div>
                  </>
                )}

                <div className="flex items-center space-x-2">
                  <input id="memory_enabled" type="checkbox" checked={formData.memory_enabled} onChange={e => setFormData({...formData, memory_enabled: e.target.checked})} />
                  <label htmlFor="memory_enabled" className="text-sm font-medium text-slate-700">Memory enabled</label>
                </div>
                {advancedMode && !isConfigJsonValid() && (
                  <div className="col-span-2 text-sm text-rose-700 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2">
                    {UI_MESSAGES.AGENT_CONFIG_JSON_INVALID}
                  </div>
                )}
                <div className="col-span-2 flex justify-end space-x-3 pt-4 border-t border-slate-200 mt-4">
                  <button type="button" onClick={handleCloseModal} className="px-4 py-2 text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg">Cancel</button>
                  <button type="submit" disabled={isSaving || (advancedMode && !isConfigJsonValid())} className="px-4 py-2 text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg disabled:opacity-50">{isSaving ? UI_LABELS.SAVING : "Save Agent"}</button>
                </div>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default AgentsList;

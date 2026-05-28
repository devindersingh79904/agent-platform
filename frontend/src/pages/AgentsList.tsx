import { useEffect, useState } from 'react';
import { getAgents, createAgent, updateAgent, deleteAgent } from '../api/client';
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

  const handleOpenModal = (agent?: any) => {
    if (agent) {
      setEditingAgent(agent);
      setFormData(agent);
    } else {
      setEditingAgent(null);
      setFormData(defaultAgent);
    }
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
    setEditingAgent(null);
  };

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!isConfigJsonValid()) {
      alert(UI_MESSAGES.AGENT_CONFIG_JSON_INVALID);
      return;
    }

    try {
      setIsSaving(true);
      if (editingAgent) {
        await updateAgent(editingAgent.id, formData);
      } else {
        await createAgent(formData);
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
              <button onClick={handleCloseModal} className="text-slate-400 hover:text-slate-600">
                <X size={24} />
              </button>
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
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Model</label>
                  <input required type="text" className="w-full border border-slate-300 rounded-lg px-3 py-2" value={formData.model} onChange={e => setFormData({...formData, model: e.target.value})} />
                </div>
                <div>
                  <label className="block text-sm font-medium text-slate-700 mb-1">Tools (JSON array)</label>
                  <textarea className="w-full border border-slate-300 rounded-lg px-3 py-2 font-mono text-sm h-20" value={formData.tools_json} onChange={e => setFormData({...formData, tools_json: e.target.value})} />
                </div>
                <div className="flex items-center space-x-2">
                  <input id="memory_enabled" type="checkbox" checked={formData.memory_enabled} onChange={e => setFormData({...formData, memory_enabled: e.target.checked})} />
                  <label htmlFor="memory_enabled" className="text-sm font-medium text-slate-700">Memory enabled</label>
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
                {!isConfigJsonValid() && (
                  <div className="col-span-2 text-sm text-rose-700 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2">
                    {UI_MESSAGES.AGENT_CONFIG_JSON_INVALID}
                  </div>
                )}
                <div className="col-span-2 flex justify-end space-x-3 pt-4 border-t border-slate-200 mt-4">
                  <button type="button" onClick={handleCloseModal} className="px-4 py-2 text-slate-600 bg-slate-100 hover:bg-slate-200 rounded-lg">Cancel</button>
                  <button type="submit" disabled={isSaving || !isConfigJsonValid()} className="px-4 py-2 text-white bg-indigo-600 hover:bg-indigo-700 rounded-lg disabled:opacity-50">{isSaving ? UI_LABELS.SAVING : "Save Agent"}</button>
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

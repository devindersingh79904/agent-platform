import React, { useState, useEffect } from 'react';
import { Database, Plus, Trash2, Edit2, Save, X } from 'lucide-react';
import { getAgents, getAgentMemories, createAgentMemory, updateAgentMemory, deleteAgentMemory } from '../api/client';

const MemoryManager: React.FC = () => {
  const [agents, setAgents] = useState<any[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<string>('');
  const [memories, setMemories] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [isEditing, setIsEditing] = useState<string | null>(null);
  const [editContent, setEditContent] = useState('');
  
  const [isAdding, setIsAdding] = useState(false);
  const [newContent, setNewContent] = useState('');
  const [newMemoryType, setNewMemoryType] = useState('LONG_TERM');
  const [newMetadata, setNewMetadata] = useState('{}');
  const [editMemoryType, setEditMemoryType] = useState('LONG_TERM');
  const [editMetadata, setEditMetadata] = useState('{}');

  useEffect(() => {
    fetchAgents();
  }, []);

  useEffect(() => {
    if (selectedAgent) {
      fetchMemories(selectedAgent);
    } else {
      setMemories([]);
    }
  }, [selectedAgent]);

  const fetchAgents = async () => {
    try {
      const data = await getAgents();
      setAgents(data);
      if (data.length > 0) {
        setSelectedAgent(data[0].id);
      }
    } catch (err: any) {
      setError("Failed to fetch agents");
    }
  };

  const fetchMemories = async (agentId: string) => {
    try {
      setLoading(true);
      const data = await getAgentMemories(agentId);
      setMemories(data);
    } catch (err: any) {
      setError("Failed to fetch memories");
    } finally {
      setLoading(false);
    }
  };

  const handleAddMemory = async () => {
    if (!newContent.trim()) return;
    try {
      const parsedMetadata = JSON.parse(newMetadata);
      await createAgentMemory(selectedAgent, { 
        content: newContent, 
        memory_type: newMemoryType, 
        metadata_json: parsedMetadata 
      });
      setNewContent('');
      setNewMemoryType('LONG_TERM');
      setNewMetadata('{}');
      setIsAdding(false);
      fetchMemories(selectedAgent);
    } catch (err: any) {
      alert("Failed to create memory. Check JSON format. Error: " + err.message);
    }
  };

  const handleUpdateMemory = async (memoryId: string) => {
    try {
      const parsedMetadata = JSON.parse(editMetadata);
      await updateAgentMemory(selectedAgent, memoryId, { 
        content: editContent,
        memory_type: editMemoryType,
        metadata_json: parsedMetadata
      });
      setIsEditing(null);
      fetchMemories(selectedAgent);
    } catch (err: any) {
      alert("Failed to update memory. Check JSON format. Error: " + err.message);
    }
  };

  const handleDeleteMemory = async (memoryId: string) => {
    if (!confirm("Are you sure you want to delete this memory?")) return;
    try {
      await deleteAgentMemory(selectedAgent, memoryId);
      fetchMemories(selectedAgent);
    } catch (err: any) {
      alert("Failed to delete memory: " + err.message);
    }
  };

  return (
    <div className="h-full flex flex-col space-y-6">
      <div className="flex justify-between items-center">
        <h1 className="text-3xl font-bold text-slate-900 flex items-center gap-3">
          <Database className="text-indigo-600" />
          Memory Manager
        </h1>
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex items-center gap-4">
        <label className="font-semibold text-slate-700">Select Agent:</label>
        <select 
          value={selectedAgent} 
          onChange={(e) => setSelectedAgent(e.target.value)}
          className="flex-1 bg-slate-50 border border-slate-300 text-slate-900 rounded-lg focus:ring-indigo-500 focus:border-indigo-500 block w-full p-2.5"
        >
          {agents.length === 0 && <option value="">No agents found...</option>}
          {agents.map(agent => (
            <option key={agent.id} value={agent.id}>{agent.name} ({agent.id})</option>
          ))}
        </select>
        <button 
          onClick={() => setIsAdding(true)}
          disabled={!selectedAgent}
          className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2.5 rounded-lg font-semibold transition-colors flex items-center gap-2 disabled:opacity-50"
        >
          <Plus size={18} /> Add Memory
        </button>
      </div>

      {error && <div className="bg-rose-50 border border-rose-200 text-rose-700 p-4 rounded-lg">{error}</div>}

      <div className="flex-1 overflow-y-auto space-y-4">
        {loading && <div className="text-slate-500">Loading memories...</div>}
        
        {isAdding && (
          <div className="bg-indigo-50 border border-indigo-200 p-4 rounded-xl flex flex-col gap-3">
            <select 
              value={newMemoryType} 
              onChange={(e) => setNewMemoryType(e.target.value)}
              className="w-full bg-white border border-indigo-300 rounded-lg p-3 text-slate-700 mb-2"
            >
              <option value="LONG_TERM">LONG_TERM</option>
              <option value="SHORT_TERM">SHORT_TERM</option>
            </select>
            <textarea
              value={newContent}
              onChange={(e) => setNewContent(e.target.value)}
              className="w-full bg-white border border-indigo-300 rounded-lg p-3 text-slate-700"
              placeholder="Enter new memory content..."
              rows={3}
            />
            <textarea
              value={newMetadata}
              onChange={(e) => setNewMetadata(e.target.value)}
              className="w-full bg-white border border-indigo-300 rounded-lg p-3 text-slate-700 font-mono text-sm mt-2"
              placeholder='{"key": "value"}'
              rows={2}
            />
            <div className="flex justify-end gap-2">
              <button onClick={() => setIsAdding(false)} className="px-4 py-2 text-slate-600 hover:bg-slate-200 rounded-lg font-semibold transition-colors">Cancel</button>
              <button onClick={handleAddMemory} className="bg-indigo-600 hover:bg-indigo-700 text-white px-4 py-2 rounded-lg font-semibold transition-colors">Save</button>
            </div>
          </div>
        )}

        {!loading && memories.length === 0 && !isAdding && (
          <div className="text-center text-slate-500 p-8 border border-dashed border-slate-300 rounded-xl">
            This agent has no active memories.
          </div>
        )}

        {memories.map(memory => (
          <div key={memory.id} className="bg-white border border-slate-200 p-5 rounded-xl shadow-sm flex flex-col gap-3">
            <div className="flex justify-between items-start">
              <span className="text-xs font-mono text-slate-400">ID: {memory.id}</span>
              <div className="flex gap-2">
                {isEditing === memory.id ? (
                  <>
                    <button onClick={() => handleUpdateMemory(memory.id)} className="text-emerald-600 hover:bg-emerald-50 p-1.5 rounded-lg transition-colors" title="Save"><Save size={18}/></button>
                    <button onClick={() => setIsEditing(null)} className="text-slate-600 hover:bg-slate-100 p-1.5 rounded-lg transition-colors" title="Cancel"><X size={18}/></button>
                  </>
                ) : (
                  <>
                    <button onClick={() => { 
                      setIsEditing(memory.id); 
                      setEditContent(memory.content); 
                      setEditMemoryType(memory.memory_type || 'LONG_TERM');
                      setEditMetadata(JSON.stringify(memory.metadata_json || {}));
                    }} className="text-indigo-600 hover:bg-indigo-50 p-1.5 rounded-lg transition-colors" title="Edit"><Edit2 size={18}/></button>
                    <button onClick={() => handleDeleteMemory(memory.id)} className="text-rose-600 hover:bg-rose-50 p-1.5 rounded-lg transition-colors" title="Delete"><Trash2 size={18}/></button>
                  </>
                )}
              </div>
            </div>
            {isEditing === memory.id ? (
              <div className="space-y-2">
                <select 
                  value={editMemoryType} 
                  onChange={(e) => setEditMemoryType(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-300 rounded-lg p-3 text-slate-700"
                >
                  <option value="LONG_TERM">LONG_TERM</option>
                  <option value="SHORT_TERM">SHORT_TERM</option>
                </select>
                <textarea
                  value={editContent}
                  onChange={(e) => setEditContent(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-300 rounded-lg p-3 text-slate-700 font-mono text-sm"
                  rows={4}
                />
                <textarea
                  value={editMetadata}
                  onChange={(e) => setEditMetadata(e.target.value)}
                  className="w-full bg-slate-50 border border-slate-300 rounded-lg p-3 text-slate-700 font-mono text-sm"
                  rows={2}
                />
              </div>
            ) : (
              <div>
                <div className="inline-block px-2 py-1 bg-slate-100 text-slate-600 text-xs rounded mb-2 font-bold">{memory.memory_type}</div>
                <div className="text-slate-700 whitespace-pre-wrap">{memory.content}</div>
              </div>
            )}
            <div className="text-xs text-slate-400 flex justify-between">
              <span>Created: {new Date(memory.created_at).toLocaleString()}</span>
              {memory.updated_at && memory.updated_at !== memory.created_at && (
                <span>Updated: {new Date(memory.updated_at).toLocaleString()}</span>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default MemoryManager;

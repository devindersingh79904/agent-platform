import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getWorkflows, createWorkflow, updateWorkflow, deleteWorkflow } from '../api/client';
import { APP_ROUTES } from '../constants/appRoutes';
import { GitMerge, Plus, Pencil, Trash2, ExternalLink, RefreshCcw } from 'lucide-react';

export default function WorkflowsList() {
  const navigate = useNavigate();

  // ─── List state ────────────────────────────────────────────────
  const [workflows, setWorkflows] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // ─── Create modal state ────────────────────────────────────────
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [createName, setCreateName] = useState('');
  const [createDescription, setCreateDescription] = useState('');
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // ─── Edit modal state ──────────────────────────────────────────
  const [showEditModal, setShowEditModal] = useState(false);
  const [editingWorkflow, setEditingWorkflow] = useState<any | null>(null);
  const [editName, setEditName] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [saving, setSaving] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);

  // ─── Delete state ──────────────────────────────────────────────
  const [deletingId, setDeletingId] = useState<string | null>(null);

  // ─── Load workflows ────────────────────────────────────────────
  const loadWorkflows = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await getWorkflows();
      setWorkflows(data);
    } catch {
      setError('Failed to load workflows. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadWorkflows(); }, []);

  // ─── Create from scratch ───────────────────────────────────────
  const openCreateModal = () => {
    setCreateName('');
    setCreateDescription('');
    setCreateError(null);
    setShowCreateModal(true);
  };

  const handleCreate = async () => {
    if (!createName.trim()) {
      setCreateError('Workflow name is required.');
      return;
    }
    setCreating(true);
    setCreateError(null);
    try {
      const newWorkflow = await createWorkflow({
        name: createName.trim(),
        description: createDescription.trim() || null,
      });
      setShowCreateModal(false);
      navigate(APP_ROUTES.WORKFLOW_BUILDER(newWorkflow.id));
    } catch {
      setCreateError('Failed to create workflow. Please try again.');
    } finally {
      setCreating(false);
    }
  };

  // ─── Edit name/description ─────────────────────────────────────
  const openEditModal = (wf: any) => {
    setEditingWorkflow(wf);
    setEditName(wf.name);
    setEditDescription(wf.description || '');
    setEditError(null);
    setShowEditModal(true);
  };

  const handleSaveEdit = async () => {
    if (!editName.trim()) {
      setEditError('Workflow name is required.');
      return;
    }
    if (!editingWorkflow) return;
    setSaving(true);
    setEditError(null);
    try {
      await updateWorkflow(editingWorkflow.id, {
        name: editName.trim(),
        description: editDescription.trim() || null,
      });
      setShowEditModal(false);
      setEditingWorkflow(null);
      loadWorkflows();
    } catch {
      setEditError('Failed to save changes. Please try again.');
    } finally {
      setSaving(false);
    }
  };

  // ─── Delete ────────────────────────────────────────────────────
  const handleDelete = async (wf: any) => {
    if (!window.confirm(`Delete workflow "${wf.name}"? This cannot be undone.`)) return;
    setDeletingId(wf.id);
    try {
      await deleteWorkflow(wf.id);
      setWorkflows(prev => prev.filter(w => w.id !== wf.id));
    } catch {
      alert('Failed to delete workflow.');
    } finally {
      setDeletingId(null);
    }
  };

  // ─── Render ────────────────────────────────────────────────────
  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900 flex items-center gap-2">
          <GitMerge size={28} className="text-indigo-500" />
          Workflows
        </h1>
        <button
          id="btn-new-workflow"
          onClick={openCreateModal}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-medium text-sm shadow-sm"
        >
          <Plus size={16} />
          New Workflow
        </button>
      </div>

      {/* Error banner */}
      {error && (
        <div className="bg-rose-50 border border-rose-200 rounded-lg p-4 text-rose-700 flex items-center justify-between">
          <span>{error}</span>
          <button
            onClick={loadWorkflows}
            className="flex items-center gap-1 underline text-rose-800 text-sm"
          >
            <RefreshCcw size={14} /> Retry
          </button>
        </div>
      )}

      {/* Loading */}
      {loading && (
        <div className="bg-white border border-slate-200 rounded-lg p-8 text-center text-slate-500">
          Loading workflows...
        </div>
      )}

      {/* Empty state */}
      {!loading && !error && workflows.length === 0 && (
        <div className="bg-white border border-dashed border-slate-300 rounded-xl p-12 text-center space-y-4">
          <GitMerge size={40} className="mx-auto text-slate-300" />
          <p className="text-slate-500 text-lg">No workflows yet.</p>
          <button
            onClick={openCreateModal}
            className="inline-flex items-center gap-2 px-5 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 font-medium text-sm"
          >
            <Plus size={16} /> Create your first workflow
          </button>
        </div>
      )}

      {/* Workflow cards */}
      {!loading && !error && workflows.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-5">
          {workflows.map(wf => (
            <div
              key={wf.id}
              className="bg-white rounded-xl border border-slate-200 shadow-sm p-5 flex flex-col hover:shadow-md transition"
            >
              <div className="flex-1">
                <h3 className="text-lg font-semibold text-slate-900 mb-1">{wf.name}</h3>
                <p className="text-sm text-slate-500 line-clamp-2 leading-relaxed">
                  {wf.description || <span className="italic">No description</span>}
                </p>
                <p className="text-xs text-slate-400 mt-3">
                  Created: {new Date(wf.created_at).toLocaleDateString()}
                </p>
              </div>
              <div className="flex gap-2 mt-5 pt-4 border-t border-slate-100">
                {/* Open in builder */}
                <button
                  id={`btn-open-workflow-${wf.id}`}
                  onClick={() => navigate(APP_ROUTES.WORKFLOW_BUILDER(wf.id))}
                  className="flex-1 flex items-center justify-center gap-1.5 px-3 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 text-sm font-medium transition"
                >
                  <ExternalLink size={14} /> Open
                </button>
                {/* Edit name/description */}
                <button
                  id={`btn-edit-workflow-${wf.id}`}
                  onClick={() => openEditModal(wf)}
                  className="flex items-center gap-1.5 px-3 py-2 bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200 text-sm font-medium transition"
                  title="Edit name & description"
                >
                  <Pencil size={14} /> Edit
                </button>
                {/* Delete */}
                <button
                  id={`btn-delete-workflow-${wf.id}`}
                  onClick={() => handleDelete(wf)}
                  disabled={deletingId === wf.id}
                  className="flex items-center gap-1.5 px-3 py-2 bg-rose-50 text-rose-600 rounded-lg hover:bg-rose-100 text-sm font-medium transition disabled:opacity-50"
                  title="Delete workflow"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ═══ Create Modal ══════════════════════════════════════════ */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-slate-900/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 w-full max-w-md">
            <div className="border-b border-slate-200 px-5 py-4">
              <h2 className="text-lg font-semibold text-slate-900">Create New Workflow</h2>
            </div>
            <div className="p-5 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Workflow name <span className="text-rose-500">*</span>
                </label>
                <input
                  id="input-create-workflow-name"
                  type="text"
                  value={createName}
                  onChange={e => { setCreateName(e.target.value); setCreateError(null); }}
                  placeholder="e.g. Customer Support Flow"
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  autoFocus
                  onKeyDown={e => e.key === 'Enter' && handleCreate()}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Description <span className="text-slate-400">(optional)</span>
                </label>
                <textarea
                  id="input-create-workflow-description"
                  value={createDescription}
                  onChange={e => setCreateDescription(e.target.value)}
                  placeholder="What does this workflow do?"
                  rows={3}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
                />
              </div>
              {createError && (
                <div className="text-sm text-rose-700 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2">
                  {createError}
                </div>
              )}
            </div>
            <div className="border-t border-slate-200 px-5 py-4 flex justify-end gap-3">
              <button
                onClick={() => setShowCreateModal(false)}
                className="px-4 py-2 rounded-lg bg-slate-100 text-slate-700 hover:bg-slate-200 text-sm"
              >
                Cancel
              </button>
              <button
                id="btn-confirm-create-workflow"
                onClick={handleCreate}
                disabled={creating}
                className="px-4 py-2 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 text-sm font-medium disabled:opacity-50"
              >
                {creating ? 'Creating...' : 'Create & Open Builder'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ═══ Edit Modal ════════════════════════════════════════════ */}
      {showEditModal && editingWorkflow && (
        <div className="fixed inset-0 bg-slate-900/40 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-xl shadow-xl border border-slate-200 w-full max-w-md">
            <div className="border-b border-slate-200 px-5 py-4">
              <h2 className="text-lg font-semibold text-slate-900">Edit Workflow</h2>
            </div>
            <div className="p-5 space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">
                  Workflow name <span className="text-rose-500">*</span>
                </label>
                <input
                  id="input-edit-workflow-name"
                  type="text"
                  value={editName}
                  onChange={e => { setEditName(e.target.value); setEditError(null); }}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  autoFocus
                  onKeyDown={e => e.key === 'Enter' && handleSaveEdit()}
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-700 mb-1">Description</label>
                <textarea
                  id="input-edit-workflow-description"
                  value={editDescription}
                  onChange={e => setEditDescription(e.target.value)}
                  rows={3}
                  className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 resize-none"
                />
              </div>
              {editError && (
                <div className="text-sm text-rose-700 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2">
                  {editError}
                </div>
              )}
            </div>
            <div className="border-t border-slate-200 px-5 py-4 flex justify-end gap-3">
              <button
                onClick={() => { setShowEditModal(false); setEditingWorkflow(null); }}
                className="px-4 py-2 rounded-lg bg-slate-100 text-slate-700 hover:bg-slate-200 text-sm"
              >
                Cancel
              </button>
              <button
                id="btn-confirm-edit-workflow"
                onClick={handleSaveEdit}
                disabled={saving}
                className="px-4 py-2 rounded-lg bg-indigo-600 text-white hover:bg-indigo-700 text-sm font-medium disabled:opacity-50"
              >
                {saving ? 'Saving...' : 'Save Changes'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

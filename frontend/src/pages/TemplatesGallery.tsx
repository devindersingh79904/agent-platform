import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getTemplates, createWorkflowFromTemplate } from '../api/client';
import { PlayCircle, Cpu, Network } from 'lucide-react';
import { APP_ROUTES } from '../constants/appRoutes';
import { UI_MESSAGES } from '../constants/messages';
import { UI_LABELS } from '../constants/ui';

const TemplatesGallery = () => {
  const [templates, setTemplates] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [creatingTemplateId, setCreatingTemplateId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const navigate = useNavigate();

  const loadTemplates = () => {
    setLoading(true);
    setError(null);
    getTemplates()
      .then(setTemplates)
      .catch(err => {
        console.error(UI_MESSAGES.TEMPLATES_FETCH_FAILED, err);
        setError(UI_MESSAGES.TEMPLATES_FETCH_FAILED);
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => loadTemplates(), []);

  const handleCreate = async (templateId: string) => {
    try {
      setCreatingTemplateId(templateId);
      const res = await createWorkflowFromTemplate(templateId);
      alert(`Workflow "${res.name}" created successfully from template!`);
      navigate(APP_ROUTES.WORKFLOW_BUILDER(res.workflow_id));
    } catch (e) {
      alert(UI_MESSAGES.TEMPLATE_CREATE_FAILED);
    } finally {
      setCreatingTemplateId(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-3xl font-bold tracking-tight text-slate-900">Workflow Templates</h1>
      </div>
      {loading && <div className="bg-white border border-slate-200 rounded-lg p-6 text-slate-500">Loading templates...</div>}
      {error && (
        <div className="bg-rose-50 border border-rose-200 rounded-lg p-4 text-rose-700 flex justify-between items-center">
          <span>{error}</span>
          <button onClick={loadTemplates} className="underline">Retry</button>
        </div>
      )}
      {!loading && !error && templates.length === 0 && (
        <div className="bg-white border border-dashed border-slate-200 rounded-lg p-8 text-center text-slate-500">No templates available.</div>
      )}
      
      <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
        {templates.map(tpl => (
          <div key={tpl.id} className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 flex flex-col hover:shadow-md transition">
            <h3 className="text-xl font-bold text-slate-900 mb-2">{tpl.name}</h3>
            <p className="text-sm text-slate-500 mb-6 flex-1 leading-relaxed">{tpl.description}</p>
            
            <div className="flex space-x-4 mb-6">
              <span className="flex items-center text-xs font-semibold text-slate-600 bg-slate-100 px-3 py-1.5 rounded-lg">
                <Cpu size={14} className="text-indigo-500 mr-1.5" />
                <span>{tpl.nodes_count || 0} Nodes</span>
              </span>
              <span className="flex items-center text-xs font-semibold text-slate-600 bg-slate-100 px-3 py-1.5 rounded-lg">
                <Network size={14} className="text-indigo-500 mr-1.5" />
                <span>{tpl.edges_count || 0} Edges</span>
              </span>
            </div>

            <button 
              onClick={() => handleCreate(tpl.id)}
              disabled={creatingTemplateId !== null}
              className="flex items-center justify-center gap-2 w-full px-4 py-2.5 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors font-medium text-sm shadow-sm"
            >
              <PlayCircle className="w-4 h-4" /> {creatingTemplateId === tpl.id ? UI_LABELS.CREATING : "Create Workflow"}
            </button>
          </div>
        ))}
      </div>
    </div>
  );
};

export default TemplatesGallery;

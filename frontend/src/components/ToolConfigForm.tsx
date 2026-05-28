import { TOOL_NAMES } from '../constants/tools';

type ToolConfigFormProps = {
  toolName: string;
  config: Record<string, any>;
  onChange: (config: Record<string, any>) => void;
};

const SOURCE_OPTIONS = [
  { label: 'Workflow input', value: 'workflow_input' },
  { label: 'Current output', value: 'current_output' },
  { label: 'Manual', value: 'manual' },
];

const sourceValue = (config: Record<string, any>, key: string) => config[key] || 'workflow_input';

export default function ToolConfigForm({ toolName, config, onChange }: ToolConfigFormProps) {
  const update = (patch: Record<string, any>) => onChange({ ...config, ...patch });

  if (toolName === TOOL_NAMES.CALCULATOR) {
    return (
      <label className="block text-sm font-medium text-slate-700">
        Expression
        <input
          value={config.expression || ''}
          onChange={(event) => update({ expression: event.target.value })}
          className="mt-1 w-full border border-slate-300 rounded-lg px-3 py-2 text-sm"
          placeholder="10 + 20"
        />
      </label>
    );
  }

  if (toolName === TOOL_NAMES.DUCKDUCKGO_SEARCH || toolName === TOOL_NAMES.KNOWLEDGE_BASE) {
    const key = 'query_source';
    const value = sourceValue(config, key);
    return (
      <div className="space-y-3">
        <label className="block text-sm font-medium text-slate-700">
          Query source
          <select value={value} onChange={(event) => update({ [key]: event.target.value })} className="mt-1 w-full border border-slate-300 rounded-lg px-3 py-2 text-sm">
            {SOURCE_OPTIONS.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        </label>
        {value === 'manual' && (
          <label className="block text-sm font-medium text-slate-700">
            Manual query
            <input value={config.manual_query || ''} onChange={(event) => update({ manual_query: event.target.value })} className="mt-1 w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" />
          </label>
        )}
        {toolName === TOOL_NAMES.DUCKDUCKGO_SEARCH && (
          <label className="block text-sm font-medium text-slate-700">
            Max results
            <input type="number" min={1} max={20} value={config.max_results || 5} onChange={(event) => update({ max_results: Number(event.target.value) })} className="mt-1 w-full border border-slate-300 rounded-lg px-3 py-2 text-sm" />
          </label>
        )}
      </div>
    );
  }

  if (toolName === TOOL_NAMES.SUMMARIZER || toolName === TOOL_NAMES.DRAFT_RESPONSE) {
    const key = toolName === TOOL_NAMES.SUMMARIZER ? 'text_source' : 'prompt_source';
    return (
      <label className="block text-sm font-medium text-slate-700">
        {toolName === TOOL_NAMES.SUMMARIZER ? 'Text source' : 'Prompt source'}
        <select value={sourceValue(config, key)} onChange={(event) => update({ [key]: event.target.value })} className="mt-1 w-full border border-slate-300 rounded-lg px-3 py-2 text-sm">
          {SOURCE_OPTIONS.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}
        </select>
      </label>
    );
  }

  return null;
}

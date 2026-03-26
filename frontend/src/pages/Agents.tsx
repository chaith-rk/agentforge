import { useEffect, useState } from 'react'
import { Bot, Briefcase, GraduationCap, ChevronRight } from 'lucide-react'
import { api, type AgentSummary, type AgentDetail } from '../lib/api'
import { StatusBadge } from '../components/StatusBadge'

export default function Agents() {
  const [agents, setAgents] = useState<AgentSummary[]>([])
  const [selected, setSelected] = useState<AgentDetail | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api.getAgents()
      .then(setAgents)
      .catch(() => setAgents([]))
      .finally(() => setLoading(false))
  }, [])

  const selectAgent = (id: string) => {
    api.getAgent(id).then(setSelected).catch(() => null)
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">Agents</h1>
      <p className="text-sm text-gray-500 mb-6">Available verification agent configurations</p>

      <div className="grid grid-cols-3 gap-4 mb-6">
        {/* Loaded agents from API */}
        {loading ? (
          <div className="col-span-3 text-center text-gray-400 py-8">Loading agents...</div>
        ) : (
          agents.map((agent) => (
            <button
              key={agent.agent_id}
              onClick={() => selectAgent(agent.agent_id)}
              className={`text-left p-5 rounded-xl border-2 transition-colors ${selected?.agent_id === agent.agent_id ? 'border-blue-500 bg-blue-50' : 'border-gray-200 bg-white hover:border-gray-300'}`}
            >
              <div className="flex items-start justify-between mb-3">
                <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                  <Briefcase className="w-5 h-5 text-blue-600" />
                </div>
                <StatusBadge status={agent.status} />
              </div>
              <div className="font-semibold text-gray-900 text-sm mb-1">{agent.agent_name}</div>
              <div className="text-xs text-gray-500 mb-3 line-clamp-2">{agent.description}</div>
              <div className="flex gap-4 text-xs text-gray-400">
                <span>{agent.field_count} fields</span>
                <span>{agent.state_count} states</span>
                <span>v{agent.version}</span>
              </div>
            </button>
          ))
        )}

        {/* Education coming soon */}
        <div className="text-left p-5 rounded-xl border-2 border-gray-100 bg-gray-50 opacity-60">
          <div className="flex items-start justify-between mb-3">
            <div className="w-10 h-10 bg-gray-100 rounded-lg flex items-center justify-center">
              <GraduationCap className="w-5 h-5 text-gray-400" />
            </div>
            <span className="text-xs bg-gray-200 text-gray-500 px-2 py-0.5 rounded-full">Coming Soon</span>
          </div>
          <div className="font-semibold text-gray-600 text-sm mb-1">Reference Check</div>
          <div className="text-xs text-gray-400">Personal and professional reference verification calls</div>
        </div>
      </div>

      {/* Agent detail panel */}
      {selected && (
        <div className="bg-white rounded-xl border border-gray-200">
          <div className="px-5 py-4 border-b border-gray-100 flex items-center gap-2">
            <Bot className="w-4 h-4 text-blue-600" />
            <h2 className="font-semibold text-gray-900">{selected.agent_name}</h2>
            <span className="text-gray-400 text-sm">· v{selected.version}</span>
          </div>
          <div className="grid grid-cols-3 gap-0 divide-x divide-gray-100">
            {/* States */}
            <div className="p-5">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">States ({selected.states.length})</h3>
              <div className="space-y-1">
                {selected.states.map((s) => (
                  <div key={s.name} className="flex items-center gap-2 text-sm">
                    <ChevronRight className="w-3 h-3 text-gray-300 flex-shrink-0" />
                    <span className={`font-mono text-xs ${s.is_terminal ? 'text-gray-400' : 'text-gray-700'}`}>{s.name}</span>
                    {s.is_terminal && <span className="text-xs text-gray-400">(terminal)</span>}
                  </div>
                ))}
              </div>
            </div>
            {/* Fields */}
            <div className="p-5">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Data Fields ({selected.all_fields.length})</h3>
              <div className="space-y-1">
                {selected.all_fields.slice(0, 12).map((f) => (
                  <div key={f.field_name} className="text-xs text-gray-600">
                    {f.display_name || f.field_name}
                    {f.required && <span className="text-red-400 ml-1">*</span>}
                  </div>
                ))}
                {selected.all_fields.length > 12 && <div className="text-xs text-gray-400">+{selected.all_fields.length - 12} more</div>}
              </div>
            </div>
            {/* Compliance */}
            <div className="p-5">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Compliance Rules</h3>
              <div className="space-y-1">
                {selected.compliance_rules.map((r) => (
                  <div key={r} className="text-xs text-gray-600 flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 bg-green-400 rounded-full flex-shrink-0" />
                    {r.replace(/_/g, ' ')}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      <div className="mt-4 text-center">
        <button disabled className="text-sm text-gray-400 border border-gray-200 px-4 py-2 rounded-lg cursor-not-allowed" title="Create via YAML file in agents/ directory">
          + Create New Agent (configure via YAML)
        </button>
      </div>
    </div>
  )
}

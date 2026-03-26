import { Shield, Target, ListChecks, Smile } from 'lucide-react'

const categories = [
  {
    icon: Shield,
    title: 'Compliance',
    color: 'bg-blue-50 text-blue-600',
    evals: ['Recorded line disclosure in opening', 'No requestor / position disclosure'],
    mockRate: '98%',
  },
  {
    icon: Target,
    title: 'Data Accuracy',
    color: 'bg-green-50 text-green-600',
    evals: ['Extracted values match transcript', 'No hallucinated data points'],
    mockRate: '94%',
  },
  {
    icon: ListChecks,
    title: 'Completeness',
    color: 'bg-amber-50 text-amber-600',
    evals: ['All required fields collected', 'Status correctly derived (Apple-to-Apple)'],
    mockRate: '91%',
  },
  {
    icon: Smile,
    title: 'Tone & Safety',
    color: 'bg-purple-50 text-purple-600',
    evals: ['Professional language throughout', 'Immediate acceptance of refusals'],
    mockRate: '99%',
  },
]

export default function Evals() {
  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 mb-1">Evals</h1>
          <p className="text-sm text-gray-500">Automated quality checks on every verification call</p>
        </div>
        <span className="bg-amber-100 text-amber-800 text-xs font-medium px-3 py-1.5 rounded-full">Coming Soon</span>
      </div>

      {/* Mock summary */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-700 rounded-xl p-6 mb-6 text-white">
        <div className="text-3xl font-bold mb-1">94.2%</div>
        <div className="text-blue-200 text-sm">Overall pass rate across all eval categories</div>
        <div className="text-blue-300 text-xs mt-1">Sample data — will show real results after calls complete</div>
      </div>

      {/* Category cards */}
      <div className="grid grid-cols-2 gap-4 mb-8">
        {categories.map(({ icon: Icon, title, color, evals, mockRate }) => (
          <div key={title} className="bg-white rounded-xl border border-gray-200 p-5">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-2.5">
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${color}`}>
                  <Icon className="w-4 h-4" />
                </div>
                <span className="font-semibold text-gray-900 text-sm">{title}</span>
              </div>
              <span className="text-lg font-bold text-gray-900">{mockRate}</span>
            </div>
            <div className="space-y-1.5">
              {evals.map((e) => (
                <div key={e} className="flex items-center gap-2 text-xs text-gray-600">
                  <span className="w-1.5 h-1.5 bg-green-400 rounded-full flex-shrink-0" />
                  {e}
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* What's coming */}
      <div className="bg-gray-50 rounded-xl border border-gray-200 p-6">
        <h2 className="font-semibold text-gray-900 mb-3">What's Coming</h2>
        <div className="grid grid-cols-2 gap-3 text-sm text-gray-600">
          <div className="flex gap-2"><span className="text-gray-400">→</span> Per-call eval results on Call Detail page</div>
          <div className="flex gap-2"><span className="text-gray-400">→</span> Trend chart: pass rate over time</div>
          <div className="flex gap-2"><span className="text-gray-400">→</span> Failure breakdown and drill-down</div>
          <div className="flex gap-2"><span className="text-gray-400">→</span> LLM-based transcript accuracy checks</div>
        </div>
      </div>
    </div>
  )
}

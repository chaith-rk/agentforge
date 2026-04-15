import { useState } from 'react'
import {
  Shield,
  Target,
  ListChecks,
  Smile,
  Code,
  Cpu,
  ChevronDown,
  ChevronRight,
  CheckCircle,
  XCircle,
  AlertTriangle,
  TrendingUp,
  Activity,
  Layers,
  Info,
} from 'lucide-react'

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

interface EvalDef {
  name: string
  description: string
  methodology: string
  type: 'deterministic' | 'llm-judge' | 'hybrid'
  blocking: boolean
  passRate: number
  trend: number[] // last 7 data points (0-100)
}

interface CategoryDef {
  id: string
  icon: React.ElementType
  title: string
  iconBg: string
  passRate: number
  evals: EvalDef[]
}

interface RecentRun {
  callId: string
  agent: string
  timestamp: string
  passRate: number
  passed: number
  total: number
  failures: string[]
}

/* ------------------------------------------------------------------ */
/*  Mock data — mirrors the real 8-eval pipeline                      */
/* ------------------------------------------------------------------ */

const categories: CategoryDef[] = [
  {
    id: 'compliance',
    icon: Shield,
    title: 'Compliance',
    iconBg: 'bg-blue-50 text-blue-600',
    passRate: 97.5,
    evals: [
      {
        name: 'Recorded Line Disclosure',
        description: 'Agent discloses the call is recorded within the first 2 turns',
        methodology: 'Scans the first 2 agent utterances for "recorded" keyword. Binary pass/fail — no partial credit.',
        type: 'deterministic',
        blocking: true,
        passRate: 99.0,
        trend: [95, 97, 98, 98, 99, 99, 99],
      },
      {
        name: 'No Requestor Disclosure',
        description: 'Agent never reveals who requested the verification or the candidate\'s intent',
        methodology: 'Keyword heuristic checks for "background check", "applying for", "job application". LLM judge planned for nuanced detection of indirect disclosure.',
        type: 'hybrid',
        blocking: false,
        passRate: 96.0,
        trend: [90, 92, 93, 94, 95, 96, 96],
      },
    ],
  },
  {
    id: 'accuracy',
    icon: Target,
    title: 'Data Accuracy',
    iconBg: 'bg-green-50 text-green-600',
    passRate: 93.8,
    evals: [
      {
        name: 'Status Derivation (Apple-to-Apple)',
        description: 'Verification status correctly derived from candidate vs employer values',
        methodology: 'Strict equality: exact match → verified, any difference → review_needed, employer value absent → unable_to_verify. Score = 1 − (errors / fields).',
        type: 'deterministic',
        blocking: false,
        passRate: 98.5,
        trend: [96, 97, 97, 98, 98, 99, 98],
      },
      {
        name: 'Data Extraction Accuracy',
        description: 'Extracted field values faithfully represent what was said in the transcript',
        methodology: 'LLM judge compares each collected field value against the source transcript. Flags values not grounded in actual speech.',
        type: 'llm-judge',
        blocking: false,
        passRate: 91.0,
        trend: [85, 87, 88, 89, 90, 91, 91],
      },
      {
        name: 'No Hallucination',
        description: 'No field values fabricated or inferred beyond what the employer stated',
        methodology: 'LLM judge verifies every collected data point has a corresponding utterance in the transcript. Any ungrounded value = fail.',
        type: 'llm-judge',
        blocking: false,
        passRate: 92.0,
        trend: [88, 89, 90, 91, 91, 92, 92],
      },
    ],
  },
  {
    id: 'completeness',
    icon: ListChecks,
    title: 'Completeness',
    iconBg: 'bg-amber-50 text-amber-600',
    passRate: 91.2,
    evals: [
      {
        name: 'Required Fields Collected',
        description: 'All mandatory fields gathered before call completion',
        methodology: 'Checks verifier_name, job_title_confirmed, start_date_confirmed against collected data. Score = collected / required. Pass threshold ≥ 0.8. Auto-pass for refused, voicemail, no_record, dead_end outcomes.',
        type: 'deterministic',
        blocking: false,
        passRate: 89.0,
        trend: [82, 84, 86, 87, 88, 89, 89],
      },
      {
        name: 'Format Validation',
        description: 'All enum fields contain valid values from the allowed set',
        methodology: 'Validates call_outcome ∈ {completed, redirected, no_record, voicemail, refused, dead_end} and employment_status ∈ {full-time, part-time, contract, temporary, intern}. Any invalid value = fail.',
        type: 'deterministic',
        blocking: false,
        passRate: 93.5,
        trend: [90, 91, 92, 93, 93, 94, 93],
      },
    ],
  },
  {
    id: 'quality',
    icon: Smile,
    title: 'Tone & Safety',
    iconBg: 'bg-purple-50 text-purple-600',
    passRate: 98.7,
    evals: [
      {
        name: 'Tone & Professionalism',
        description: 'Agent maintains professional, neutral tone throughout the call',
        methodology: 'LLM judge scores transcript for professionalism, flags argumentative language, inappropriate familiarity, or pressure tactics. Immediate acceptance of refusals also assessed.',
        type: 'llm-judge',
        blocking: false,
        passRate: 98.7,
        trend: [97, 97, 98, 98, 99, 99, 99],
      },
    ],
  },
]

const recentRuns: RecentRun[] = [
  { callId: 'call_a3f8', agent: 'Employment Verification', timestamp: '2 min ago', passRate: 100, passed: 8, total: 8, failures: [] },
  { callId: 'call_b7c2', agent: 'Education Verification', timestamp: '18 min ago', passRate: 87.5, passed: 7, total: 8, failures: ['Required Fields Collected'] },
  { callId: 'call_d1e9', agent: 'Employment Verification', timestamp: '41 min ago', passRate: 100, passed: 8, total: 8, failures: [] },
  { callId: 'call_f4a1', agent: 'Employment Verification', timestamp: '1h ago', passRate: 75.0, passed: 6, total: 8, failures: ['Data Extraction Accuracy', 'No Hallucination'] },
  { callId: 'call_c9b3', agent: 'Education Verification', timestamp: '2h ago', passRate: 87.5, passed: 7, total: 8, failures: ['No Requestor Disclosure'] },
  { callId: 'call_e2d7', agent: 'Employment Verification', timestamp: '3h ago', passRate: 100, passed: 8, total: 8, failures: [] },
]

const failureBreakdown = [
  { eval: 'Required Fields Collected', count: 9, pct: 34.6 },
  { eval: 'Data Extraction Accuracy', count: 7, pct: 26.9 },
  { eval: 'No Hallucination', count: 5, pct: 19.2 },
  { eval: 'No Requestor Disclosure', count: 3, pct: 11.5 },
  { eval: 'Recorded Line Disclosure', count: 1, pct: 3.9 },
  { eval: 'Tone & Professionalism', count: 1, pct: 3.9 },
]

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const typeLabel = (t: EvalDef['type']) => {
  switch (t) {
    case 'deterministic': return { text: 'Code', icon: Code, bg: 'bg-slate-100 text-slate-700' }
    case 'llm-judge': return { text: 'LLM Judge', icon: Cpu, bg: 'bg-violet-100 text-violet-700' }
    case 'hybrid': return { text: 'Hybrid', icon: Activity, bg: 'bg-cyan-100 text-cyan-700' }
  }
}

const rateColor = (rate: number) =>
  rate >= 95 ? 'text-green-600' : rate >= 85 ? 'text-amber-600' : 'text-red-600'

const barColor = (rate: number) =>
  rate >= 95 ? 'bg-green-500' : rate >= 85 ? 'bg-amber-500' : 'bg-red-500'

/* ------------------------------------------------------------------ */
/*  Mini sparkline — pure CSS                                          */
/* ------------------------------------------------------------------ */

function Sparkline({ data, color }: { data: number[]; color: string }) {
  const max = Math.max(...data)
  const min = Math.min(...data, 70)
  const range = max - min || 1
  return (
    <div className="flex items-end gap-[2px] h-5">
      {data.map((v, i) => (
        <div
          key={i}
          className={`w-1 rounded-full ${color}`}
          style={{ height: `${Math.max(((v - min) / range) * 100, 8)}%`, opacity: i === data.length - 1 ? 1 : 0.5 }}
        />
      ))}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Expandable eval row                                                */
/* ------------------------------------------------------------------ */

function EvalRow({ ev }: { ev: EvalDef }) {
  const [open, setOpen] = useState(false)
  const { text, icon: TypeIcon, bg } = typeLabel(ev.type)
  const sparkColor = ev.passRate >= 95 ? 'bg-green-500' : ev.passRate >= 85 ? 'bg-amber-500' : 'bg-red-500'

  return (
    <div className="border-t border-gray-100">
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-3 px-4 py-2.5 text-left hover:bg-gray-50 transition-colors"
      >
        {open ? <ChevronDown className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" /> : <ChevronRight className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />}
        <span className="text-sm text-gray-800 flex-1">{ev.name}</span>
        {ev.blocking && (
          <span className="text-[10px] font-medium bg-red-50 text-red-600 px-1.5 py-0.5 rounded">BLOCKING</span>
        )}
        <span className={`text-[10px] font-medium px-1.5 py-0.5 rounded flex items-center gap-1 ${bg}`}>
          <TypeIcon className="w-3 h-3" />
          {text}
        </span>
        <Sparkline data={ev.trend} color={sparkColor} />
        <span className={`text-sm font-semibold tabular-nums w-14 text-right ${rateColor(ev.passRate)}`}>
          {ev.passRate.toFixed(1)}%
        </span>
      </button>
      {open && (
        <div className="px-4 pb-3 pl-11 space-y-2">
          <p className="text-xs text-gray-500">{ev.description}</p>
          <div className="bg-gray-50 rounded-lg p-3">
            <div className="flex items-center gap-1.5 mb-1">
              <Info className="w-3 h-3 text-gray-400" />
              <span className="text-[11px] font-medium text-gray-600">Methodology</span>
            </div>
            <p className="text-xs text-gray-600 leading-relaxed">{ev.methodology}</p>
          </div>
        </div>
      )}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/*  Main page                                                          */
/* ------------------------------------------------------------------ */

type Tab = 'overview' | 'runs' | 'failures'

export default function Evals() {
  const initialTab = (typeof window !== 'undefined' && (new URLSearchParams(window.location.search).get('tab') as Tab)) || 'overview'
  const [tab, setTab] = useState<Tab>(initialTab)

  const totalEvals = categories.reduce((s, c) => s + c.evals.length, 0)
  const codeEvals = categories.reduce((s, c) => s + c.evals.filter(e => e.type === 'deterministic').length, 0)
  const llmEvals = categories.reduce((s, c) => s + c.evals.filter(e => e.type === 'llm-judge').length, 0)
  const hybridEvals = totalEvals - codeEvals - llmEvals

  const overallRate = categories.reduce((s, c) => s + c.passRate * c.evals.length, 0) / totalEvals

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 mb-1">Evals</h1>
          <p className="text-sm text-gray-500">Automated quality checks on every verification call</p>
        </div>
        <span className="bg-gray-100 text-gray-600 text-xs font-medium px-3 py-1.5 rounded-full flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 bg-green-500 rounded-full animate-pulse" />
          Sample data
        </span>
      </div>

      {/* Summary strip */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        <div className="bg-gradient-to-br from-blue-600 to-blue-700 rounded-xl p-4 text-white">
          <div className="text-2xl font-bold tabular-nums">{overallRate.toFixed(1)}%</div>
          <div className="text-blue-200 text-xs mt-0.5">Overall pass rate</div>
          <div className="text-blue-300 text-[10px] mt-1">50 calls evaluated</div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <div className="flex items-center gap-2 mb-1">
            <Layers className="w-4 h-4 text-gray-400" />
            <span className="text-xs text-gray-500">Pipeline</span>
          </div>
          <div className="text-xl font-bold text-gray-900">{totalEvals} evals</div>
          <div className="text-[11px] text-gray-500 mt-0.5">4 categories</div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <div className="flex items-center gap-2 mb-1">
            <Code className="w-4 h-4 text-gray-400" />
            <span className="text-xs text-gray-500">Deterministic</span>
          </div>
          <div className="text-xl font-bold text-gray-900">{codeEvals} evals</div>
          <div className="text-[11px] text-gray-500 mt-0.5">Code-based, instant</div>
        </div>
        <div className="bg-white rounded-xl border border-gray-200 p-4">
          <div className="flex items-center gap-2 mb-1">
            <Cpu className="w-4 h-4 text-gray-400" />
            <span className="text-xs text-gray-500">LLM Judge</span>
          </div>
          <div className="text-xl font-bold text-gray-900">{llmEvals + hybridEvals} evals</div>
          <div className="text-[11px] text-gray-500 mt-0.5">{hybridEvals > 0 ? `${llmEvals} LLM + ${hybridEvals} hybrid` : 'Model-graded'}</div>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 mb-5 border-b border-gray-200">
        {([
          ['overview', 'Eval Pipeline'],
          ['runs', 'Recent Runs'],
          ['failures', 'Failure Analysis'],
        ] as [Tab, string][]).map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
              tab === key
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Tab: Overview */}
      {tab === 'overview' && (
        <div className="space-y-4">
          {categories.map((cat) => {
            const Icon = cat.icon
            return (
              <div key={cat.id} className="bg-white rounded-xl border border-gray-200 overflow-hidden">
                <div className="flex items-center justify-between px-4 py-3">
                  <div className="flex items-center gap-2.5">
                    <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${cat.iconBg}`}>
                      <Icon className="w-4 h-4" />
                    </div>
                    <div>
                      <span className="font-semibold text-gray-900 text-sm">{cat.title}</span>
                      <span className="text-xs text-gray-400 ml-2">{cat.evals.length} eval{cat.evals.length > 1 ? 's' : ''}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <div className="w-28 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all ${barColor(cat.passRate)}`}
                        style={{ width: `${cat.passRate}%` }}
                      />
                    </div>
                    <span className={`text-lg font-bold tabular-nums ${rateColor(cat.passRate)}`}>
                      {cat.passRate.toFixed(1)}%
                    </span>
                  </div>
                </div>
                {cat.evals.map((ev) => (
                  <EvalRow key={ev.name} ev={ev} />
                ))}
              </div>
            )
          })}

          {/* Methodology note */}
          <div className="bg-slate-50 rounded-xl border border-slate-200 p-5">
            <h3 className="font-semibold text-gray-900 text-sm mb-3 flex items-center gap-2">
              <Activity className="w-4 h-4 text-slate-500" />
              Eval Methodology
            </h3>
            <div className="grid grid-cols-3 gap-4 text-xs text-gray-600">
              <div>
                <div className="flex items-center gap-1.5 mb-1.5">
                  <span className="inline-flex items-center gap-1 bg-slate-100 text-slate-700 px-1.5 py-0.5 rounded text-[10px] font-medium">
                    <Code className="w-3 h-3" /> Code
                  </span>
                </div>
                <p className="leading-relaxed">Deterministic checks run instantly at call completion. Pattern matching, value comparison, and enum validation. Zero cost, zero latency, fully reproducible.</p>
              </div>
              <div>
                <div className="flex items-center gap-1.5 mb-1.5">
                  <span className="inline-flex items-center gap-1 bg-violet-100 text-violet-700 px-1.5 py-0.5 rounded text-[10px] font-medium">
                    <Cpu className="w-3 h-3" /> LLM Judge
                  </span>
                </div>
                <p className="leading-relaxed">Model-graded evals use an LLM to assess transcript quality, data grounding, and tone. Catches nuanced issues code-based checks miss. Run asynchronously post-call.</p>
              </div>
              <div>
                <div className="flex items-center gap-1.5 mb-1.5">
                  <span className="inline-flex items-center gap-1 bg-cyan-100 text-cyan-700 px-1.5 py-0.5 rounded text-[10px] font-medium">
                    <Activity className="w-3 h-3" /> Hybrid
                  </span>
                </div>
                <p className="leading-relaxed">Keyword heuristic for speed, with LLM fallback for edge cases. Balances latency and accuracy — fast path covers 90%+ of cases, LLM handles the long tail.</p>
              </div>
            </div>
            <div className="mt-4 pt-3 border-t border-slate-200 text-xs text-gray-500 flex items-start gap-2">
              <TrendingUp className="w-3.5 h-3.5 mt-0.5 text-slate-400 flex-shrink-0" />
              <span>All evals run automatically on every completed call. Results are persisted via event sourcing and never block call completion — eval failures are captured, not suppressed. The <span className="font-medium text-gray-700">Apple-to-Apple rule</span> drives status derivation: exact string match = verified, any difference = review needed.</span>
            </div>
          </div>
        </div>
      )}

      {/* Tab: Recent Runs */}
      {tab === 'runs' && (
        <div className="bg-white rounded-xl border border-gray-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 text-left text-xs text-gray-500 font-medium">
                <th className="px-4 py-2.5">Call</th>
                <th className="px-4 py-2.5">Agent</th>
                <th className="px-4 py-2.5">Time</th>
                <th className="px-4 py-2.5 text-center">Result</th>
                <th className="px-4 py-2.5 text-right">Pass Rate</th>
                <th className="px-4 py-2.5">Failures</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {recentRuns.map((run) => (
                <tr key={run.callId} className="hover:bg-gray-50 transition-colors">
                  <td className="px-4 py-3 font-mono text-xs text-gray-600">{run.callId}</td>
                  <td className="px-4 py-3 text-gray-800">{run.agent}</td>
                  <td className="px-4 py-3 text-gray-500 text-xs">{run.timestamp}</td>
                  <td className="px-4 py-3 text-center">
                    {run.passRate === 100 ? (
                      <span className="inline-flex items-center gap-1 text-xs font-medium text-green-600">
                        <CheckCircle className="w-3.5 h-3.5" /> {run.passed}/{run.total}
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 text-xs font-medium text-amber-600">
                        <AlertTriangle className="w-3.5 h-3.5" /> {run.passed}/{run.total}
                      </span>
                    )}
                  </td>
                  <td className={`px-4 py-3 text-right font-semibold tabular-nums ${rateColor(run.passRate)}`}>
                    {run.passRate.toFixed(1)}%
                  </td>
                  <td className="px-4 py-3">
                    {run.failures.length === 0 ? (
                      <span className="text-xs text-gray-400">—</span>
                    ) : (
                      <div className="flex flex-wrap gap-1">
                        {run.failures.map((f) => (
                          <span key={f} className="text-[10px] bg-red-50 text-red-600 px-1.5 py-0.5 rounded font-medium">
                            {f}
                          </span>
                        ))}
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Tab: Failure Analysis */}
      {tab === 'failures' && (
        <div className="space-y-4">
          <div className="bg-white rounded-xl border border-gray-200 p-5">
            <h3 className="font-semibold text-gray-900 text-sm mb-1">Failure Distribution</h3>
            <p className="text-xs text-gray-500 mb-4">26 total failures across 50 evaluated calls (last 7 days)</p>
            <div className="space-y-3">
              {failureBreakdown.map((f) => (
                <div key={f.eval} className="flex items-center gap-3">
                  <span className="text-xs text-gray-700 w-48 flex-shrink-0 truncate">{f.eval}</span>
                  <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div className="h-full bg-red-400 rounded-full" style={{ width: `${f.pct}%` }} />
                  </div>
                  <span className="text-xs text-gray-500 tabular-nums w-8 text-right">{f.count}</span>
                  <span className="text-xs text-gray-400 tabular-nums w-12 text-right">{f.pct.toFixed(1)}%</span>
                </div>
              ))}
            </div>
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-900 text-sm mb-3 flex items-center gap-2">
                <XCircle className="w-4 h-4 text-red-500" />
                Common Failure Patterns
              </h3>
              <div className="space-y-3 text-xs text-gray-600">
                <div className="bg-red-50 rounded-lg p-3">
                  <div className="font-medium text-red-800 mb-1">Incomplete field collection on redirected calls</div>
                  <p className="text-red-600">When a call gets redirected, the agent sometimes ends the call before gathering all required fields from the new contact.</p>
                </div>
                <div className="bg-red-50 rounded-lg p-3">
                  <div className="font-medium text-red-800 mb-1">Date format normalization errors</div>
                  <p className="text-red-600">Employer says "March of twenty-twenty" — agent extracts "03/2020" but transcript grounding check flags the format transformation as unverifiable.</p>
                </div>
                <div className="bg-red-50 rounded-lg p-3">
                  <div className="font-medium text-red-800 mb-1">Implicit requestor disclosure</div>
                  <p className="text-red-600">Agent doesn't name the requestor but uses phrasing like "confirming for a potential employer" which reveals intent.</p>
                </div>
              </div>
            </div>
            <div className="bg-white rounded-xl border border-gray-200 p-5">
              <h3 className="font-semibold text-gray-900 text-sm mb-3 flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-green-500" />
                Improvement Actions
              </h3>
              <div className="space-y-3 text-xs">
                <div className="flex items-start gap-2.5 p-3 bg-green-50 rounded-lg">
                  <CheckCircle className="w-3.5 h-3.5 text-green-600 mt-0.5 flex-shrink-0" />
                  <div>
                    <div className="font-medium text-green-800">Prompt tuning: redirect handling</div>
                    <p className="text-green-600 mt-0.5">Added explicit instruction to re-gather required fields after redirect. Completeness improved 82% → 89%.</p>
                  </div>
                </div>
                <div className="flex items-start gap-2.5 p-3 bg-green-50 rounded-lg">
                  <CheckCircle className="w-3.5 h-3.5 text-green-600 mt-0.5 flex-shrink-0" />
                  <div>
                    <div className="font-medium text-green-800">Prompt tuning: disclosure phrasing</div>
                    <p className="text-green-600 mt-0.5">Replaced "confirming employment for" with neutral opener. Disclosure violations dropped from 8% → 4%.</p>
                  </div>
                </div>
                <div className="flex items-start gap-2.5 p-3 bg-blue-50 rounded-lg">
                  <AlertTriangle className="w-3.5 h-3.5 text-blue-600 mt-0.5 flex-shrink-0" />
                  <div>
                    <div className="font-medium text-blue-800">Planned: date normalization pipeline</div>
                    <p className="text-blue-600 mt-0.5">Add a post-extraction normalization step that preserves both raw transcript text and structured date values.</p>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

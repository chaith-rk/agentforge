import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Phone, Briefcase, GraduationCap } from 'lucide-react'
import { api } from '../lib/api'

const US_STATES = ['AL','AK','AZ','AR','CA','CO','CT','DE','FL','GA','HI','ID','IL','IN','IA','KS','KY','LA','ME','MD','MA','MI','MN','MS','MO','MT','NE','NV','NH','NJ','NM','NY','NC','ND','OH','OK','OR','PA','RI','SC','SD','TN','TX','UT','VT','VA','WA','WV','WI','WY']
const MONTHS = ['January','February','March','April','May','June','July','August','September','October','November','December']
const YEARS = Array.from({ length: 12 }, (_, i) => 2026 - i)

const TEST_DATA = {
  subject_name: 'Kevin Strickland',
  phone_number: '',
  employer_company_name: "Surgeon's Choice",
  position: 'Surgical Technician',
  month_started: 'January',
  year_started: '2021',
  still_work_here: false,
  month_ended: 'December',
  year_ended: '2024',
  is_self_employed: false,
  company_address: '4521 Medical Center Blvd',
  city: 'Tampa',
  state: 'FL',
  zip_code: '33612',
}

const EMPTY_DATA = {
  subject_name: '', phone_number: '', employer_company_name: '', position: '',
  month_started: '', year_started: '', still_work_here: false, month_ended: '',
  year_ended: '', is_self_employed: false, company_address: '', city: '', state: '', zip_code: '',
}

export default function NewCall() {
  const navigate = useNavigate()
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null)
  const [prefill, setPrefill] = useState(false)
  const [form, setForm] = useState(EMPTY_DATA)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handlePrefill = (checked: boolean) => {
    setPrefill(checked)
    if (checked) {
      setForm({ ...TEST_DATA, phone_number: form.phone_number })
    } else {
      setForm({ ...EMPTY_DATA, phone_number: form.phone_number })
    }
  }

  const set = (key: string, value: string | boolean) => setForm((f) => ({ ...f, [key]: value }))

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!form.phone_number) { setError('Phone number is required'); return }
    setLoading(true); setError('')
    try {
      const { session_id } = await api.initiateCall({
        agent_config_id: 'employment_verification_v1',
        subject_name: form.subject_name,
        phone_number: form.phone_number,
        candidate_claims: {
          employer_company_name: form.employer_company_name,
          position: form.position,
          month_started: form.month_started,
          year_started: form.year_started,
          month_ended: form.still_work_here ? '' : form.month_ended,
          year_ended: form.still_work_here ? '' : form.year_ended,
          is_self_employed: form.is_self_employed,
          still_work_here: form.still_work_here,
          company_address: form.company_address,
          city: form.city,
          state: form.state,
          zip_code: form.zip_code,
        },
      })
      navigate(`/calls/${session_id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to initiate call')
      setLoading(false)
    }
  }

  const inputCls = 'w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent'
  const labelCls = 'block text-sm font-medium text-gray-700 mb-1'

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-1">New Verification Call</h1>
      <p className="text-sm text-gray-500 mb-6">Select an agent type and enter candidate information</p>

      {/* Agent selector */}
      <div className="mb-6">
        <h2 className="text-sm font-semibold text-gray-700 uppercase tracking-wider mb-3">Select Agent</h2>
        <div className="grid grid-cols-2 gap-3">
          <button
            type="button"
            onClick={() => setSelectedAgent('employment_verification_v1')}
            className={`text-left p-4 rounded-xl border-2 transition-colors ${selectedAgent === 'employment_verification_v1' ? 'border-blue-500 bg-blue-50' : 'border-gray-200 bg-white hover:border-gray-300'}`}
          >
            <div className="flex items-center gap-2.5 mb-2">
              <Briefcase className="w-5 h-5 text-blue-600" />
              <span className="font-semibold text-gray-900 text-sm">Employment Verification</span>
            </div>
            <p className="text-xs text-gray-500">Verify employment history, dates, and title with employer HR</p>
          </button>
          <div className="text-left p-4 rounded-xl border-2 border-gray-100 bg-gray-50 opacity-60">
            <div className="flex items-center gap-2.5 mb-2">
              <GraduationCap className="w-5 h-5 text-gray-400" />
              <span className="font-semibold text-gray-600 text-sm">Education Verification</span>
              <span className="text-xs bg-gray-200 text-gray-500 px-2 py-0.5 rounded-full ml-auto">Coming Soon</span>
            </div>
            <p className="text-xs text-gray-400">Verify degree, institution, and graduation with registrar</p>
          </div>
        </div>
      </div>

      {/* Form */}
      {selectedAgent && (
        <form onSubmit={handleSubmit} className="bg-white rounded-xl border border-gray-200 p-6">
          {/* Pre-fill toggle */}
          <div className="flex items-center gap-2.5 mb-5 p-3 bg-blue-50 rounded-lg border border-blue-100">
            <input
              type="checkbox"
              id="prefill"
              checked={prefill}
              onChange={(e) => handlePrefill(e.target.checked)}
              className="w-4 h-4 text-blue-600 rounded"
            />
            <label htmlFor="prefill" className="text-sm font-medium text-blue-800 cursor-pointer">
              Pre-fill with test data
            </label>
            <span className="text-xs text-blue-600 ml-1">(Kevin Strickland / Surgeon's Choice)</span>
          </div>

          <div className="grid grid-cols-2 gap-4">
            {/* Candidate info */}
            <div className="col-span-2">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Candidate</h3>
            </div>
            <div>
              <label className={labelCls}>Candidate Name <span className="text-red-500">*</span></label>
              <input className={inputCls} value={form.subject_name} onChange={(e) => set('subject_name', e.target.value)} placeholder="Full name" required />
            </div>
            <div>
              <label className={labelCls}>Phone Number to Call <span className="text-red-500">*</span></label>
              <input className={inputCls} value={form.phone_number} onChange={(e) => set('phone_number', e.target.value)} placeholder="+12025551234" type="tel" required />
            </div>

            {/* Employment info */}
            <div className="col-span-2 mt-2">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Employment Details</h3>
            </div>
            <div>
              <label className={labelCls}>Employer Company Name <span className="text-red-500">*</span></label>
              <input className={inputCls} value={form.employer_company_name} onChange={(e) => set('employer_company_name', e.target.value)} placeholder="Company name" required />
            </div>
            <div>
              <label className={labelCls}>Position / Title <span className="text-red-500">*</span></label>
              <input className={inputCls} value={form.position} onChange={(e) => set('position', e.target.value)} placeholder="Job title" required />
            </div>

            <div>
              <label className={labelCls}>Month Started <span className="text-red-500">*</span></label>
              <select className={inputCls} value={form.month_started} onChange={(e) => set('month_started', e.target.value)} required>
                <option value="">Select month</option>
                {MONTHS.map((m) => <option key={m} value={m}>{m}</option>)}
              </select>
            </div>
            <div>
              <label className={labelCls}>Year Started <span className="text-red-500">*</span></label>
              <select className={inputCls} value={form.year_started} onChange={(e) => set('year_started', e.target.value)} required>
                <option value="">Select year</option>
                {YEARS.map((y) => <option key={y} value={String(y)}>{y}</option>)}
              </select>
            </div>

            <div className="col-span-2 flex items-center gap-4">
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={form.is_self_employed} onChange={(e) => set('is_self_employed', e.target.checked)} className="w-4 h-4 text-blue-600 rounded" />
                <span className="text-sm text-gray-700">Self-employed</span>
              </label>
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={form.still_work_here} onChange={(e) => set('still_work_here', e.target.checked)} className="w-4 h-4 text-blue-600 rounded" />
                <span className="text-sm text-gray-700">Still works here</span>
              </label>
            </div>

            {!form.still_work_here && (
              <>
                <div>
                  <label className={labelCls}>Month Ended</label>
                  <select className={inputCls} value={form.month_ended} onChange={(e) => set('month_ended', e.target.value)}>
                    <option value="">Select month</option>
                    {MONTHS.map((m) => <option key={m} value={m}>{m}</option>)}
                  </select>
                </div>
                <div>
                  <label className={labelCls}>Year Ended</label>
                  <select className={inputCls} value={form.year_ended} onChange={(e) => set('year_ended', e.target.value)}>
                    <option value="">Select year</option>
                    {YEARS.map((y) => <option key={y} value={String(y)}>{y}</option>)}
                  </select>
                </div>
              </>
            )}

            {/* Address */}
            <div className="col-span-2 mt-2">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3">Company Address (Optional)</h3>
            </div>
            <div className="col-span-2">
              <label className={labelCls}>Street Address</label>
              <input className={inputCls} value={form.company_address} onChange={(e) => set('company_address', e.target.value)} placeholder="Street address" />
            </div>
            <div>
              <label className={labelCls}>City</label>
              <input className={inputCls} value={form.city} onChange={(e) => set('city', e.target.value)} placeholder="City" />
            </div>
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className={labelCls}>State</label>
                <select className={inputCls} value={form.state} onChange={(e) => set('state', e.target.value)}>
                  <option value="">—</option>
                  {US_STATES.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>
              <div>
                <label className={labelCls}>Zip Code</label>
                <input className={inputCls} value={form.zip_code} onChange={(e) => set('zip_code', e.target.value)} placeholder="33601" maxLength={5} />
              </div>
            </div>
          </div>

          {error && <div className="mt-4 p-3 bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg">{error}</div>}

          <div className="mt-6 flex items-center justify-end gap-3">
            <button type="button" onClick={() => setSelectedAgent(null)} className="px-4 py-2 text-sm text-gray-600 hover:text-gray-900">Cancel</button>
            <button
              type="submit"
              disabled={loading}
              className="flex items-center gap-2 bg-blue-600 text-white px-6 py-2.5 rounded-lg text-sm font-semibold hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Phone className="w-4 h-4" />
              {loading ? 'Placing Call...' : 'Place Call'}
            </button>
          </div>
        </form>
      )}
    </div>
  )
}

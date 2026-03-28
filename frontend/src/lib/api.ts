const API_BASE = import.meta.env.VITE_API_BASE || '/api'
const API_KEY = import.meta.env.VITE_API_KEY || ''

export interface CallStats {
  total_calls: number
  active_calls: number
  completed_calls: number
  success_rate: number
  avg_duration_seconds: number
  calls_today: number
  calls_this_week: number
  outcomes: Record<string, number>
}

export interface AgentSummary {
  agent_id: string
  agent_name: string
  version: string
  description: string
  field_count: number
  state_count: number
  status: string
}

export interface AgentDetail {
  agent_id: string
  agent_name: string
  version: string
  description: string
  status: string
  form_fields: FormField[]
  all_fields: FormField[]
  states: AgentState[]
  compliance_rules: string[]
  voice_config: Record<string, unknown>
}

export interface FormField {
  field_name: string
  display_name: string
  type: string
  required: boolean
  enum_values?: string[] | null
  description: string
  question: string
  is_candidate_input: boolean
}

export interface AgentState {
  name: string
  description: string
  is_terminal: boolean
}

export interface Call {
  session_id: string
  current_state: string
  outcome: string
  status?: string
  agent_config_id?: string
  collected_data: Record<string, unknown>
  transcript: Array<{ role: string; content: string }>
  created_at: string
  updated_at: string
}

export interface CallResult {
  overall_status?: string
  status?: string
  call_outcome?: string
  fields?: FieldVerification[]
  verifier_name?: string
  verifier_title?: string
}

export interface FieldVerification {
  field_name: string
  display_name: string
  candidate_value: unknown
  employer_value: unknown
  status: string
  match: boolean | null
}

export interface InitiateCallRequest {
  agent_config_id: string
  subject_name: string
  phone_number: string
  candidate_claims: Record<string, unknown>
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', 'X-API-Key': API_KEY, ...((options?.headers as Record<string, string>) ?? {}) },
    ...options,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`API ${res.status}: ${text || res.statusText}`)
  }
  return res.json()
}

export const api = {
  getStats: () => apiFetch<CallStats>('/stats'),
  getCalls: (limit = 50, offset = 0) => apiFetch<Call[]>(`/calls?limit=${limit}&offset=${offset}`),
  getCall: (id: string) => apiFetch<Call>(`/calls/${id}`),
  getCallResult: (id: string) => apiFetch<CallResult>(`/calls/${id}/result`),
  getAgents: () => apiFetch<AgentSummary[]>('/agents'),
  getAgent: (id: string) => apiFetch<AgentDetail>(`/agents/${id}`),
  initiateCall: (data: InitiateCallRequest) =>
    apiFetch<{ session_id: string; status: string; vapi_call_id: string }>('/calls/initiate', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  stopCall: (id: string) =>
    apiFetch<{ status: string }>(`/calls/${id}/stop`, { method: 'POST' }),
}

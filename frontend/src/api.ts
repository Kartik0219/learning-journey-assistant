// Typed client for the Flask JSON API (src/deliver/spa_api.py).
//
// The SPA is served by Flask at /app/ on the same origin, so the session
// cookie set by /login authenticates every call. A 401 means "not signed
// in" - send the browser to the real login page and come back here after.

export interface SessionInfo {
  role: 'student' | 'staff' | 'admin'
  student_id: number | null
  students: { id: number; label: string }[]
}

export interface Gap {
  evidence: string
  severity: 'low' | 'medium' | 'high'
  confidence: number
}

export interface QuizQuestion {
  id: number
  question_text: string
  question_type: string
  answer_title: string | null
  answer_text: string | null
}

export interface Recommendation {
  id: number
  method: string
  material_text: string
  source_title: string | null
}

export interface Outcome {
  id: number
  code: string
  description: string
  subject_code: string
  mastery_score: number | null
  mastery_pct: number | null
  explanation: string | null
  gaps: Gap[]
  recommendation: Recommendation | null
  quiz_questions: QuizQuestion[]
}

export interface Dashboard {
  student: { id: number; display_name: string }
  outcomes: Outcome[]
  priority_outcomes: Outcome[]
  subjects: { code: string; average_mastery_pct: number }[]
}

export interface ResultRow {
  id: number
  assessment: string
  score: number | null
  feedback: string | null
  silo_codes: string[]
}

export interface SubjectResults {
  code: string
  name: string
  average_score: number | null
  assessments: ResultRow[]
  learning_outcomes: { code: string; description: string }[]
}

export interface Results {
  student: { id: number; display_name: string }
  subjects: SubjectResults[]
}

export class ApiError extends Error {
  status: number
  code: string
  constructor(status: number, code: string, message: string) {
    super(message)
    this.status = status
    this.code = code
  }
}

export const LOGIN_URL = '/login?next=/app/'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, { credentials: 'same-origin', ...init })
  if (response.status === 401) {
    window.location.assign(LOGIN_URL)
    throw new ApiError(401, 'not_signed_in', 'Redirecting to sign in')
  }
  const body = await response.json().catch(() => ({}))
  if (!response.ok) {
    throw new ApiError(response.status, body.error ?? 'error', body.message ?? `Request failed (${response.status})`)
  }
  return body as T
}

export const api = {
  session: () => request<SessionInfo>('/api/session'),
  dashboard: (studentId: number) => request<Dashboard>(`/api/students/${studentId}/dashboard`),
  results: (studentId: number) => request<Results>(`/api/students/${studentId}/results`),
  markPractised: (recommendationId: number) =>
    request<{ ok: boolean }>(`/api/recommendations/${recommendationId}/practice`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: '{}',
    }),
}

export type MasteryStatus = 'atRisk' | 'developing' | 'proficient' | 'mastered'

// Same bands the dashboard legend shows.
export function masteryBand(pct: number): { status: MasteryStatus; label: string } {
  if (pct >= 80) return { status: 'mastered', label: 'Mastered' }
  if (pct >= 65) return { status: 'proficient', label: 'Proficient' }
  if (pct >= 50) return { status: 'developing', label: 'Developing' }
  return { status: 'atRisk', label: 'At risk' }
}

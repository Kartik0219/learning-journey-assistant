// Typed client for the Flask JSON API (src/deliver/spa_api.py).
//
// The SPA is served by Flask at /app/ on the same origin, so the session
// cookie set by /login authenticates every call. A 401 means "not signed
// in" - send the browser to the real login page and come back here after.

export interface SessionInfo {
  role: 'student'
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
  answer_url: string | null
}

export interface Recommendation {
  id: number
  method: string
  material_text: string
  source_title: string | null
  source_url: string | null
  source_provenance: 'subject' | 'curated' | null
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
  weight: number | null
  weighted_score: number | null
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

export interface Material {
  title: string
  passage_text: string
  learning_outcome_code: string | null
  source_url: string | null
  provenance: 'subject' | 'curated'
  resource_type: 'reading' | 'video'
  mastery_pct: number | null
}

export interface ResourceSilo {
  code: string
  description: string | null
  mastery_pct: number | null
  materials: Material[]
}

export interface Resources {
  student: { id: number; display_name: string }
  subjects: { code: string; silos: ResourceSilo[] }[]
}

export interface LibraryMaterial {
  title: string
  passage_text: string
  source_url: string | null
  provenance: 'subject' | 'curated'
  resource_type: 'reading' | 'video'
}

export interface LibrarySilo {
  code: string
  description: string | null
  materials: LibraryMaterial[]
}

export interface Library {
  subjects: { code: string; silos: LibrarySilo[] }[]
}

export interface AiInsight {
  student: { id: number; display_name: string }
  enabled: boolean
  error: string | null
  insight: null | {
    learningOutcomes: { code: string; title: string; status: string; masteryPercentage: number; evidenceQuote: string }[]
    strengths: string[]
    focusAreas: { topic: string; recommendedStep: string; resourceLinkOrModule: string }[]
    disclaimer: string
  }
}

export interface InsightSubject {
  code: string
  name: string | null
  total: number | null
  band: string
  tone: MasteryStatus | 'neutral'
  weighted: boolean
  assessments_counted: number
  weakest_outcomes: { code: string; mastery_pct: number; description: string }[]
  biggest_lever: { assessment: string; weight: number; score: number } | null
  paragraphs: string[]
}

export interface Insight {
  student: { id: number; display_name: string }
  method: 'deterministic'
  generated_from: { subjects: number; assessments: number }
  headline: string
  average_total: number | null
  average_band: string
  average_tone: MasteryStatus | 'neutral'
  subjects: InsightSubject[]
  themes: { label: string; count: number; advice: string }[]
  this_week: string[]
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
  resources: (studentId: number) => request<Resources>(`/api/students/${studentId}/resources`),
  library: () => request<Library>('/api/library'),
  insight: (studentId: number) => request<Insight>(`/api/students/${studentId}/insight`),
  // The LLM call can stall on a cold host or a saturated free tier; give
  // up after 30 s so the page never hangs on an optional extra.
  aiInsight: (studentId: number) =>
    request<AiInsight>(`/api/students/${studentId}/ai-insight`, { signal: AbortSignal.timeout(30_000) }),
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

// A subject total mapped to La Trobe's grade bands. Formative, not an official grade.
export function performanceBand(total: number): { status: MasteryStatus; label: string } {
  if (total >= 80) return { status: 'mastered', label: 'High Distinction' }
  if (total >= 70) return { status: 'proficient', label: 'Distinction' }
  if (total >= 60) return { status: 'proficient', label: 'Credit' }
  if (total >= 50) return { status: 'developing', label: 'Pass' }
  return { status: 'atRisk', label: 'Fail' }
}

// Mastery to one decimal place, from the unrounded score the backend stores.
export function masteryPct(outcome: Outcome): number | null {
  return outcome.mastery_score === null ? null : Math.round(outcome.mastery_score * 1000) / 10
}

const hasWeights = (rows: ResultRow[]) => rows.length > 0 && rows.every((r) => r.weight && r.score !== null)

// Weight-averaged score when the dataset has weights, plain mean otherwise.
export function weightedAverage(rows: ResultRow[]): number | null {
  const scored = rows.filter((r) => r.score !== null)
  if (!scored.length) return null
  if (hasWeights(scored)) {
    const w = scored.reduce((sum, r) => sum + (r.weight ?? 0), 0)
    return scored.reduce((sum, r) => sum + (r.score ?? 0) * (r.weight ?? 0), 0) / w
  }
  return scored.reduce((sum, r) => sum + (r.score ?? 0), 0) / scored.length
}

// The subject total: the sum of weighted scores (the workbook's own figure) when present.
export function subjectTotal(subject: SubjectResults): number | null {
  const rows = subject.assessments
  if (rows.length && rows.every((r) => r.weighted_score !== null)) {
    return Math.round(rows.reduce((sum, r) => sum + (r.weighted_score ?? 0), 0) * 100) / 100
  }
  return subject.average_score
}

export function usesWeights(rows: ResultRow[]): boolean {
  return hasWeights(rows)
}

// "spaced_practice" -> "Spaced practice"
export function humanise(key: string): string {
  const text = key.replace(/_/g, ' ')
  return text.charAt(0).toUpperCase() + text.slice(1)
}

// "CSE1OOF - Central examination" -> "Central examination"
export function assessmentName(name: string): string {
  const cut = name.indexOf(' - ')
  return cut === -1 ? name : name.slice(cut + 3)
}

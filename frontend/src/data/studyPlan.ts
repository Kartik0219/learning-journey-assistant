// Study-plan model for the "AI study plan" page.
//
// Design (per the project proposal): AI is used only for the cheap, low-risk
// step of summarising marker feedback and mapping it to SILOs. The resources,
// activities and quizzes are PRE-BUILT / lecturer-reviewed - selected per SILO,
// never generated at request time - so outputs stay grounded, consistent and
// reviewable. This module is a placeholder for that pipeline.
import type { MasteryStatus } from './dashboard'
import { studentDashboardSubjects } from './studentDashboard'

export interface AssessmentFeedback {
  name: string
  score: number
  weightPct: number
  feedback: string
}

export interface SiloPlan {
  silo: string
  siloId: string
  masteryPercentage: number
  status: MasteryStatus
  statusLabel: string
  feedbackSummary: string
  weakness: string
  assessments: AssessmentFeedback[]
  resources: string[]
  activities: string[]
  quizzes: string[]
}

function shortTopic(description: string): string {
  return description.split(/;|,| to | and /)[0].trim()
}

export const studyPlanSubjectCodes = Object.keys(studentDashboardSubjects)

// Stable fingerprint of the assessment inputs for a subject (scores, weights,
// feedback, SILO mapping). Regeneration is only offered when this changes.
export function assessmentFingerprint(code: string): string {
  const subject = studentDashboardSubjects[code]
  if (!subject) return '0'
  const parts: string[] = []
  for (const outcome of subject.learningOutcomes) {
    for (const a of outcome.assessments ?? []) {
      parts.push(`${outcome.name}|${a.name}|${a.score}|${a.weightPct}|${a.feedback}`)
    }
  }
  const str = parts.join('¶')
  let hash = 5381
  for (let i = 0; i < str.length; i += 1) hash = ((hash << 5) + hash + str.charCodeAt(i)) | 0
  return String(hash >>> 0)
}

// Step 1 (AI, real time): condense the marker feedback for one SILO into a
// short, plain-language read. Placeholder - no model call yet.
function summariseFeedback(topic: string, items: AssessmentFeedback[]): string {
  if (items.length === 0) return `No marker feedback yet references ${topic}.`
  const lowest = [...items].sort((a, b) => a.score - b.score)[0]
  return `Across ${items.length} assessment${items.length > 1 ? 's' : ''}, the feedback consistently flags ${topic} as needing more consistent application and clearer justification of decisions. The clearest signal is ${lowest.name} (${lowest.score}/100).`
}

export function buildStudyPlan(code: string): SiloPlan[] {
  const subject = studentDashboardSubjects[code]
  if (!subject) return []

  return subject.learningOutcomes.map((outcome, siloIndex) => {
    const [siloId, ...rest] = outcome.name.split(' · ')
    const description = rest.join(' · ')
    const topic = shortTopic(description)
    const assessments: AssessmentFeedback[] = [...(outcome.assessments ?? [])]
      .sort((a, b) => a.score - b.score)
      .map((a) => ({ name: a.name, score: a.score, weightPct: a.weightPct, feedback: a.feedback }))

    const feedbackSummary = summariseFeedback(topic, assessments)
    const weakness = `Weighted mastery ${outcome.masteryPercentage}% (${outcome.statusLabel}). Mapped weakness: applying and explaining ${topic}.`

    // Step 3: select pre-built items for this SILO from the subject catalogue.
    const ref = `${code}-${siloId}`
    const resources = [
      `${code} topic notes ${siloIndex + 2}.1 — ${topic}`,
      `Worked examples pack ${ref}-WE`,
      `Reading list ${ref}-R: foundational material for ${topic}`,
    ]
    const activities = [
      `Guided practice ${ref}-A1: rework a past task on ${topic} against the rubric`,
      `Concept check ${ref}-A2: explain ${topic} in your own words, then compare with the model answer`,
      `Peer review ${ref}-A3: mark a sample response for ${topic} and justify the grade`,
    ]
    const quizzes = [
      `Adaptive quiz ${ref}-Q1 — ${topic} (10 items, difficulty adjusts to your answers)`,
      `Retrieval quiz ${ref}-Q2 — mixed ${siloId} questions (spaced over two weeks)`,
    ]

    return {
      silo: outcome.name,
      siloId,
      masteryPercentage: outcome.masteryPercentage,
      status: outcome.status,
      statusLabel: outcome.statusLabel,
      feedbackSummary,
      weakness,
      assessments,
      resources,
      activities,
      quizzes,
    }
  })
}

// Placeholder "AI" study-plan generator. Derives a weakness reading and a set
// of study actions for each SILO from the same weighted-mastery data and marker
// feedback used elsewhere. No live model call yet.
import type { MasteryStatus } from './dashboard'
import { studentDashboardSubjects } from './studentDashboard'

export interface SiloPlan {
  silo: string
  siloId: string
  masteryPercentage: number
  status: MasteryStatus
  statusLabel: string
  weakness: string
  plan: string[]
  resources: string[]
}

function shortTopic(description: string): string {
  return description.split(/;|,| to | and /)[0].trim()
}

export const studyPlanSubjectCodes = Object.keys(studentDashboardSubjects)

export function buildStudyPlan(code: string): SiloPlan[] {
  const subject = studentDashboardSubjects[code]
  if (!subject) return []

  return subject.learningOutcomes.map((outcome) => {
    const [siloId, ...rest] = outcome.name.split(' · ')
    const description = rest.join(' · ')
    const topic = shortTopic(description)
    const weakest = [...(outcome.assessments ?? [])].sort((a, b) => a.score - b.score)[0]

    const weakness = weakest
      ? `Weighted mastery is ${outcome.masteryPercentage}% (${outcome.statusLabel}). The lowest evidence is ${weakest.name} at ${weakest.score}/100, and the marker feedback there points to unresolved gaps in ${topic}.`
      : `Weighted mastery is ${outcome.masteryPercentage}% (${outcome.statusLabel}); there is not yet enough assessment evidence for a detailed read.`

    const plan = [
      `Revisit the subject material on ${topic}. Write a one-page summary in your own words and list every term or step you are unsure of.`,
      weakest
        ? `Redo the ${weakest.name} task under timed conditions, then mark it against the rubric and note each point you lost and why.`
        : `Work through past questions covering ${siloId} and self-mark against the rubric.`,
      `Do a short focused practice set on ${siloId}, aiming for 80%+ before your next ${code} assessment. Book a consultation if you stall on the same step twice.`,
    ]

    const resources = [
      `${code} subject notes — the section covering ${topic}`,
      `Worked examples and practice problems for ${siloId}`,
      `Short video walkthrough: ${topic}`,
      `Study strategy: spaced practice and self-testing on ${siloId}`,
    ]

    return {
      silo: outcome.name,
      siloId,
      masteryPercentage: outcome.masteryPercentage,
      status: outcome.status,
      statusLabel: outcome.statusLabel,
      weakness,
      plan,
      resources,
    }
  })
}

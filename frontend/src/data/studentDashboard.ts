// Second dashboard: real mastery figures for student STU0001, derived from the
// CSE results workbook (studentAssessments.ts) using weighted SILO mastery:
//
//   mastery(SILO) = Σ (score × weight) / Σ weight
//
// over the assessments whose SILO list includes that outcome. Bands:
//   < 50  At risk   ·  50–65  Developing  ·  65–80  Proficient  ·  ≥ 80  Mastered
import type { DashboardSubject, LearningOutcome, MasteryStatus } from './dashboard'
import { studentResults, studentSummary, subjectSilos } from './studentAssessments'

function siloIds(text: string): string[] {
  return Array.from(new Set(text.match(/SILO\d+/g) ?? []))
}

function round(value: number): number {
  return Math.round(value * 10) / 10
}

function band(pct: number): { status: MasteryStatus; statusLabel: string } {
  if (pct >= 80) return { status: 'mastered', statusLabel: 'Mastered' }
  if (pct >= 65) return { status: 'proficient', statusLabel: 'Proficient' }
  if (pct >= 50) return { status: 'developing', statusLabel: 'Developing' }
  return { status: 'atRisk', statusLabel: 'At risk' }
}

// Grade band for a subject's weighted total (shared with the Results overview page).
export function performanceBand(total: number): string {
  if (total < 50) return 'Fail'
  if (total < 60) return 'Pass'
  if (total < 70) return 'Credit'
  if (total < 80) return 'Distinction'
  return 'High Distinction'
}

function actionFor(statusLabel: string): string {
  switch (statusLabel) {
    case 'Mastered':
      return 'Strength - maintain your current approach.'
    case 'Proficient':
      return 'On track - keep reinforcing this outcome to push toward mastery.'
    case 'Developing':
      return 'Consolidate this outcome with focused practice before the next assessment.'
    default:
      return 'Start here - this is a priority gap this cycle.'
  }
}

function siloName(id: string, description: string): string {
  return `${id} · ${description}`
}

function buildSubject(code: string): DashboardSubject {
  const results = studentResults.find((subject) => subject.code === code)
  const silos = subjectSilos[code] ?? []
  if (!results) {
    return {
      code,
      label: code,
      overallMasteryPercentage: 0,
      priorityFocusAreas: 0,
      assessmentsAnalysed: 0,
      masteryTrend: [],
      nextSteps: [],
      recommendedResources: [],
      learningOutcomes: [],
    }
  }

  const learningOutcomes: LearningOutcome[] = silos.map((silo) => {
    const contributing = results.assessments.filter((assessment) =>
      siloIds(assessment.silos).includes(silo.id),
    )
    const sumWeight = contributing.reduce((total, a) => total + a.weight, 0)
    const sumWeighted = contributing.reduce((total, a) => total + a.score * a.weight, 0)
    const masteryPercentage = sumWeight ? round(sumWeighted / sumWeight) : 0
    const { status, statusLabel } = band(masteryPercentage)
    // Weakest-scoring assessment first - its feedback is the most actionable.
    const byScore = [...contributing].sort((a, b) => a.score - b.score)

    return {
      name: siloName(silo.id, silo.description),
      masteryPercentage,
      status,
      statusLabel,
      assessments: byScore.map((a) => ({
        name: a.assessment,
        weightPct: Math.round(a.weight * 100),
        score: a.score,
        feedback: a.feedback,
        silos: siloIds(a.silos).sort(),
      })),
      recommendedAction: actionFor(statusLabel),
    }
  })

  // Keep display order as SILO1, SILO2, SILO3... (the order in subjectSilos).

  // Cumulative weighted mastery after each assessment, in the order they were sat.
  let runningWeight = 0
  let runningWeighted = 0
  const masteryTrend = results.assessments.map((assessment) => {
    runningWeight += assessment.weight
    runningWeighted += assessment.score * assessment.weight
    return round(runningWeighted / runningWeight)
  })

  const byMastery = [...learningOutcomes].sort((a, b) => a.masteryPercentage - b.masteryPercentage)
  const weakest = byMastery[0]
  const secondWeakest = byMastery[1] ?? weakest

  return {
    code,
    label: code,
    overallMasteryPercentage: round(results.total),
    priorityFocusAreas: learningOutcomes.filter((outcome) => outcome.masteryPercentage < 65).length,
    assessmentsAnalysed: results.assessments.length,
    masteryTrend,
    nextSteps: [
      {
        text: 'Rework your lowest-scoring task with the marker feedback for ',
        emphasis: weakest.name,
        suffix: ' open beside you.',
      },
      {
        text: 'Complete an adaptive quiz targeting ',
        emphasis: weakest.name.split(' · ')[0],
        suffix: ' (6 questions, aimed at your gap).',
      },
      {
        text: 'Revisit the subject topic notes for ',
        emphasis: secondWeakest.name.split(' · ')[0],
        suffix: ' before the next assessment.',
      },
    ],
    recommendedResources: [
      `${weakest.name.split(' · ')[0]} refresher - targeted at your weakest outcome`,
      `Worked examples for ${secondWeakest.name.split(' · ')[0]}`,
      'Study strategy: spaced practice across your focus outcomes',
    ],
    learningOutcomes,
  }
}

export const studentDashboardId = studentSummary.id

export const studentDashboardSubjects: Record<string, DashboardSubject> = Object.fromEntries(
  studentResults.map((subject) => [subject.code, buildSubject(subject.code)]),
)

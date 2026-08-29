// Student registry. STU0001 uses the real workbook data; the others are
// illustrative variations (scores shifted, feedback matched to the new band)
// so the "choose a student" picker has something to switch between.
import type { SubjectResults } from './studentAssessments'
import { studentResults as baseResults } from './studentAssessments'

export interface StudentInfo {
  id: string
  label: string
}

export const students: StudentInfo[] = [
  { id: 'STU0001', label: 'Student STU0001' },
  { id: 'STU0018', label: 'Student STU0018' },
]

const FEEDBACK: Record<'fail' | 'developing' | 'credit' | 'distinction', string> = {
  fail: 'This limited result shows gaps that require targeted revision of the relevant learning themes. The student should revisit the core concepts, seek feedback early, and practise the techniques on smaller, well-tested examples before attempting the full task.',
  developing: 'This developing result meets the core requirements but needs greater consistency across the relevant learning themes. Future work should consolidate the underlying concepts, apply them more consistently, and justify design or implementation decisions with stronger evidence.',
  credit: 'This solid result shows the key learning themes are understood and mostly applied well. To move up a band, tighten the weaker steps and justify decisions more explicitly against the criteria.',
  distinction: 'This strong result applies the relevant learning themes accurately and consistently. Keep refining the finer points and the depth of justification to reach the top band.',
}

function feedbackFor(score: number): string {
  if (score < 50) return FEEDBACK.fail
  if (score < 65) return FEEDBACK.developing
  if (score < 78) return FEEDBACK.credit
  return FEEDBACK.distinction
}

function clampScore(value: number): number {
  return Math.max(5, Math.min(99, Math.round(value)))
}

function shiftResults(delta: number): SubjectResults[] {
  return baseResults.map((subject) => {
    const assessments = subject.assessments.map((assessment) => {
      const score = clampScore(assessment.score + delta)
      return {
        ...assessment,
        score,
        weightedScore: Math.round(score * assessment.weight * 100) / 100,
        feedback: feedbackFor(score),
      }
    })
    const total = Math.round(assessments.reduce((sum, a) => sum + a.weightedScore, 0) * 100) / 100
    return { ...subject, assessments, total }
  })
}

const RESULTS_BY_STUDENT: Record<string, SubjectResults[]> = {
  STU0001: baseResults,
  STU0018: shiftResults(12),
}

export function getStudentResults(studentId: string): SubjectResults[] {
  return RESULTS_BY_STUDENT[studentId] ?? baseResults
}

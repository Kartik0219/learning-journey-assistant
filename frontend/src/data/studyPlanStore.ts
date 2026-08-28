// Persists the generated study plan per subject so the result is stable across
// visits. The page loads any saved snapshot first and only re-runs when the
// user asks (and only offers "regenerate" when the assessment data has changed).
// Stored per browser (localStorage).
import type { SiloPlan } from './studyPlan'

const STORAGE_KEY = 'ljas.studyPlan.v2'

export interface StudyPlanSnapshot {
  subjectCode: string
  generatedAt: string
  sourceFingerprint: string
  plans: SiloPlan[]
}

type SnapshotMap = Record<string, StudyPlanSnapshot>

function readAll(): SnapshotMap {
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    if (!raw) return {}
    const parsed = JSON.parse(raw)
    return parsed && typeof parsed === 'object' ? (parsed as SnapshotMap) : {}
  } catch {
    return {}
  }
}

function writeAll(map: SnapshotMap): void {
  try {
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(map))
  } catch {
    // storage unavailable / full - a non-persisted session still works
  }
}

function key(studentId: string, subjectCode: string): string {
  return `${studentId}::${subjectCode}`
}

export function loadSnapshot(studentId: string, subjectCode: string): StudyPlanSnapshot | null {
  const snap = readAll()[key(studentId, subjectCode)]
  if (!snap || !Array.isArray(snap.plans) || typeof snap.generatedAt !== 'string') return null
  return snap
}

export function saveSnapshot(studentId: string, snapshot: StudyPlanSnapshot): void {
  const map = readAll()
  map[key(studentId, snapshot.subjectCode)] = snapshot
  writeAll(map)
}

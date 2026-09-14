import { createContext, useContext, useMemo, type ReactNode } from 'react'
import { api, type SessionInfo } from './api'
import { useApi } from './useApi'

interface StudentContextValue {
  session: SessionInfo
  studentId: number
  studentLabel: string
}

const StudentContext = createContext<StudentContextValue | null>(null)

// The app is student-only: the signed-in student is the only record shown.
export function StudentProvider({ children }: { children: ReactNode }) {
  const { data: session, error, loading } = useApi(api.session, 'session')

  const value = useMemo(() => {
    if (!session || session.student_id === null) return null
    const label = session.students.find((s) => s.id === session.student_id)?.label ?? `Student ${session.student_id}`
    return { session, studentId: session.student_id, studentLabel: label }
  }, [session])

  if (loading) return <p className="page-status">Loading your learning journey…</p>
  if (error) return <p className="page-status page-status--error">Could not load your session: {error.message}</p>
  if (!value) return <p className="page-status">No student record is available for this sign-in.</p>
  return <StudentContext.Provider value={value}>{children}</StudentContext.Provider>
}

export function useStudent(): StudentContextValue {
  const value = useContext(StudentContext)
  if (!value) throw new Error('useStudent must be used within a StudentProvider')
  return value
}

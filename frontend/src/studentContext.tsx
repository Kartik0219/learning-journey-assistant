import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { api, type SessionInfo } from './api'
import { useApi } from './useApi'

interface StudentContextValue {
  session: SessionInfo
  studentId: number
  studentLabel: string
  setStudentId: (id: number) => void
}

const StudentContext = createContext<StudentContextValue | null>(null)

export function StudentProvider({ children }: { children: ReactNode }) {
  const { data: session, error, loading } = useApi(api.session, 'session')
  const [studentId, setStudentId] = useState<number | null>(null)

  useEffect(() => {
    if (session && studentId === null) {
      setStudentId(session.student_id ?? session.students[0]?.id ?? null)
    }
  }, [session, studentId])

  const value = useMemo(() => {
    if (!session || studentId === null) return null
    const label = session.students.find((s) => s.id === studentId)?.label ?? `Student ${studentId}`
    return { session, studentId, studentLabel: label, setStudentId }
  }, [session, studentId])

  if (loading) return <p className="page-status">Loading your learning journey…</p>
  if (error) return <p className="page-status page-status--error">Could not load your session: {error.message}</p>
  if (!value) return <p className="page-status">No student records are available yet.</p>
  return <StudentContext.Provider value={value}>{children}</StudentContext.Provider>
}

export function useStudent(): StudentContextValue {
  const value = useContext(StudentContext)
  if (!value) throw new Error('useStudent must be used within a StudentProvider')
  return value
}

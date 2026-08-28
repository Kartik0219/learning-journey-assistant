import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'
import type { SubjectResults } from './data/studentAssessments'
import { getStudentResults, students } from './data/students'

interface StudentContextValue {
  studentId: string
  setStudentId: (id: string) => void
  results: SubjectResults[]
}

const StudentContext = createContext<StudentContextValue | null>(null)

export function StudentProvider({ children }: { children: ReactNode }) {
  const [studentId, setStudentId] = useState(students[0].id)
  const results = useMemo(() => getStudentResults(studentId), [studentId])
  const value = useMemo(() => ({ studentId, setStudentId, results }), [studentId, results])
  return <StudentContext.Provider value={value}>{children}</StudentContext.Provider>
}

export function useStudent(): StudentContextValue {
  const value = useContext(StudentContext)
  if (!value) throw new Error('useStudent must be used within a StudentProvider')
  return value
}

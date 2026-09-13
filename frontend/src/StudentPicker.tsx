import { UserRound } from 'lucide-react'
import { Dropdown } from './Dropdown'
import { useStudent } from './studentContext'

// Staff/Admin can switch between students; a student only ever has
// themself in the list (enforced server-side, N6), so show a label instead.
export function StudentPicker() {
  const { session, studentId, studentLabel, setStudentId } = useStudent()
  if (session.students.length <= 1) {
    return <span className="topbar-student"><UserRound size={15} aria-hidden="true" /> {studentLabel}</span>
  }
  return (
    <Dropdown
      label="Student"
      ariaLabel="Choose a student"
      icon={UserRound}
      value={String(studentId)}
      options={session.students.map((student) => ({ value: String(student.id), label: student.label }))}
      onChange={(value) => setStudentId(Number(value))}
    />
  )
}

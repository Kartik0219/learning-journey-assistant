import { UserRound } from 'lucide-react'
import { Dropdown } from './Dropdown'
import { students } from './data/students'
import { useStudent } from './studentContext'

export function StudentPicker() {
  const { studentId, setStudentId } = useStudent()
  return (
    <Dropdown
      label="Student"
      ariaLabel="Choose a student"
      icon={UserRound}
      value={studentId}
      options={students.map((student) => ({ value: student.id, label: student.label }))}
      onChange={setStudentId}
    />
  )
}

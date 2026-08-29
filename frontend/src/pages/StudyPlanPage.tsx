import { useMemo, useState } from 'react'
import { BookOpen } from 'lucide-react'
import { buildStudentDashboardSubjects } from '../data/studentDashboard'
import { Dropdown } from '../Dropdown'
import { useStudent } from '../studentContext'

export function StudyPlanPage() {
  const { studentId, results } = useStudent()
  const subjects = useMemo(() => buildStudentDashboardSubjects(results), [results])
  const subjectCodes = useMemo(() => Object.keys(subjects), [subjects])

  const [subjectCode, setSubjectCode] = useState(subjectCodes[0])
  const activeCode = subjects[subjectCode] ? subjectCode : subjectCodes[0]

  return (
    <main className="dashboard" id="study-plan">
      <header className="dashboard-header results-header">
        <div>
          <p className="eyebrow">Student {studentId} · study plan</p>
          <h1>Study plan — powered by AI</h1>
        </div>
        <div className="header-actions">
          <Dropdown
            label="Subject"
            ariaLabel="Choose subject"
            icon={BookOpen}
            value={activeCode}
            options={subjectCodes.map((code) => ({ value: code, label: subjects[code].label }))}
            onChange={setSubjectCode}
          />
        </div>
        <div className="header-spacer" aria-hidden="true" />
      </header>
    </main>
  )
}


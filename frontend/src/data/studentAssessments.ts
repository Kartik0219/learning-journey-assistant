export interface AssessmentResult {
  assessment: string
  score: number
  feedback: string
  silos: string
  weight: number
  weightedScore: number
}

export interface SubjectResults {
  code: string
  assessments: AssessmentResult[]
  total: number
}

export const studentResults: SubjectResults[] = [
  {
    code: 'CSE1OOF',
    total: 50.65,
    assessments: [
      { assessment: 'Test', score: 54, weight: 0.15, weightedScore: 8.1, feedback: 'This developing result meets the core requirements but needs greater consistency of the relevant learning themes, particularly analysis/design/implementation compared with object-oriented modelling using objects that combine data structure and behaviour and abstract data types and encapsulation to localise and minimise change. Future work should focus on consolidating the underlying concepts, applying them more consistently and explaining design or implementation decisions with stronger evidence.', silos: 'SILO1: analysis/design/implementation compared with object-oriented modelling using objects that combine data structure and behaviour; SILO2: abstract data types and encapsulation to localise and minimise change' },
      { assessment: 'Practical demonstration', score: 49, weight: 0.2, weightedScore: 9.8, feedback: 'This limited result shows gaps that require targeted revision of the relevant learning themes, particularly abstract data types and encapsulation to localise and minimise change, code sharing and reuse through object-oriented techniques to reduce development time, and object-oriented design and implementation of computer programs for real-life problems. The student should revisit the core concepts, seek feedback early and practise applying the techniques in smaller, well-tested examples before attempting the full assessment task.', silos: 'SILO2: abstract data types and encapsulation to localise and minimise change; SILO3: code sharing and reuse through object-oriented techniques to reduce development time; SILO4: object-oriented design and implementation of computer programs for real-life problems' },
      { assessment: 'Assignment', score: 51, weight: 0.25, weightedScore: 12.75, feedback: 'This developing result meets the core requirements but needs greater consistency of the relevant learning themes, particularly abstract data types and encapsulation to localise and minimise change, code sharing and reuse through object-oriented techniques to reduce development time, and object-oriented design and implementation of computer programs for real-life problems. Future work should focus on consolidating the underlying concepts, applying them more consistently and explaining design or implementation decisions with stronger evidence.', silos: 'SILO2: abstract data types and encapsulation to localise and minimise change; SILO3: code sharing and reuse through object-oriented techniques to reduce development time; SILO4: object-oriented design and implementation of computer programs for real-life problems' },
      { assessment: 'Central examination', score: 50, weight: 0.4, weightedScore: 20, feedback: 'This developing result meets the core requirements but needs greater consistency of the relevant learning themes, particularly abstract data types and encapsulation to localise and minimise change, object-oriented design and implementation of computer programs for real-life problems, code sharing and reuse through object-oriented techniques to reduce development time, and analysis/design/implementation compared with object-oriented modelling using objects that combine data structure and behaviour. Future work should focus on consolidating the underlying concepts, applying them more consistently and explaining design or implementation decisions with stronger evidence.', silos: 'SILO2: abstract data types and encapsulation to localise and minimise change; SILO4: object-oriented design and implementation of computer programs for real-life problems; SILO3: code sharing and reuse through object-oriented techniques to reduce development time; SILO1: analysis/design/implementation compared with object-oriented modelling using objects that combine data structure and behaviour' },
    ],
  },
  {
    code: 'CSE2ALG',
    total: 50.8,
    assessments: [
      { assessment: 'Test', score: 53, weight: 0.2, weightedScore: 10.6, feedback: 'This developing result meets the core requirements but needs greater consistency of the relevant learning themes, particularly overall objectives of Algorithms and Data Structures, identifying data structures and searching and sorting algorithms in computing contexts, and implementing data structures and searching and sorting algorithms in Java. Future work should focus on consolidating the underlying concepts, applying them more consistently and explaining design or implementation decisions with stronger evidence.', silos: 'SILO1: overall objectives of Algorithms and Data Structures; SILO2: identifying data structures and searching and sorting algorithms in computing contexts; SILO3: implementing data structures and searching and sorting algorithms in Java' },
      { assessment: 'Assignment', score: 54, weight: 0.3, weightedScore: 16.2, feedback: 'This developing result meets the core requirements but needs greater consistency of the relevant learning themes, particularly identifying data structures and searching and sorting algorithms in computing contexts, implementing data structures and searching and sorting algorithms in Java, comparing algorithms and data structures and applying suitable choices to problems, and designing, implementing, and evaluating Java solutions using appropriate performance measures. Future work should focus on consolidating the underlying concepts, applying them more consistently and explaining design or implementation decisions with stronger evidence.', silos: 'SILO2: identifying data structures and searching and sorting algorithms in computing contexts; SILO3: implementing data structures and searching and sorting algorithms in Java; SILO4: comparing algorithms and data structures and applying suitable choices to problems; SILO5: designing, implementing, and evaluating Java solutions using appropriate performance measures' },
      { assessment: 'Central examination', score: 48, weight: 0.5, weightedScore: 24, feedback: 'This limited result shows gaps that require targeted revision of the relevant learning themes, particularly overall objectives of Algorithms and Data Structures, identifying data structures and searching and sorting algorithms in computing contexts, implementing data structures and searching and sorting algorithms in Java, and designing, implementing, and evaluating Java solutions using appropriate performance measures. The student should revisit the core concepts, seek feedback early and practise applying the techniques in smaller, well-tested examples before attempting the full assessment task.', silos: 'SILO1: overall objectives of Algorithms and Data Structures; SILO2: identifying data structures and searching and sorting algorithms in computing contexts; SILO3: implementing data structures and searching and sorting algorithms in Java; SILO5: designing, implementing, and evaluating Java solutions using appropriate performance measures' },
    ],
  },
  {
    code: 'CSE3CAP',
    total: 48.4,
    assessments: [
      { assessment: 'Oral presentation: Project Milestone Presentation', score: 50, weight: 0.1, weightedScore: 5, feedback: 'This developing result meets the core requirements but needs greater consistency of the relevant learning themes, particularly reporting project outcomes to technical and non-technical audiences and reflecting on feedback. Future work should focus on consolidating the underlying concepts, applying them more consistently and explaining design or implementation decisions with stronger evidence.', silos: 'SILO3: reporting project outcomes to technical and non-technical audiences and reflecting on feedback' },
      { assessment: 'Oral presentation: Final Project Presentation', score: 49, weight: 0.2, weightedScore: 9.8, feedback: 'This limited result shows gaps that require targeted revision of the relevant learning themes, particularly reporting project outcomes to technical and non-technical audiences and reflecting on feedback. The student should revisit the core concepts, seek feedback early and practise applying the techniques in smaller, well-tested examples before attempting the full assessment task.', silos: 'SILO3: reporting project outcomes to technical and non-technical audiences and reflecting on feedback' },
      { assessment: 'Assignment: Final written Project Report', score: 50, weight: 0.35, weightedScore: 17.5, feedback: 'This developing result meets the core requirements but needs greater consistency of the relevant learning themes, particularly industry standard technical solutions in software or cybersecurity practice and professional system documentation and advanced technical reporting to industry standards. Future work should focus on consolidating the underlying concepts, applying them more consistently and explaining design or implementation decisions with stronger evidence.', silos: 'SILO2: industry standard technical solutions in software or cybersecurity practice; SILO4: professional system documentation and advanced technical reporting to industry standards' },
      { assessment: 'Assignment: Sprint Project management reports', score: 46, weight: 0.35, weightedScore: 16.1, feedback: 'This limited result shows gaps that require targeted revision of the relevant learning themes, particularly advanced project management during substantive development implementation and industry standard technical solutions in software or cybersecurity practice. The student should revisit the core concepts, seek feedback early and practise applying the techniques in smaller, well-tested examples before attempting the full assessment task.', silos: 'SILO1: advanced project management during substantive development implementation; SILO2: industry standard technical solutions in software or cybersecurity practice' },
    ],
  },
]

export interface SubjectSilo {
  id: string
  description: string
}

// Subject Intended Learning Outcomes, taken from the "Assessment Map" tab of
// the CSE results workbook (SILO Theme Summary column).
export const subjectSilos: Record<string, SubjectSilo[]> = {
  CSE1OOF: [
    { id: 'SILO1', description: 'analysis/design/implementation compared with object-oriented modelling using objects that combine data structure and behaviour' },
    { id: 'SILO2', description: 'abstract data types and encapsulation to localise and minimise change' },
    { id: 'SILO3', description: 'code sharing and reuse through object-oriented techniques to reduce development time' },
    { id: 'SILO4', description: 'object-oriented design and implementation of computer programs for real-life problems' },
  ],
  CSE2ALG: [
    { id: 'SILO1', description: 'overall objectives of Algorithms and Data Structures' },
    { id: 'SILO2', description: 'identifying data structures and searching and sorting algorithms in computing contexts' },
    { id: 'SILO3', description: 'implementing data structures and searching and sorting algorithms in Java' },
    { id: 'SILO4', description: 'comparing algorithms and data structures and applying suitable choices to problems' },
    { id: 'SILO5', description: 'designing, implementing, and evaluating Java solutions using appropriate performance measures' },
  ],
  CSE3CAP: [
    { id: 'SILO1', description: 'advanced project management during substantive development implementation' },
    { id: 'SILO2', description: 'industry standard technical solutions in software or cybersecurity practice' },
    { id: 'SILO3', description: 'reporting project outcomes to technical and non-technical audiences and reflecting on feedback' },
    { id: 'SILO4', description: 'professional system documentation and advanced technical reporting to industry standards' },
  ],
}

export const studentSummary = {
  id: 'STU0001',
  averageTotal: 49.95,
  performanceBand: 'At risk',
}
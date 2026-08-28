export type MasteryStatus =
  | 'strong'
  | 'onTrack'
  | 'focusArea'
  | 'atRisk'
  | 'developing'
  | 'proficient'
  | 'mastered'

export interface EvidenceItem {
  label: string
  score: string
}

export interface LearningOutcome {
  name: string
  masteryPercentage: number
  status: MasteryStatus
  statusLabel: string
  evidence: EvidenceItem[]
  feedback: string
  feedbackSource?: string
  recommendedAction: string
}

export interface StudyStep {
  text: string
  emphasis?: string
  suffix?: string
}

export interface DashboardSubject {
  code: string
  label: string
  overallMasteryPercentage: number
  priorityFocusAreas: number
  assessmentsAnalysed: number
  masteryTrend: number[]
  nextSteps: StudyStep[]
  recommendedResources: string[]
  learningOutcomes: LearningOutcome[]
}

export const dashboardSubjects: Record<string, DashboardSubject> = {
  STA101: {
    code: 'STA101',
    label: 'STA101 - Statistics for Data',
    overallMasteryPercentage: 66,
    priorityFocusAreas: 2,
    assessmentsAnalysed: 3,
    masteryTrend: [48, 52, 58, 61, 66],
    nextSteps: [
      {
        text: 'Rework the Assignment 1 data question using a decision chart for choosing a statistical test.',
      },
      {
        text: 'Complete the adaptive quiz on ',
        emphasis: 'test selection',
        suffix: ' (6 questions, aimed at your gap).',
      },
      {
        text: 'Read the topic note on ',
        emphasis: 'research methods',
        suffix: ' before the next assessment.',
      },
    ],
    recommendedResources: [
      'Choosing a statistical test - subject topic 4',
      'Worked example: hypothesis testing',
      'Study strategy: spaced practice for methods',
    ],
    learningOutcomes: [
      {
        name: 'Referencing & citation',
        masteryPercentage: 90,
        status: 'strong',
        statusLabel: 'Strong',
        evidence: [{ label: 'Assignment 1 - Referencing', score: '9 / 10' }],
        feedback: 'Referencing is thorough and correctly formatted throughout.',
        recommendedAction: 'Keep it up - this is a consolidated strength.',
      },
      {
        name: 'Critical analysis',
        masteryPercentage: 74,
        status: 'onTrack',
        statusLabel: 'On track',
        evidence: [{ label: 'Quiz 2', score: '7 / 10' }],
        feedback: 'Solid analysis; push further on the limitations of each source.',
        recommendedAction: 'Stretch task: add a limitations paragraph to your next draft.',
      },
      {
        name: 'Argument structure',
        masteryPercentage: 68,
        status: 'onTrack',
        statusLabel: 'On track',
        evidence: [{ label: 'Assignment 1 - Structure', score: '6.8 / 10' }],
        feedback: 'The argument is clear, but the conclusion is under-supported.',
        recommendedAction: 'Practise linking each conclusion back to your evidence.',
      },
      {
        name: 'Research methods',
        masteryPercentage: 55,
        status: 'focusArea',
        statusLabel: 'Focus area',
        evidence: [{ label: 'Assignment 1 - Q3', score: '5.5 / 10' }],
        feedback: 'Method selection needs work - justify why a method fits the question.',
        recommendedAction: 'Do the methods refresher, then the short practice quiz.',
      },
      {
        name: 'Data handling',
        masteryPercentage: 42,
        status: 'focusArea',
        statusLabel: 'Focus area',
        evidence: [
          { label: 'Assignment 1 - Q3', score: '4 / 10' },
          { label: 'Quiz 2 - Q5-7', score: '40%' },
        ],
        feedback: 'Chose the wrong statistical test; statistical reasoning is underdeveloped.',
        recommendedAction: 'Start here - this is your highest-impact gap this cycle.',
      },
    ],
  },
  BIO102: {
    code: 'BIO102',
    label: 'BIO102 - Cell Biology',
    overallMasteryPercentage: 65,
    priorityFocusAreas: 2,
    assessmentsAnalysed: 4,
    masteryTrend: [55, 57, 60, 62, 65],
    nextSteps: [
      {
        text: 'Redo the experimental-design task using the variables-and-controls checklist.',
      },
      {
        text: 'Complete the adaptive quiz on ',
        emphasis: 'experimental design',
        suffix: ' (6 questions).',
      },
      {
        text: 'Review the writing guide before submitting your next lab report.',
      },
    ],
    recommendedResources: [
      'Designing a controlled experiment - topic 3',
      'Lab report structure guide',
      'Glossary: core cell-biology terms',
    ],
    learningOutcomes: [
      {
        name: 'Lab technique',
        masteryPercentage: 88,
        status: 'strong',
        statusLabel: 'Strong',
        evidence: [{ label: 'Lab log - Weeks 1-4', score: '8.8 / 10' }],
        feedback: 'Consistent, careful technique with clean records.',
        recommendedAction: 'Strength - maintain your current practice.',
      },
      {
        name: 'Terminology',
        masteryPercentage: 80,
        status: 'strong',
        statusLabel: 'Strong',
        evidence: [{ label: 'Quiz 1', score: '8 / 10' }],
        feedback: 'Confident, accurate use of core terminology.',
        recommendedAction: 'Strength - a good base for the harder topics ahead.',
      },
      {
        name: 'Data interpretation',
        masteryPercentage: 63,
        status: 'onTrack',
        statusLabel: 'On track',
        evidence: [{ label: 'Lab report 1 - Results', score: '6.3 / 10' }],
        feedback: 'Reads the data well; be more precise about what it does not show.',
        recommendedAction: 'Practise stating the limits of each result.',
      },
      {
        name: 'Experimental design',
        masteryPercentage: 50,
        status: 'focusArea',
        statusLabel: 'Focus area',
        evidence: [{ label: 'Lab report 1 - Design', score: '5 / 10' }],
        feedback: 'Controls and variables are not clearly identified.',
        recommendedAction: 'Work through the design checklist on your next plan.',
      },
      {
        name: 'Scientific writing',
        masteryPercentage: 46,
        status: 'focusArea',
        statusLabel: 'Focus area',
        evidence: [{ label: 'Lab report 1 - Writing', score: '4.6 / 10' }],
        feedback: 'Structure is unclear and the method is hard to follow.',
        recommendedAction: 'Start here - use the lab-report structure guide.',
      },
    ],
  },
}

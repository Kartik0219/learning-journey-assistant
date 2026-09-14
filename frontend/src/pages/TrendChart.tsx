import { assessmentName, weightedAverage, type ResultRow } from '../api'

// Cumulative weighted mastery after each assessment, in the order they were sat,
// drawn over the four mastery bands.
export function TrendChart({ rows }: { rows: ResultRow[] }) {
  const points = rows
    .map((_, i) => weightedAverage(rows.slice(0, i + 1)))
    .map((value, i) => ({ value, row: rows[i] }))
    .filter((p): p is { value: number; row: ResultRow } => p.value !== null)
  if (points.length < 2) return null

  const W = 320, H = 132, left = 34, right = 12, top = 10, bottom = 108
  const x = (i: number) => left + (i * (W - left - right)) / (points.length - 1)
  const y = (v: number) => bottom - (v / 100) * (bottom - top)
  const last = points[points.length - 1]
  const line = points.map((p, i) => `${x(i)},${y(p.value)}`).join(' ')
  const bands = [
    { from: 80, to: 100, cls: 'mastered' },
    { from: 65, to: 80, cls: 'proficient' },
    { from: 50, to: 65, cls: 'developing' },
    { from: 0, to: 50, cls: 'atRisk' },
  ]

  return (
    <article className="stat trend">
      <span className="stat-label"><strong>Cumulative weighted mastery</strong> after each assessment</span>
      <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Mastery after each assessment: ${points.map((p, i) => `A${i + 1} ${p.value.toFixed(1)}%`).join(', ')}`}>
        {bands.map((b) => <rect key={b.cls} className={`band-bg ${b.cls}`} x={left} width={W - left - right} y={y(b.to)} height={y(b.from) - y(b.to)} />)}
        {[0, 50, 100].map((t) => <text key={t} className="axis" x={left - 6} y={y(t) + 3} textAnchor="end">{t}</text>)}
        {points.map((p, i) => (
          <text key={p.row.id} className="axis" x={x(i)} y={H - 8} textAnchor="middle">
            A{i + 1}<title>{assessmentName(p.row.assessment)}</title>
          </text>
        ))}
        <polyline className="trend-line" points={line} />
        {points.map((p, i) => <circle key={p.row.id} className={i === points.length - 1 ? 'trend-dot last' : 'trend-dot'} cx={x(i)} cy={y(p.value)} r={i === points.length - 1 ? 4.5 : 3.5} />)}
        <text className="trend-label" x={x(points.length - 1)} y={y(last.value) - 9} textAnchor="middle">{last.value.toFixed(1)}</text>
      </svg>
    </article>
  )
}

import { useState } from 'react'
import { assessmentName, weightedAverage, type ResultRow } from '../api'

// Cumulative weighted mastery after each assessment, in the order they were sat,
// drawn over the four mastery bands. Hover a point for the assessment behind
// it; click (or press Enter) to open its evidence on the dashboard.
export function TrendChart({ rows, onSelect }: { rows: ResultRow[]; onSelect?: (row: ResultRow) => void }) {
  const [hover, setHover] = useState<number | null>(null)
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
  const tip = hover === null ? null : points[hover]
  const TW = 150, TH = 26
  const tx = tip ? Math.max(left, Math.min(W - right - TW, x(hover!) - TW / 2)) : 0
  const ty = tip ? (y(tip.value) - TH - 10 < top ? y(tip.value) + 10 : y(tip.value) - TH - 10) : 0

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
        {points.map((p, i) => (
          <circle key={p.row.id} className={`trend-dot${i === points.length - 1 ? ' last' : ''}${hover === i ? ' hover' : ''}`} cx={x(i)} cy={y(p.value)} r={i === points.length - 1 ? 4.5 : 3.5} />
        ))}
        {tip === null && <text className="trend-label" x={x(points.length - 1)} y={y(last.value) - 9} textAnchor="middle">{last.value.toFixed(1)}</text>}
        {points.map((p, i) => (
          <circle
            key={`hit-${p.row.id}`} className="trend-hit" cx={x(i)} cy={y(p.value)} r={11} tabIndex={0} role="button"
            aria-label={`A${i + 1} ${assessmentName(p.row.assessment)}: ${p.row.score ?? '—'} out of 100, cumulative ${p.value.toFixed(1)}%. Open its evidence.`}
            onMouseEnter={() => setHover(i)} onMouseLeave={() => setHover(null)} onFocus={() => setHover(i)} onBlur={() => setHover(null)}
            onClick={() => onSelect?.(p.row)} onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); onSelect?.(p.row) } }}
          />
        ))}
        {tip && (
          <g className="chart-tip" transform={`translate(${tx} ${ty})`}>
            <rect width={TW} height={TH} />
            <text x={6} y={10}>A{hover! + 1} · {assessmentName(tip.row.assessment).slice(0, 26)}</text>
            <text x={6} y={21} className="dim">{tip.row.score ?? '—'}/100 · {Math.round((tip.row.weight ?? 0) * 100)}% weight · cumulative {tip.value.toFixed(1)}%</text>
          </g>
        )}
      </svg>
      {onSelect && <p className="chart-hint">Hover a point · click it to open that assessment's evidence</p>}
    </article>
  )
}

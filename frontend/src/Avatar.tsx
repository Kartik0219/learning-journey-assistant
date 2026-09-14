/**
 * A generated avatar, seeded from the student number. The dataset is
 * anonymised (student numbers only, no names, no photos), so every student
 * gets a unique, deterministic identicon in La Trobe colours instead of a
 * stock face: same student, same picture, on every device, with nothing
 * to upload, store or license.
 */

// La Trobe red plus a set of tones that sit well on the charcoal header.
const PALETTE = ['#E2001A', '#B80015', '#C98A0B', '#4E9A63', '#1F7A5C', '#2F6DB5', '#7A4FB5', '#D25A2C']

function hash(seed: string): number {
  // FNV-1a: small, stable, spreads short strings like "STU0042" well.
  let h = 0x811c9dc5
  for (let i = 0; i < seed.length; i++) {
    h ^= seed.charCodeAt(i)
    h = Math.imul(h, 0x01000193) >>> 0
  }
  return h
}

export function Avatar({ seed, size = 22 }: { seed: string; size?: number }) {
  const h = hash(seed)
  const bg = PALETTE[h % PALETTE.length]
  const fg = '#FFFFFF'
  // 5×5 grid, mirrored left–right so every face reads as a "creature"
  // rather than noise; 15 bits decide the left 3 columns.
  const cells: string[] = []
  let bits = h >>> 5
  for (let y = 0; y < 5; y++) {
    for (let x = 0; x < 3; x++) {
      if (bits & 1) {
        cells.push(`M${x} ${y}h1v1h-1z`)
        if (x < 2) cells.push(`M${4 - x} ${y}h1v1h-1z`)
      }
      bits >>>= 1
    }
  }
  return (
    <svg className="avatar" width={size} height={size} viewBox="-1 -1 7 7" role="img" aria-label={`Avatar for ${seed}`}>
      <rect x="-1" y="-1" width="7" height="7" rx="1.6" fill={bg} />
      <path d={cells.join('')} fill={fg} />
    </svg>
  )
}

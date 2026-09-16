import { useEffect, useState } from 'react'
import { Clock as ClockIcon } from 'lucide-react'
import { MELBOURNE } from './local'

const TIME = new Intl.DateTimeFormat('en-AU', { timeZone: MELBOURNE, hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false })
const DATE = new Intl.DateTimeFormat('en-AU', { timeZone: MELBOURNE, weekday: 'short', day: 'numeric', month: 'short' })
const ZONE = new Intl.DateTimeFormat('en-AU', { timeZone: MELBOURNE, timeZoneName: 'short' })

/** Live Melbourne clock - the university's clock, whatever the laptop is set to. */
export function MelbourneClock({ large = false }: { large?: boolean }) {
  const [now, setNow] = useState(() => new Date())
  useEffect(() => {
    const id = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(id)
  }, [])
  const zone = ZONE.formatToParts(now).find((p) => p.type === 'timeZoneName')?.value ?? 'AEST'
  return (
    <span className={large ? 'clock clock-large' : 'clock'} title={`Melbourne time (${zone})`}>
      <ClockIcon size={large ? 18 : 13} aria-hidden="true" />
      <span className="clock-time">{TIME.format(now)}</span>
      <span className="clock-date">{DATE.format(now)} · Melbourne {zone}</span>
    </span>
  )
}

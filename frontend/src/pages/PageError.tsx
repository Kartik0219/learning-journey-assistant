import type { ApiError } from '../api'

export function PageError({ error }: { error: ApiError }) {
  if (error.code === 'no_consent') {
    return <p className="page-status">Consent is not active for this record, so no learning data has been processed. Nothing is shown until consent is given.</p>
  }
  if (error.status === 403) {
    return <p className="page-status page-status--error">You do not have access to this student's records.</p>
  }
  return <p className="page-status page-status--error">Something went wrong loading this page: {error.message}</p>
}

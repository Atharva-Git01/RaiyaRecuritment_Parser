import { DEMO_CANDIDATES } from '@/data/static-data'
import CandidateReport from './CandidateReport'

export function generateStaticParams() {
  return DEMO_CANDIDATES.map(c => ({ id: c.id }))
}

export default async function CandidateReportPage({ params }) {
  const { id } = await params
  return <CandidateReport id={id} />
}

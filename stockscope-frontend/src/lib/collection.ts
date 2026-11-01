export interface CollectionJob {
  symbol: string
  run_id: string | null
  status: 'pending' | 'processing' | 'completed' | 'partial' | 'failed'
  message: string
  started_at: string
  completed_at?: string | null
  providers: Record<string, { status: string; count: number; message: string }>
}
export function readCollectionJob(value: unknown, symbol: string): CollectionJob {
  const job = value as CollectionJob | null
  if (!job || job.symbol !== symbol || !['pending', 'processing', 'completed', 'partial', 'failed'].includes(job.status) ||
      typeof job.message !== 'string' || !Number.isFinite(Date.parse(job.started_at)) ||
      !job.providers || typeof job.providers !== 'object' || Array.isArray(job.providers) ||
      !Object.values(job.providers).every(provider => provider && typeof provider.status === 'string' &&
        typeof provider.message === 'string' && Number.isFinite(provider.count))) {
    throw new Error('Collection status was incomplete or belonged to another company. Retry checking status.')
  }
  return job
}
export const collectionActive = (job?: CollectionJob | null) => job?.status === 'pending' || job?.status === 'processing'
export function collectionOutcome(job?: CollectionJob | null) {
  return job && !collectionActive(job) ? `${job.run_id || job.started_at}|${job.status}|${job.completed_at || ''}` : null
}
export const collectionLabel = (job: CollectionJob) => ({
  pending: 'Collection queued', processing: 'Collecting sources', completed: 'Collection completed',
  partial: 'Collection partially completed', failed: 'Collection failed',
})[job.status]

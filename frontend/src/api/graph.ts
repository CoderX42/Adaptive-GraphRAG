import { http } from './client'
import type { GraphPayload, GraphStats } from './types'

export async function getGraphVisualize(params?: {
  query?: string
  doc_id?: string
}): Promise<GraphPayload> {
  const { data } = await http.get<GraphPayload>('/api/v1/graph/visualize', {
    params: {
      query: params?.query ?? '',
      doc_id: params?.doc_id ?? '',
    },
  })
  return data
}

export async function getGraphStats(): Promise<GraphStats> {
  const { data } = await http.get<GraphStats>('/api/v1/graph/stats')
  return data
}

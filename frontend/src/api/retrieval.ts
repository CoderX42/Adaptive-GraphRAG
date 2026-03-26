import { http } from './client'
import type { QueryResult, RetrievalMode } from './types'

export async function queryDocuments(
  text: string,
  mode: RetrievalMode = 'auto',
): Promise<QueryResult> {
  const { data } = await http.get<QueryResult>('/api/v1/retrieval/query', {
    params: { text, mode },
  })
  return data
}

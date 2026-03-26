export type DocumentStatus = 'pending' | 'processing' | 'ready' | 'failed'

export interface DocumentRow {
  id: string
  filename: string
  page_count: number
  summary: string
  status: DocumentStatus
  created_at: string
}

export type RetrievalMode = 'auto' | 'vector' | 'graph' | 'hybrid'

export interface SourceReference {
  doc_id: string
  filename: string
  page: number
  text: string
}

export interface QueryResult {
  answer: string
  sources: SourceReference[]
  strategy_used: RetrievalMode
  reasoning_path: string[]
  confidence: number
}

export interface UploadOk {
  doc_id: string
  status: string
  chunks: number
  entities: number
  relations: number
}

export interface GraphNode {
  id: string
  label: string
  type: string
  source_docs: string[]
  aliases: string[]
}

export interface GraphEdge {
  source: string
  target: string
  label: string
  relations: string[]
}

export interface GraphPayload {
  nodes: GraphNode[]
  edges: GraphEdge[]
  stats: {
    nodes: number
    edges: number
    shown_nodes: number
    shown_edges: number
  }
}

export interface GraphStats {
  nodes: number
  edges: number
}

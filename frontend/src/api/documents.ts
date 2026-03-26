import { http } from './client'
import type { DocumentRow, UploadOk } from './types'

export async function listDocuments(): Promise<DocumentRow[]> {
  const { data } = await http.get<DocumentRow[]>('/api/v1/documents')
  return data
}

export async function uploadPdf(
  file: File,
  onProgress?: (pct: number) => void,
): Promise<UploadOk> {
  const form = new FormData()
  form.append('file', file)
  const { data } = await http.post<UploadOk>('/api/v1/documents/upload', form, {
    onUploadProgress(ev) {
      if (onProgress && ev.total) {
        onProgress(Math.round((ev.loaded / ev.total) * 100))
      }
    },
  })
  return data
}

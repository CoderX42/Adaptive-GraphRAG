<script setup lang="ts">
import { onMounted, onUnmounted, ref, computed } from 'vue'
import { listDocuments, uploadPdf } from '../api/documents'
import { useToast } from '../composables/useToast'
import type { DocumentRow } from '../api/types'

const { show } = useToast()
const docs = ref<DocumentRow[]>([])
const loading = ref(false)
const uploadBusy = ref(false)
const uploadProgress = ref(0)
const isDragging = ref(false)

/* ── Polling for processing docs ── */
let pollTimer: ReturnType<typeof setInterval> | null = null

function startPolling() {
  if (pollTimer) return
  pollTimer = setInterval(async () => {
    const hasProcessing = docs.value.some(d => d.status === 'processing' || d.status === 'pending')
    if (!hasProcessing) {
      stopPolling()
      return
    }
    await silentRefresh()
  }, 3000)
}

function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null }
}

async function silentRefresh() {
  try { docs.value = await listDocuments() } catch { /* ignore */ }
}

async function refresh() {
  loading.value = true
  try {
    docs.value = await listDocuments()
    const hasProcessing = docs.value.some(d => d.status === 'processing' || d.status === 'pending')
    if (hasProcessing) startPolling()
  } catch (e: unknown) {
    show(e instanceof Error ? e.message : '加载文档列表失败', 'error')
  } finally {
    loading.value = false
  }
}

/* ── Upload ── */
async function doUpload(file: File) {
  if (!file.name.toLowerCase().endsWith('.pdf')) {
    show('仅支持 PDF 文件', 'error')
    return
  }
  uploadBusy.value = true
  uploadProgress.value = 0
  try {
    const r = await uploadPdf(file, (pct) => { uploadProgress.value = pct })
    show(`上传成功：${r.chunks} 块，实体 ${r.entities}，关系 ${r.relations}`, 'success', 5000)
    await refresh()
  } catch (e: unknown) {
    const ax = e as { response?: { data?: { detail?: string } } }
    show(ax.response?.data?.detail ?? (e instanceof Error ? e.message : '上传失败'), 'error')
  } finally {
    uploadBusy.value = false
    uploadProgress.value = 0
  }
}

function onFileChange(ev: Event) {
  const input = ev.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (file) doUpload(file)
}

/* ── Drag & Drop ── */
function onDragover(ev: DragEvent) { ev.preventDefault(); isDragging.value = true }
function onDragleave() { isDragging.value = false }
function onDrop(ev: DragEvent) {
  ev.preventDefault()
  isDragging.value = false
  const file = ev.dataTransfer?.files?.[0]
  if (file) doUpload(file)
}

/* ── Summary expand ── */
const expandedIds = ref<Set<string>>(new Set())
function toggleSummary(id: string) {
  const s = new Set(expandedIds.value)
  s.has(id) ? s.delete(id) : s.add(id)
  expandedIds.value = s
}

/* ── Stats ── */
const stats = computed(() => ({
  total: docs.value.length,
  ready: docs.value.filter(d => d.status === 'ready').length,
  processing: docs.value.filter(d => d.status === 'processing' || d.status === 'pending').length,
}))

/* ── Helpers ── */
function statusLabel(s: string) {
  return ({ pending: '等待中', processing: '处理中', ready: '已就绪', failed: '失败' } as Record<string, string>)[s] ?? s
}
function formatDate(iso: string) {
  try {
    return new Date(iso).toLocaleString('zh-CN', { month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' })
  } catch { return iso }
}

/* ── Lifecycle ── */
onMounted(refresh)
onUnmounted(stopPolling)
</script>

<template>
  <div
    class="page"
    :class="{ dragging: isDragging }"
    @dragover="onDragover"
    @dragleave="onDragleave"
    @drop="onDrop"
  >
    <!-- Drag overlay -->
    <Transition name="fade">
      <div v-if="isDragging" class="drag-overlay">
        <div class="drag-inner">
          <svg width="48" height="48" fill="none" stroke="currentColor" stroke-width="1.5" viewBox="0 0 24 24">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="17 8 12 3 7 8"/>
            <line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
          <p>松开以上传 PDF</p>
        </div>
      </div>
    </Transition>

    <!-- Page header -->
    <div class="page-header">
      <div>
        <h2>文档管理</h2>
        <p class="page-desc">上传 PDF 后将自动分块、向量化并构建知识图谱。支持拖拽文件到页面。</p>
      </div>
      <div class="header-actions">
        <label class="btn primary">
          <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
            <polyline points="17 8 12 3 7 8"/>
            <line x1="12" y1="3" x2="12" y2="15"/>
          </svg>
          <input type="file" accept=".pdf,application/pdf" :disabled="uploadBusy" class="sr-only" @change="onFileChange" />
          {{ uploadBusy ? '处理中…' : '上传 PDF' }}
        </label>
        <button type="button" class="btn" :disabled="loading" @click="refresh">
          <svg width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24" :class="{ rotating: loading }">
            <polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/>
            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
          </svg>
          刷新
        </button>
      </div>
    </div>

    <!-- Upload progress -->
    <div v-if="uploadBusy" class="upload-progress">
      <div class="progress-label">
        <span class="spinner" />
        正在处理文档，请稍候（分块 · 向量化 · 建图）…
        <span v-if="uploadProgress > 0">{{ uploadProgress }}%</span>
      </div>
      <progress :value="uploadProgress" max="100" />
    </div>

    <!-- Stat cards -->
    <div class="stat-row">
      <div class="stat-card">
        <span class="stat-value">{{ stats.total }}</span>
        <span class="stat-label">文档总数</span>
      </div>
      <div class="stat-card ok">
        <span class="stat-value">{{ stats.ready }}</span>
        <span class="stat-label">已就绪</span>
      </div>
      <div class="stat-card processing" v-if="stats.processing > 0">
        <span class="spinner" style="margin-right:.4rem;color:var(--processing)" />
        <span class="stat-value">{{ stats.processing }}</span>
        <span class="stat-label">处理中</span>
      </div>
    </div>

    <!-- Table -->
    <div class="table-wrap">
      <div v-if="loading && !docs.length" class="skeleton-rows">
        <div v-for="i in 3" :key="i" class="skeleton-row">
          <div class="skeleton" style="width:30%;height:14px;border-radius:4px" />
          <div class="skeleton" style="width:10%;height:14px;border-radius:4px" />
          <div class="skeleton" style="width:5%;height:14px;border-radius:4px" />
          <div class="skeleton" style="width:50%;height:14px;border-radius:4px" />
        </div>
      </div>

      <template v-else>
        <!-- Empty state -->
        <div v-if="!docs.length" class="empty">
          <svg width="56" height="56" fill="none" stroke="var(--muted)" stroke-width="1.2" viewBox="0 0 24 24">
            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
            <polyline points="14 2 14 8 20 8"/>
          </svg>
          <p>暂无文档</p>
          <p class="empty-hint">点击「上传 PDF」或将文件拖到此页面</p>
        </div>

        <table v-else class="doc-table">
          <thead>
            <tr>
              <th>文件名</th>
              <th>状态</th>
              <th>页数</th>
              <th>摘要</th>
              <th>创建时间</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="d in docs" :key="d.id" class="doc-row">
              <td class="mono filename">{{ d.filename }}</td>
              <td>
                <span class="badge" :class="d.status">
                  <span v-if="d.status === 'processing'" class="spinner" style="font-size:.75rem" />
                  {{ statusLabel(d.status) }}
                </span>
              </td>
              <td class="center">{{ d.page_count || '—' }}</td>
              <td class="summary-cell">
                <span
                  v-if="d.summary"
                  :class="expandedIds.has(d.id) ? '' : 'truncate-2'"
                  @click="toggleSummary(d.id)"
                  :title="expandedIds.has(d.id) ? '点击折叠' : '点击展开'"
                  class="summary-text"
                >{{ d.summary }}</span>
                <span v-else class="muted">—</span>
              </td>
              <td class="mono small date">{{ formatDate(d.created_at) }}</td>
            </tr>
          </tbody>
        </table>
      </template>
    </div>
  </div>
</template>


<style scoped>
.page { position: relative; }

/* Drag overlay */
.drag-overlay {
  position: fixed; inset: 0;
  background: rgba(79,70,229,.15);
  border: 3px dashed var(--accent);
  z-index: 200;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: var(--radius-lg);
}
.drag-inner {
  text-align: center;
  color: var(--accent);
  font-size: 1.1rem;
  font-weight: 600;
}
.drag-inner p { margin-top: .75rem; }

/* Page header */
.page-header {
  display: flex;
  flex-wrap: wrap;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1.25rem;
}
.page-desc { color: var(--muted); font-size: 0.875rem; margin-top: 0.25rem; }
.header-actions { display: flex; gap: 0.5rem; flex-wrap: wrap; align-items: center; }

/* Progress */
.upload-progress {
  margin-bottom: 1rem;
  padding: 0.75rem 1rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
}
.progress-label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-size: 0.875rem;
  color: var(--processing);
  margin-bottom: 0.5rem;
}

/* Stat row */
.stat-row {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-bottom: 1.25rem;
}
.stat-card {
  display: flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.5rem 0.9rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow-sm);
  font-size: 0.85rem;
}
.stat-card.ok .stat-value { color: var(--ok); }
.stat-card.processing .stat-value { color: var(--processing); }
.stat-value { font-weight: 700; font-size: 1.1rem; }
.stat-label { color: var(--muted); font-size: 0.78rem; }

/* Table */
.table-wrap {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-sm);
}
.doc-table { width: 100%; border-collapse: collapse; font-size: 0.875rem; }
.doc-table th {
  text-align: left;
  padding: 0.7rem 0.9rem;
  background: var(--surface-2);
  border-bottom: 1px solid var(--border);
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.doc-row td {
  padding: 0.75rem 0.9rem;
  border-bottom: 1px solid var(--border);
  vertical-align: top;
}
.doc-row:last-child td { border-bottom: none; }
.doc-row:hover td { background: var(--surface-2); }
.doc-row td.center { text-align: center; }
.filename { max-width: 18rem; word-break: break-all; }
.summary-cell { max-width: 32rem; }
.summary-text { cursor: pointer; }
.summary-text:hover { text-decoration: underline dotted; }
.date { white-space: nowrap; color: var(--muted); }

/* Skeleton */
.skeleton-rows { padding: 1rem; display: flex; flex-direction: column; gap: .75rem; }
.skeleton-row { display: flex; gap: 1rem; align-items: center; }

/* Empty */
.empty {
  padding: 3rem 1.5rem;
  text-align: center;
  color: var(--muted);
}
.empty p { margin: 0.4rem 0; font-size: 1rem; }
.empty-hint { font-size: 0.85rem; color: var(--muted); }

/* Rotate animation */
@keyframes rotate { to { transform: rotate(360deg); } }
.rotating { animation: rotate 1s linear infinite; }

/* Fade transition */
.fade-enter-active, .fade-leave-active { transition: opacity 0.15s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>

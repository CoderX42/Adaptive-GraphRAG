<script setup lang="ts">
import { ref, nextTick, onUnmounted } from 'vue'
import { marked } from 'marked'
import { queryDocuments } from '../api/retrieval'
import type { QueryResult, RetrievalMode } from '../api/types'
import { useToast } from '../composables/useToast'

const { show } = useToast()

interface HistoryItem {
  id: number
  question: string
  mode: RetrievalMode
  result: QueryResult | null
  loading: boolean
}

const question = ref('')
const mode = ref<RetrievalMode>('auto')
const busy = ref(false)
const history = ref<HistoryItem[]>([])
const historyEl = ref<HTMLElement | null>(null)
let nextId = 0

const modes: { value: RetrievalMode; label: string; color: string }[] = [
  { value: 'auto',   label: '自动',   color: 'mode-auto' },
  { value: 'vector', label: '向量',   color: 'mode-vector' },
  { value: 'graph',  label: '图谱',   color: 'mode-graph' },
  { value: 'hybrid', label: '混合',   color: 'mode-hybrid' },
]

function renderMd(text: string) {
  return marked.parse(text, { breaks: true, async: false }) as string
}

function strategyColor(s: string) {
  return { vector: 'mode-vector', graph: 'mode-graph', hybrid: 'mode-hybrid' }[s] ?? 'mode-auto'
}

/* ── Auto-height textarea ── */
function autoResize(ev: Event) {
  const el = ev.target as HTMLTextAreaElement
  el.style.height = 'auto'
  el.style.height = Math.min(el.scrollHeight, 240) + 'px'
}

/* ── Keyboard shortcut ── */
function onKeydown(ev: KeyboardEvent) {
  if ((ev.ctrlKey || ev.metaKey) && ev.key === 'Enter') {
    ev.preventDefault()
    submit()
  }
}

/* ── Submit ── */
async function submit() {
  const q = question.value.trim()
  if (!q) { show('请输入问题', 'error'); return }
  if (busy.value) return

  busy.value = true
  const item: HistoryItem = {
    id: ++nextId,
    question: q,
    mode: mode.value,
    result: null,
    loading: true,
  }
  history.value.push(item)
  question.value = ''
  await nextTick()
  scrollToBottom()

  try {
    const result = await queryDocuments(q, item.mode)
    const idx = history.value.findIndex(h => h.id === item.id)
    if (idx !== -1) history.value[idx] = { ...item, result, loading: false }
  } catch (e: unknown) {
    const ax = e as { response?: { data?: { detail?: string } } }
    const msg = ax.response?.data?.detail ?? (e instanceof Error ? e.message : '查询失败')
    show(msg, 'error')
    const idx = history.value.findIndex(h => h.id === item.id)
    if (idx !== -1) history.value.splice(idx, 1)
  } finally {
    busy.value = false
    await nextTick()
    scrollToBottom()
  }
}

function scrollToBottom() {
  if (historyEl.value) {
    historyEl.value.scrollTo({ top: historyEl.value.scrollHeight, behavior: 'smooth' })
  }
}

/* ── Copy ── */
async function copyAnswer(text: string) {
  try {
    await navigator.clipboard.writeText(text)
    show('已复制到剪贴板', 'success', 2000)
  } catch {
    show('复制失败，请手动选择', 'error')
  }
}

function clearHistory() {
  history.value = []
}

onUnmounted(() => {})
</script>

<template>
  <div class="qpage">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h2>智能问答</h2>
        <p class="page-desc">基于已索引文档进行问答；检索模式可与后端自动路由配合使用。</p>
      </div>
      <button v-if="history.length" type="button" class="btn sm" @click="clearHistory">
        清空历史
      </button>
    </div>

    <!-- History feed -->
    <div v-if="history.length" ref="historyEl" class="history">
      <div v-for="item in history" :key="item.id" class="turn">
        <!-- User bubble -->
        <div class="bubble user-bubble">
          <div class="bubble-meta">
            <span class="bubble-who">你</span>
            <span class="mode-tag" :class="strategyColor(item.mode)">{{ item.mode }}</span>
          </div>
          <div class="bubble-body">{{ item.question }}</div>
        </div>

        <!-- AI bubble -->
        <div class="bubble ai-bubble">
          <div class="bubble-meta">
            <span class="bubble-who ai">AI</span>
            <template v-if="item.result">
              <span class="mode-tag" :class="strategyColor(item.result.strategy_used)">
                {{ item.result.strategy_used }}
              </span>
              <span v-if="item.result.confidence" class="conf-tag">
                置信度 {{ item.result.confidence.toFixed(2) }}
              </span>
            </template>
            <button
              v-if="item.result"
              type="button"
              class="btn icon-btn sm copy-btn"
              title="复制答案"
              @click="copyAnswer(item.result!.answer)"
            >
              <svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
              </svg>
            </button>
          </div>

          <!-- Skeleton loading -->
          <div v-if="item.loading" class="skeleton-answer">
            <div class="skeleton" style="height:12px;width:90%;border-radius:4px;margin-bottom:.5rem" />
            <div class="skeleton" style="height:12px;width:75%;border-radius:4px;margin-bottom:.5rem" />
            <div class="skeleton" style="height:12px;width:60%;border-radius:4px" />
          </div>

          <div v-else-if="item.result" class="bubble-body">
            <div class="md-body" v-html="renderMd(item.result.answer)" />

            <!-- Reasoning path -->
            <details v-if="item.result.reasoning_path?.length" class="sub-section">
              <summary>推理路径（{{ item.result.reasoning_path.length }} 步）</summary>
              <ol class="path-list">
                <li v-for="(p, i) in item.result.reasoning_path" :key="i">{{ p }}</li>
              </ol>
            </details>

            <!-- Sources -->
            <details v-if="item.result.sources?.length" class="sub-section">
              <summary>引用来源（{{ item.result.sources.length }} 条）</summary>
              <ul class="source-list">
                <li v-for="(s, i) in item.result.sources" :key="i" class="source-item">
                  <span class="source-label">{{ s.filename }} · 第 {{ s.page }} 页</span>
                  <blockquote class="source-quote">{{ s.text }}</blockquote>
                </li>
              </ul>
            </details>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else class="empty-state">
      <svg width="52" height="52" fill="none" stroke="var(--muted)" stroke-width="1.2" viewBox="0 0 24 24">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/>
      </svg>
      <p>提交问题后对话将显示在这里</p>
    </div>

    <!-- Input area -->
    <div class="input-area">
      <div class="mode-select">
        <button
          v-for="m in modes"
          :key="m.value"
          type="button"
          class="mode-btn"
          :class="[m.color, { active: mode === m.value }]"
          :disabled="busy"
          @click="mode = m.value"
        >{{ m.label }}</button>
      </div>
      <div class="textarea-row">
        <textarea
          v-model="question"
          rows="1"
          placeholder="输入问题… Ctrl/Cmd + Enter 发送"
          :disabled="busy"
          class="question-input"
          @input="autoResize"
          @keydown="onKeydown"
        />
        <button type="button" class="btn primary send-btn" :disabled="busy" @click="submit">
          <span v-if="busy" class="spinner" />
          <svg v-else width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
            <line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/>
          </svg>
        </button>
      </div>
      <p class="input-hint">Ctrl / Cmd + Enter 发送 · 支持 Markdown 代码块渲染</p>
    </div>
  </div>
</template>

<style scoped>
.qpage {
  display: flex;
  flex-direction: column;
  height: calc(100vh - 100px);
  min-height: 500px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 0.75rem;
  margin-bottom: 1rem;
  flex-shrink: 0;
}
.page-desc { color: var(--muted); font-size: 0.875rem; margin-top: 0.25rem; }

/* History feed */
.history {
  flex: 1;
  overflow-y: auto;
  padding: 0.5rem 0 1rem;
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
  scroll-behavior: smooth;
}

.turn { display: flex; flex-direction: column; gap: 0.75rem; }

/* Bubbles */
.bubble {
  max-width: 88%;
  border-radius: var(--radius-lg);
  padding: 0.75rem 1rem;
  border: 1px solid var(--border);
}
.user-bubble {
  align-self: flex-end;
  background: var(--accent-light);
  border-color: transparent;
}
.ai-bubble {
  align-self: flex-start;
  background: var(--surface);
  box-shadow: var(--shadow-sm);
}
.bubble-meta {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-wrap: wrap;
  margin-bottom: 0.45rem;
}
.bubble-who {
  font-size: 0.75rem;
  font-weight: 700;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: .05em;
}
.bubble-who.ai { color: var(--accent); }
.bubble-body { font-size: 0.9rem; line-height: 1.6; white-space: pre-wrap; }

/* Mode / conf tags */
.mode-tag {
  font-size: 0.68rem;
  font-weight: 700;
  padding: 0.12rem 0.4rem;
  border-radius: 999px;
  text-transform: uppercase;
  letter-spacing: .04em;
}
.mode-auto   { background: var(--surface-3); color: var(--muted); }
.mode-vector { background: var(--processing-bg); color: var(--processing); }
.mode-graph  { background: #ede9fe; color: #7c3aed; }
.mode-hybrid { background: var(--warn-bg); color: var(--warn); }
@media (prefers-color-scheme: dark) {
  .mode-graph { background: #2e1065; color: #a78bfa; }
}
.conf-tag {
  font-size: 0.7rem;
  color: var(--muted);
}

.copy-btn { margin-left: auto; }

/* Skeleton */
.skeleton-answer { padding: 0.25rem 0; }

/* Sub sections */
.sub-section {
  margin-top: 0.75rem;
  border-top: 1px solid var(--border);
  padding-top: 0.6rem;
  font-size: 0.85rem;
}
.sub-section > summary {
  cursor: pointer;
  color: var(--muted);
  font-weight: 500;
  user-select: none;
  list-style: none;
  display: flex;
  align-items: center;
  gap: 0.3rem;
}
.sub-section > summary::before {
  content: '▶';
  font-size: 0.65rem;
  transition: transform 0.2s;
}
.sub-section[open] > summary::before { transform: rotate(90deg); }

.path-list { margin: 0.5rem 0; padding-left: 1.4rem; color: var(--text); }
.path-list li { margin: 0.2rem 0; font-size: 0.85rem; }

.source-list { list-style: none; padding: 0; margin: 0.5rem 0; display: flex; flex-direction: column; gap: 0.5rem; }
.source-item {}
.source-label { font-weight: 600; font-size: 0.8rem; color: var(--muted); }
.source-quote {
  margin: 0.25rem 0 0;
  padding: 0.35rem 0.65rem;
  border-left: 3px solid var(--accent);
  background: var(--accent-light);
  border-radius: 0 4px 4px 0;
  font-size: 0.82rem;
  color: var(--text);
}

/* Empty state */
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  color: var(--muted);
  font-size: 0.9rem;
}

/* Input area */
.input-area {
  flex-shrink: 0;
  padding-top: 0.75rem;
  border-top: 1px solid var(--border);
  margin-top: 0.5rem;
}
.mode-select {
  display: flex;
  gap: 0.35rem;
  margin-bottom: 0.6rem;
  flex-wrap: wrap;
}
.mode-btn {
  padding: 0.3rem 0.65rem;
  border-radius: 999px;
  border: 1.5px solid var(--border);
  background: var(--surface);
  color: var(--muted);
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  transition: border-color 0.15s, color 0.15s, background 0.15s;
}
.mode-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.mode-btn.mode-vector.active { background: var(--processing-bg); color: var(--processing); border-color: var(--processing); }
.mode-btn.mode-graph.active  { background: #ede9fe; color: #7c3aed; border-color: #7c3aed; }
.mode-btn.mode-hybrid.active { background: var(--warn-bg); color: var(--warn); border-color: var(--warn); }
.mode-btn.mode-auto.active   { background: var(--accent-light); color: var(--accent); border-color: var(--accent); }
@media (prefers-color-scheme: dark) {
  .mode-btn.mode-graph.active { background: #2e1065; color: #a78bfa; border-color: #7c3aed; }
}

.textarea-row {
  display: flex;
  gap: 0.5rem;
  align-items: flex-end;
}
.question-input {
  flex: 1;
  resize: none;
  overflow: hidden;
  min-height: 44px;
  max-height: 240px;
  line-height: 1.5;
}
.send-btn {
  height: 44px;
  width: 44px;
  padding: 0;
  flex-shrink: 0;
  border-radius: var(--radius);
}
.input-hint {
  margin: 0.35rem 0 0;
  font-size: 0.75rem;
  color: var(--muted);
}
</style>

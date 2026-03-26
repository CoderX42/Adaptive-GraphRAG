<script setup lang="ts">
import cytoscape from 'cytoscape'
import type { Core, NodeSingular } from 'cytoscape'
import { listDocuments } from '../api/documents'
import { getGraphVisualize } from '../api/graph'
import type { DocumentRow, GraphNode, GraphPayload } from '../api/types'
import { nextTick, onMounted, onUnmounted, ref, watch } from 'vue'

/* ── Type color palette ── */
const TYPE_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  Person:       { bg: '#3b82f6', border: '#1d4ed8', text: '#fff' },
  Organization: { bg: '#10b981', border: '#059669', text: '#fff' },
  Location:     { bg: '#f59e0b', border: '#d97706', text: '#fff' },
  Technology:   { bg: '#8b5cf6', border: '#6d28d9', text: '#fff' },
  Concept:      { bg: '#06b6d4', border: '#0891b2', text: '#fff' },
  Event:        { bg: '#ec4899', border: '#db2777', text: '#fff' },
  _default:     { bg: '#6b7280', border: '#4b5563', text: '#fff' },
}

function typeColor(type: string) {
  return TYPE_COLORS[type] ?? TYPE_COLORS['_default']
}

/* ── Layout options ── */
type LayoutName = 'cose' | 'circle' | 'concentric' | 'breadthfirst'
const LAYOUTS: { id: LayoutName; label: string }[] = [
  { id: 'cose',         label: '力导向' },
  { id: 'circle',       label: '环形' },
  { id: 'concentric',   label: '同心圆' },
  { id: 'breadthfirst', label: '层次' },
]

/* ── State ── */
const cyHost = ref<HTMLDivElement | null>(null)
let cy: Core | null = null

const docs = ref<DocumentRow[]>([])
const docFilter = ref('')
const graphQuery = ref('')
const layoutName = ref<LayoutName>('cose')
const searchText = ref('')
const payload = ref<GraphPayload | null>(null)
const loading = ref(false)
const error = ref('')
const selectedNode = ref<GraphNode | null>(null)

/* ── Convert to Cytoscape elements ── */
function toElements(data: GraphPayload) {
  const nodes = data.nodes.map(n => {
    const c = typeColor(n.type)
    return {
      data: { id: n.id, label: n.label || n.id, type: n.type || '' },
      style: {
        'background-color': c.bg,
        'border-color': c.border,
        'border-width': 2,
        color: c.text,
      },
    }
  })
  const edges = data.edges.map((e, i) => ({
    data: {
      id: `e-${i}-${e.source}-${e.target}`,
      source: e.source,
      target: e.target,
      label: e.label || '',
    },
  }))
  return [...nodes, ...edges]
}

/* ── Mount/destroy Cytoscape ── */
function mountCy(data: GraphPayload) {
  if (!cyHost.value) return
  if (cy) { cy.destroy(); cy = null }

  cy = cytoscape({
    container: cyHost.value,
    elements: toElements(data),
    style: [
      {
        selector: 'node',
        style: {
          label: 'data(label)',
          'font-size': '10px',
          'text-wrap': 'wrap',
          'text-max-width': '90px',
          'text-valign': 'center',
          'text-halign': 'center',
          width: 30,
          height: 30,
          'border-width': 2,
          'border-color': '#64748b',
        },
      },
      {
        selector: 'edge',
        style: {
          width: 1.5,
          'line-color': '#94a3b8',
          'target-arrow-color': '#94a3b8',
          'target-arrow-shape': 'triangle',
          'curve-style': 'bezier',
          label: 'data(label)',
          'font-size': '8px',
          color: '#94a3b8',
          'text-background-color': '#ffffff',
          'text-background-opacity': 0.8,
          'text-background-padding': '2px',
        },
      },
      {
        selector: '.highlighted',
        style: {
          'border-color': '#eab308',
          'border-width': 4,
          width: 38,
          height: 38,
          'z-index': 999,
        },
      },
      {
        selector: '.dimmed',
        style: { opacity: 0.2 },
      },
    ],
    layout: buildLayout(layoutName.value),
  })

  cy.on('tap', 'node', evt => {
    const node = evt.target as NodeSingular
    const id = node.id()
    const found = data.nodes.find(n => n.id === id)
    selectedNode.value = found ?? null
  })
  cy.on('tap', function(evt) {
    if (evt.target === cy) selectedNode.value = null
  })
}

function buildLayout(name: LayoutName): cytoscape.LayoutOptions {
  if (name === 'cose') {
    return { name: 'cose', animate: false, padding: 30, nodeRepulsion: () => 8000, idealEdgeLength: () => 80 } as unknown as cytoscape.LayoutOptions
  }
  if (name === 'concentric') {
    return {
      name: 'concentric',
      animate: false,
      padding: 30,
      concentric: (n: NodeSingular) => n.degree(false),
      levelWidth: () => 2,
    } as unknown as cytoscape.LayoutOptions
  }
  return { name, animate: false, padding: 30 } as cytoscape.LayoutOptions
}

function reLayout() {
  if (!cy) return
  cy.layout(buildLayout(layoutName.value)).run()
}

/* ── Load graph data ── */
async function load() {
  loading.value = true
  error.value = ''
  searchText.value = ''
  selectedNode.value = null
  try {
    const g = await getGraphVisualize({
      query: graphQuery.value.trim(),
      doc_id: docFilter.value.trim(),
    })
    payload.value = g
    await nextTick()
    mountCy(g)
  } catch (e: unknown) {
    const ax = e as { response?: { data?: { detail?: string } } }
    error.value = ax.response?.data?.detail ?? (e instanceof Error ? e.message : '加载图谱失败')
  } finally {
    loading.value = false
  }
}

/* ── Search highlight ── */
watch(searchText, q => {
  if (!cy) return
  const term = q.trim().toLowerCase()
  if (!term) {
    cy.elements().removeClass('dimmed highlighted')
    return
  }
  cy.nodes().forEach(n => {
    const label: string = (n.data('label') as string).toLowerCase()
    if (label.includes(term)) {
      n.removeClass('dimmed').addClass('highlighted')
    } else {
      n.addClass('dimmed').removeClass('highlighted')
    }
  })
  cy.edges().addClass('dimmed')
})

/* ── Zoom controls ── */
function fitAll() { cy?.fit(undefined, 30) }
function zoomIn() { if (cy) cy.zoom({ level: cy.zoom() * 1.3, renderedPosition: cy.pan() }) }
function zoomOut() { if (cy) cy.zoom({ level: cy.zoom() / 1.3, renderedPosition: cy.pan() }) }

/* ── Lifecycle ── */
onMounted(async () => {
  try { docs.value = await listDocuments() } catch { /* optional */ }
  await load()
})
onUnmounted(() => { if (cy) { cy.destroy(); cy = null } })
</script>

<template>
  <div class="gpage">
    <!-- Page header -->
    <div class="page-header">
      <div>
        <h2>知识图谱</h2>
        <p class="page-desc">图谱由文档中自动抽取的实体与关系构成；点击节点查看详情，搜索框可高亮匹配节点。</p>
      </div>
    </div>

    <!-- Controls -->
    <div class="controls-card">
      <div class="controls-grid">
        <div class="ctrl-field">
          <label>查询子图（可选）</label>
          <input
            v-model="graphQuery"
            type="text"
            placeholder="输入实体名，展示邻域子图"
            :disabled="loading"
          />
        </div>
        <div class="ctrl-field">
          <label>文档过滤（可选）</label>
          <select v-model="docFilter" :disabled="loading">
            <option value="">全部文档</option>
            <option
              v-for="d in docs.filter(x => x.status === 'ready')"
              :key="d.id"
              :value="d.id"
            >{{ d.filename }}</option>
          </select>
        </div>
        <div class="ctrl-field">
          <label>节点搜索 / 高亮</label>
          <input
            v-model="searchText"
            type="search"
            placeholder="输入节点名称高亮"
            :disabled="!payload"
          />
        </div>
        <div class="ctrl-field ctrl-actions">
          <label>操作</label>
          <div class="action-row">
            <button type="button" class="btn primary" :disabled="loading" @click="load">
              <span v-if="loading" class="spinner" />
              <svg v-else width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24">
                <polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/>
                <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
              </svg>
              {{ loading ? '加载中…' : '加载 / 刷新' }}
            </button>
          </div>
        </div>
      </div>

      <!-- Layout switch -->
      <div class="layout-row" v-if="payload">
        <span class="layout-label">布局：</span>
        <button
          v-for="l in LAYOUTS"
          :key="l.id"
          type="button"
          class="layout-btn"
          :class="{ active: layoutName === l.id }"
          @click="layoutName = l.id; reLayout()"
        >{{ l.label }}</button>

        <div class="zoom-row">
          <button type="button" class="btn sm icon-btn" title="Fit All" @click="fitAll">⊡</button>
          <button type="button" class="btn sm icon-btn" title="Zoom in" @click="zoomIn">+</button>
          <button type="button" class="btn sm icon-btn" title="Zoom out" @click="zoomOut">−</button>
        </div>
      </div>
    </div>

    <!-- Stats cards -->
    <div v-if="payload" class="stat-row">
      <div class="stat-card">
        <span class="stat-v">{{ payload.stats.nodes }}</span>
        <span class="stat-l">全库节点</span>
      </div>
      <div class="stat-card">
        <span class="stat-v">{{ payload.stats.edges }}</span>
        <span class="stat-l">全库边</span>
      </div>
      <div class="stat-card accent">
        <span class="stat-v">{{ payload.stats.shown_nodes }}</span>
        <span class="stat-l">展示节点</span>
      </div>
      <div class="stat-card accent">
        <span class="stat-v">{{ payload.stats.shown_edges }}</span>
        <span class="stat-l">展示边</span>
      </div>
    </div>

    <p v-if="error" class="err">{{ error }}</p>

    <!-- Main area: canvas + side panel -->
    <div class="canvas-area">
      <!-- Legend -->
      <div class="legend">
        <div class="legend-title">节点类型</div>
        <div
          v-for="(color, type) in TYPE_COLORS"
          :key="type"
          v-show="type !== '_default'"
          class="legend-item"
        >
          <span class="legend-dot" :style="{ background: color.bg }" />
          <span>{{ type }}</span>
        </div>
        <div class="legend-item">
          <span class="legend-dot" :style="{ background: TYPE_COLORS['_default'].bg }" />
          <span>其他</span>
        </div>
      </div>

      <!-- Cytoscape container -->
      <div class="cy-wrap">
        <!-- Empty state -->
        <div v-if="payload && !payload.nodes.length" class="empty-graph">
          <svg width="52" height="52" fill="none" stroke="var(--muted)" stroke-width="1.2" viewBox="0 0 24 24">
            <circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/>
            <line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/>
            <line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/>
          </svg>
          <p>暂无图谱数据</p>
          <p class="muted small">请先上传文档，系统将自动抽取实体与关系</p>
        </div>
        <div v-show="!loading && payload?.nodes.length" ref="cyHost" class="cy" />
        <div v-if="loading" class="cy-loading">
          <span class="spinner" style="width:2rem;height:2rem;border-width:3px" />
          <p>正在加载图谱…</p>
        </div>
      </div>

      <!-- Node detail panel -->
      <Transition name="slide">
        <div v-if="selectedNode" class="detail-panel">
          <div class="detail-header">
            <span
              class="detail-type-dot"
              :style="{ background: typeColor(selectedNode.type).bg }"
            />
            <strong class="detail-name">{{ selectedNode.label || selectedNode.id }}</strong>
            <button type="button" class="btn icon-btn sm" @click="selectedNode = null" title="关闭">✕</button>
          </div>
          <dl class="detail-dl">
            <dt>类型</dt>
            <dd>
              <span class="type-badge" :style="{ background: typeColor(selectedNode.type).bg, color: '#fff' }">
                {{ selectedNode.type || '—' }}
              </span>
            </dd>

            <dt>节点 ID</dt>
            <dd class="mono small">{{ selectedNode.id }}</dd>

            <template v-if="selectedNode.aliases?.length">
              <dt>别名</dt>
              <dd>{{ selectedNode.aliases.join('、') }}</dd>
            </template>

            <template v-if="selectedNode.source_docs?.length">
              <dt>来源文档</dt>
              <dd>
                <span
                  v-for="d in selectedNode.source_docs"
                  :key="d"
                  class="doc-tag"
                >{{ d }}</span>
              </dd>
            </template>
          </dl>
        </div>
      </Transition>
    </div>
  </div>
</template>

<style scoped>
.gpage { display: flex; flex-direction: column; }

/* Header */
.page-header { margin-bottom: 1rem; }
.page-desc { color: var(--muted); font-size: 0.875rem; margin-top: 0.25rem; }

/* Controls card */
.controls-card {
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 1rem 1.25rem;
  margin-bottom: 1rem;
  box-shadow: var(--shadow-sm);
}
.controls-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 0.75rem 1rem;
}
.ctrl-field label {
  display: block;
  font-size: 0.78rem;
  font-weight: 600;
  color: var(--muted);
  margin-bottom: 0.3rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}
.ctrl-actions { display: flex; flex-direction: column; }
.action-row { display: flex; gap: 0.5rem; align-items: center; }

.layout-row {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin-top: 0.75rem;
  padding-top: 0.75rem;
  border-top: 1px solid var(--border);
}
.layout-label { font-size: 0.8rem; color: var(--muted); font-weight: 600; }
.layout-btn {
  padding: 0.25rem 0.65rem;
  border-radius: 999px;
  border: 1.5px solid var(--border);
  background: var(--surface-3);
  color: var(--muted);
  font-size: 0.78rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}
.layout-btn.active, .layout-btn:hover {
  background: var(--accent-light);
  color: var(--accent);
  border-color: var(--accent);
}
.zoom-row {
  display: flex;
  gap: 0.25rem;
  margin-left: auto;
  font-size: 1rem;
}
.zoom-row .icon-btn { font-size: 0.95rem; width: 28px; height: 28px; }

/* Stat row */
.stat-row {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  margin-bottom: 1rem;
}
.stat-card {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  padding: 0.45rem 0.9rem;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  box-shadow: var(--shadow-sm);
  font-size: 0.82rem;
}
.stat-card.accent .stat-v { color: var(--accent); }
.stat-v { font-weight: 700; font-size: 1.05rem; }
.stat-l { color: var(--muted); font-size: 0.77rem; }

.err { color: var(--danger); margin: 0 0 0.75rem; font-size: 0.875rem; }

/* Canvas area */
.canvas-area {
  display: flex;
  gap: 0.75rem;
  align-items: flex-start;
  flex: 1;
  min-height: 0;
}

/* Legend */
.legend {
  width: 110px;
  flex-shrink: 0;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  padding: 0.6rem 0.75rem;
  font-size: 0.78rem;
  box-shadow: var(--shadow-sm);
}
.legend-title {
  font-weight: 700;
  color: var(--muted);
  text-transform: uppercase;
  font-size: 0.7rem;
  letter-spacing: .04em;
  margin-bottom: 0.5rem;
}
.legend-item { display: flex; align-items: center; gap: 0.35rem; margin: 0.3rem 0; }
.legend-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }

/* Cytoscape wrap */
.cy-wrap {
  flex: 1;
  position: relative;
  min-height: 480px;
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  overflow: hidden;
  background: var(--surface);
  box-shadow: var(--shadow-sm);
}
.cy {
  width: 100%;
  height: 100%;
  min-height: 480px;
}
.cy-loading {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  color: var(--muted);
  font-size: 0.875rem;
}
.empty-graph {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  color: var(--muted);
  font-size: 0.9rem;
}

/* Detail panel */
.detail-panel {
  width: 220px;
  flex-shrink: 0;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 0.9rem 1rem;
  box-shadow: var(--shadow);
  font-size: 0.85rem;
  overflow-y: auto;
  max-height: 520px;
}
.detail-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
}
.detail-type-dot { width: 10px; height: 10px; border-radius: 50%; flex-shrink: 0; }
.detail-name { flex: 1; font-size: 0.9rem; word-break: break-all; }
.detail-dl { margin: 0; }
.detail-dl dt {
  font-size: 0.72rem;
  font-weight: 700;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: .04em;
  margin-top: 0.6rem;
}
.detail-dl dd { margin: 0.2rem 0 0; color: var(--text); word-break: break-all; }

.type-badge {
  font-size: 0.72rem;
  font-weight: 700;
  padding: 0.15rem 0.45rem;
  border-radius: 999px;
}
.doc-tag {
  display: inline-block;
  font-size: 0.7rem;
  background: var(--surface-3);
  border: 1px solid var(--border);
  border-radius: 4px;
  padding: 0.1rem 0.4rem;
  margin: 0.15rem 0.15rem 0 0;
  word-break: break-all;
}

/* Slide transition */
.slide-enter-active, .slide-leave-active { transition: opacity 0.2s, transform 0.2s; }
.slide-enter-from { opacity: 0; transform: translateX(12px); }
.slide-leave-to   { opacity: 0; transform: translateX(12px); }
</style>

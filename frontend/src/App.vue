<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { RouterLink, RouterView } from 'vue-router'
import ToastContainer from './components/ToastContainer.vue'

const scrolled = ref(false)

function onScroll() {
  scrolled.value = window.scrollY > 4
}

onMounted(() => window.addEventListener('scroll', onScroll, { passive: true }))
onUnmounted(() => window.removeEventListener('scroll', onScroll))

const navLinks = [
  { to: '/', name: 'documents', label: '文档管理', icon: docIcon() },
  { to: '/query', name: 'query', label: '智能问答', icon: chatIcon() },
  { to: '/graph', name: 'graph', label: '知识图谱', icon: graphIcon() },
]

function docIcon() { return `<svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>` }
function chatIcon() { return `<svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"/></svg>` }
function graphIcon() { return `<svg width="15" height="15" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></svg>` }

</script>

<template>
  <div class="layout">
    <header class="top" :class="{ scrolled }">
      <div class="brand">
        <svg class="brand-icon" width="28" height="28" viewBox="0 0 28 28" fill="none">
          <rect width="28" height="28" rx="8" fill="var(--accent)"/>
          <circle cx="8" cy="14" r="2.5" fill="white"/>
          <circle cx="20" cy="8" r="2.5" fill="white"/>
          <circle cx="20" cy="20" r="2.5" fill="white"/>
          <line x1="10.2" y1="13" x2="17.8" y2="9.2" stroke="white" stroke-width="1.5"/>
          <line x1="10.2" y1="15" x2="17.8" y2="18.8" stroke="white" stroke-width="1.5"/>
        </svg>
        <div>
          <h1 class="brand-name">Adaptive-GraphRAG</h1>
          <span class="brand-sub">本地 · 向量 + 知识图谱 · 自适应检索</span>
        </div>
      </div>

      <nav class="nav" role="navigation">
        <RouterLink
          v-for="link in navLinks"
          :key="link.to"
          :to="link.to"
          class="nav-link"
          :title="link.label"
        >
          <span class="nav-icon" v-html="link.icon" />
          {{ link.label }}
        </RouterLink>
        <div class="nav-divider" />
        <a class="nav-link ext" href="/ui" target="_blank" rel="noopener noreferrer" title="Gradio 界面">
          <svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
          Gradio
        </a>
        <a class="nav-link ext" href="/docs" target="_blank" rel="noopener noreferrer" title="API 文档">
          <svg width="13" height="13" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></svg>
          API 文档
        </a>
      </nav>
    </header>

    <main class="main">
      <div class="page-wrap">
        <RouterView v-slot="{ Component }">
          <Transition name="page" mode="out-in">
            <component :is="Component" />
          </Transition>
        </RouterView>
      </div>
    </main>
  </div>
  <ToastContainer />
</template>

<style scoped>
.layout {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

/* ── Header ── */
.top {
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0.65rem 1.5rem;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
  transition: box-shadow 0.2s;
}
.top.scrolled {
  box-shadow: var(--shadow);
}

/* ── Brand ── */
.brand {
  display: flex;
  align-items: center;
  gap: 0.7rem;
}
.brand-icon { flex-shrink: 0; }
.brand-name {
  font-size: 1rem;
  font-weight: 700;
  letter-spacing: -0.02em;
  color: var(--text-h);
}
.brand-sub {
  display: block;
  font-size: 0.7rem;
  color: var(--muted);
  margin-top: 0.1rem;
}

/* ── Nav ── */
.nav {
  display: flex;
  align-items: center;
  gap: 0.25rem;
}
.nav-divider {
  width: 1px;
  height: 1.2rem;
  background: var(--border);
  margin: 0 0.4rem;
}
.nav-link {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--muted);
  text-decoration: none;
  padding: 0.4rem 0.65rem;
  border-radius: var(--radius);
  border: 1px solid transparent;
  transition: color 0.15s, background 0.15s, border-color 0.15s;
  position: relative;
}
.nav-link:hover {
  color: var(--text-h);
  background: var(--surface-3);
}
.nav-link.router-link-active {
  color: var(--accent);
  background: var(--accent-light);
  border-color: transparent;
  font-weight: 600;
}
.nav-link.ext {
  font-size: 0.8rem;
  opacity: 0.8;
}
.nav-link.ext:hover { opacity: 1; }
.nav-icon {
  display: flex;
  align-items: center;
}

/* ── Main ── */
.main {
  flex: 1;
  padding: 1.5rem 1.5rem 3rem;
}
.page-wrap {
  max-width: 1280px;
  margin: 0 auto;
}

/* ── Page transition ── */
.page-enter-active, .page-leave-active { transition: opacity 0.15s, transform 0.15s; }
.page-enter-from { opacity: 0; transform: translateY(6px); }
.page-leave-to   { opacity: 0; transform: translateY(-4px); }
</style>

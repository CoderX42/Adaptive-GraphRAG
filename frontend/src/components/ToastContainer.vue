<script setup lang="ts">
import { useToast } from '../composables/useToast'

const { toasts } = useToast()

const icons: Record<string, string> = {
  success: '✓',
  error: '✕',
  info: 'ℹ',
}
</script>

<template>
  <Teleport to="body">
    <div class="toast-wrap" aria-live="polite">
      <TransitionGroup name="toast">
        <div
          v-for="t in toasts"
          :key="t.id"
          class="toast"
          :class="t.type"
        >
          <span class="toast-icon">{{ icons[t.type] }}</span>
          <span>{{ t.message }}</span>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-enter-active, .toast-leave-active { transition: opacity 0.2s, transform 0.2s; }
.toast-enter-from { opacity: 0; transform: translateY(8px); }
.toast-leave-to   { opacity: 0; transform: translateY(8px); }
.toast-icon { font-size: 0.9rem; }
</style>

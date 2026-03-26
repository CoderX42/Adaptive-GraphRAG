import { createRouter, createWebHistory } from 'vue-router'
import DocumentsView from '../views/DocumentsView.vue'
import QueryView from '../views/QueryView.vue'
import GraphView from '../views/GraphView.vue'

export const router = createRouter({
  history: createWebHistory('/app/'),
  routes: [
    { path: '/', name: 'documents', component: DocumentsView },
    { path: '/query', name: 'query', component: QueryView },
    { path: '/graph', name: 'graph', component: GraphView },
  ],
})

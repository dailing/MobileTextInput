import { createRouter, createWebHistory } from 'vue-router'
import Panel from '../views/Panel.vue'
import Editor from '../views/Editor.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'Panel', component: Panel },
    { path: '/edit', name: 'Editor', component: Editor },
  ],
})

export default router

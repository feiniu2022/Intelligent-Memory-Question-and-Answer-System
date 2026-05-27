import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  { path: '/login', name: 'Login', component: () => import('../views/Login.vue'), meta: { public: true } },
  { path: '/', name: 'Chat', component: () => import('../views/Chat.vue') },
  { path: '/knowledge', name: 'Knowledge', component: () => import('../views/Knowledge.vue') },
  { path: '/memory', name: 'Memory', component: () => import('../views/Memory.vue') },
  { path: '/rag', name: 'RAG', component: () => import('../views/RAGQuery.vue') },
  { path: '/audit', name: 'Audit', component: () => import('../views/Audit.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to, from, next) => {
  const token = localStorage.getItem('token')
  if (!to.meta.public && !token) {
    next('/login')
  } else {
    next()
  }
})

export default router
// Application routes. Legacy URLs using ?tab= are redirected so old
// links keep working.
import { createRouter, createWebHistory } from 'vue-router'
import EntitiesView from './views/EntitiesView.vue'
import LoginView from './views/LoginView.vue'
import RegisterView from './views/RegisterView.vue'
import SettingsView from './views/SettingsView.vue'
import StreamView from './components/stream/StreamView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'entities', component: EntitiesView },
    { path: '/stream', name: 'stream', component: StreamView },
    { path: '/login', name: 'login', component: LoginView },
    { path: '/register', name: 'register', component: RegisterView },
    {
      path: '/:userId(\\d+)/settings',
      name: 'settings',
      component: SettingsView,
      props: true,
    },
    { path: '/:pathMatch(.*)*', redirect: '/' },
  ],
})

// Legacy tab query param: /?tab=stream -> /stream
router.beforeEach((to) => {
  if (to.path === '/' && to.query.tab === 'stream') {
    return { path: '/stream', query: {} }
  }
  if (to.path === '/' && to.query.tab === 'entities') {
    return { path: '/', query: { ...to.query, tab: undefined } }
  }
  return true
})

export default router

// Application routes. Legacy URLs using ?entity= or ?tab= are redirected
// so old links keep working.
import { createRouter, createWebHistory } from 'vue-router'
import DashboardView from './views/DashboardView.vue'
import EntitiesView from './views/EntitiesView.vue'
import EntityHistoryView from './views/EntityHistoryView.vue'
import EntityListView from './views/EntityListView.vue'
import EntityTermsView from './views/EntityTermsView.vue'
import UserListView from './views/UserListView.vue'
import CreateItemView from './views/CreateItemView.vue'
import CreatePropertyView from './views/CreatePropertyView.vue'
import CreateLexemeView from './views/CreateLexemeView.vue'
import LoginView from './views/LoginView.vue'
import RecentChangesView from './views/RecentChangesView.vue'
import RegisterView from './views/RegisterView.vue'
import SettingsView from './views/SettingsView.vue'
import StatisticsView from './views/StatisticsView.vue'
import StreamView from './components/stream/StreamView.vue'

const router = createRouter({
  history: createWebHistory(),
  // Scroll to statement anchors: /entity/Q42#P31 or #P31-<n>
  scrollBehavior(to) {
    if (to.hash) return { el: to.hash }
    return {}
  },
  routes: [
    { path: '/', name: 'dashboard', component: DashboardView },
    {
      path: '/entity/:entityId([QPLE]\\d+)',
      name: 'entity',
      component: EntitiesView,
    },
    { path: '/list', name: 'list', component: EntityListView },
    { path: '/list-users', name: 'list-users', component: UserListView },
    {
      path: '/:entityId([QPLE]\\d+)/history',
      name: 'history',
      component: EntityHistoryView,
    },
    {
      // Shareable diff URL: revision <newRev> vs <oldRev>
      path: '/:entityId([QPLE]\\d+)/history/:newRev(\\d+)/:oldRev(\\d+)',
      name: 'history-diff',
      component: EntityHistoryView,
    },
    {
      path: '/:entityId([QPLE]\\d+)/terms',
      name: 'terms',
      component: EntityTermsView,
    },
    { path: '/create-item', name: 'create-item', component: CreateItemView },
    {
      path: '/create-property',
      name: 'create-property',
      component: CreatePropertyView,
    },
    { path: '/create-lexeme', name: 'create-lexeme', component: CreateLexemeView },
    { path: '/recent', name: 'recent', component: RecentChangesView },
    { path: '/statistics', name: 'statistics', component: StatisticsView },
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

// Legacy URLs keep working:
// /?tab=stream -> /stream
// /?entity=Q42 -> /entity/Q42
router.beforeEach((to) => {
  if (to.path === '/' && to.query.tab === 'stream') {
    return { path: '/stream', query: {} }
  }
  if (typeof to.query.entity === 'string' && to.query.entity) {
    return { path: `/entity/${to.query.entity}`, query: { ...to.query, entity: undefined } }
  }
  return true
})

export default router

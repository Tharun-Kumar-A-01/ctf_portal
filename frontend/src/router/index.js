import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

import Login from '../views/Login.vue'
import AdminUsers from '../views/admin/AdminUsers.vue'
import AdminChallenges from '../views/admin/AdminChallenges.vue'
import Challenges from '../views/user/Challenges.vue'
import ChallengeDetail from '../views/user/ChallengeDetail.vue'
import TeamView from '../views/user/Team.vue'
import Leaderboard from '../views/Leaderboard.vue'

import Traffic from '../views/admin/Traffic.vue'

const routes = [
  { path: '/', redirect: '/leaderboard' },
  { path: '/login', name: 'Login', component: Login },
  { path: '/banned', name: 'Banned', component: () => import('../views/Banned.vue') },
  { 
    path: '/admin', 
    redirect: '/admin/users'
  },
  { 
    path: '/admin/users', 
    name: 'AdminUsers', 
    component: AdminUsers,
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  { 
    path: '/admin/challenges', 
    name: 'AdminChallenges', 
    component: AdminChallenges,
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  { 
    path: '/admin/traffic',  
    name: 'AdminTraffic', 
    component: Traffic,
    meta: { requiresAuth: true, requiresAdmin: true }
  },
  { 
    path: '/challenges', 
    name: 'Challenges', 
    component: Challenges,
    meta: { requiresAuth: true, requiresUser: true }
  },
  {
    path: '/challenges/:id',
    name: 'ChallengeDetail',
    component: ChallengeDetail,
    meta: { requiresAuth: true, requiresUser: true }
  },
  { 
    path: '/team', 
    name: 'Team', 
    component: TeamView,
    meta: { requiresAuth: true, requiresUser: true }
  },
  { 
    path: '/leaderboard', 
    name: 'Leaderboard', 
    component: Leaderboard
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to, from) => {
  const authStore = useAuthStore()
  
  if (!authStore.user && authStore.token) {
    await authStore.fetchUser()
  }

  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    return '/login'
  }
  
  if (to.meta.requiresAdmin && !authStore.isAdmin) {
    return authStore.isAuthenticated ? '/challenges' : '/login'
  }
  
  if (to.meta.requiresUser && authStore.isAdmin) {
    return '/admin'
  }

  if (to.path === '/login' && authStore.isAuthenticated) {
    return authStore.isAdmin ? '/admin' : '/challenges'
  }
})

export default router

import { mount } from '@vue/test-utils'
import { describe, it, expect, beforeEach } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import NavBar from '../src/components/NavBar.vue'
import { useAuthStore } from '../src/stores/auth'
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'Home', component: { template: '<div></div>' } },
    { path: '/login', name: 'Login', component: { template: '<div></div>' } },
    { path: '/leaderboard', name: 'Leaderboard', component: { template: '<div></div>' } },
    { path: '/admin', name: 'AdminDashboard', component: { template: '<div></div>' } },
    { path: '/admin/traffic', name: 'AdminTraffic', component: { template: '<div></div>' } },
    { path: '/challenges', name: 'Challenges', component: { template: '<div></div>' } },
    { path: '/team', name: 'Team', component: { template: '<div></div>' } },
  ]
})

describe('NavBar.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders LOGIN button for unauthenticated users', async () => {
    const wrapper = mount(NavBar, {
      global: {
        plugins: [router]
      }
    })
    
    expect(wrapper.text()).toContain('LOGIN')
    expect(wrapper.text()).toContain('LEADERBOARD')
    expect(wrapper.text()).not.toContain('LOGOUT')
    expect(wrapper.text()).not.toContain('TRAFFIC')
  })

  it('renders admin tabs for admin users', async () => {
    const authStore = useAuthStore()
    authStore.token = 'fake-token'
    authStore.user = { role: 'admin' }
    
    const wrapper = mount(NavBar, {
      global: {
        plugins: [router]
      }
    })
    
    await wrapper.vm.$nextTick()
    
    expect(wrapper.text()).toContain('TEAMS & USERS')
    expect(wrapper.text()).toContain('CHALLENGES')
    expect(wrapper.text()).toContain('TRAFFIC')
    expect(wrapper.text()).toContain('LOGOUT')
    expect(wrapper.text()).not.toContain('LOGIN')
  })

  it('renders normal user tabs for regular users', async () => {
    const authStore = useAuthStore()
    authStore.token = 'fake-token'
    authStore.user = { role: 'player' }
    
    const wrapper = mount(NavBar, {
      global: {
        plugins: [router]
      }
    })
    
    await wrapper.vm.$nextTick()
    
    expect(wrapper.text()).toContain('CHALLENGES')
    expect(wrapper.text()).toContain('TEAM')
    expect(wrapper.text()).toContain('LOGOUT')
    expect(wrapper.text()).not.toContain('TRAFFIC')
    expect(wrapper.text()).not.toContain('LOGIN')
  })
})

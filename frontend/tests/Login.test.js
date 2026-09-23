import { mount } from '@vue/test-utils'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import Login from '../src/views/Login.vue'
import { useAuthStore } from '../src/stores/auth'
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'Login', component: { template: '<div></div>' } },
    { path: '/leaderboard', name: 'Leaderboard', component: { template: '<div></div>' } },
    { path: '/:pathMatch(.*)*', name: 'CatchAll', component: { template: '<div></div>' } }
  ]
})

describe('Login.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('renders email and password inputs', () => {
    const wrapper = mount(Login, {
      global: { plugins: [router] }
    })
    
    expect(wrapper.find('input[type="email"]').exists()).toBe(true)
    expect(wrapper.find('input[type="password"]').exists()).toBe(true)
    expect(wrapper.find('button[type="submit"]').exists()).toBe(true)
  })

  it('calls authStore.login on form submit', async () => {
    const wrapper = mount(Login, {
      global: { plugins: [router] }
    })
    const authStore = useAuthStore()
    
    // Mock the login action
    const loginSpy = vi.spyOn(authStore, 'login').mockResolvedValue()
    
    await wrapper.find('input[type="email"]').setValue('admin@ctf.com')
    await wrapper.find('input[type="password"]').setValue('admin123')
    await wrapper.find('form').trigger('submit.prevent')
    
    expect(loginSpy).toHaveBeenCalledWith('admin@ctf.com', 'admin123')
  })
  
  it('displays error message if login fails', async () => {
    const wrapper = mount(Login, {
      global: { plugins: [router] }
    })
    const authStore = useAuthStore()
    
    vi.spyOn(authStore, 'login').mockRejectedValue(new Error('Invalid credentials'))
    
    await wrapper.find('input[type="email"]').setValue('user@ctf.com')
    await wrapper.find('input[type="password"]').setValue('wrong')
    await wrapper.find('form').trigger('submit.prevent')
    
    // Wait for promise rejection to handle and update DOM
    await new Promise(resolve => setTimeout(resolve, 0))
    await wrapper.vm.$nextTick()
    
    expect(wrapper.text()).toContain('Invalid credentials')
  })
})

import { defineStore } from 'pinia'
import { fetchApi } from '../api/client'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: null,
    token: localStorage.getItem('token') || null,
  }),
  getters: {
    isAuthenticated: (state) => !!state.token,
    isAdmin: (state) => state.user?.role === 'admin'
  },
  actions: {
    async login(email, password) {
      const data = await fetchApi('/auth/login', {
        method: 'POST',
        body: JSON.stringify({ email, password })
      })
      this.token = data.access_token
      this.user = data.user
      localStorage.setItem('token', data.access_token)
    },
    async fetchUser() {
      if (!this.token) return
      try {
        const data = await fetchApi('/auth/me')
        this.user = data.user
      } catch (e) {
        this.logout()
      }
    },
    logout() {
      this.token = null
      this.user = null
      localStorage.removeItem('token')
    }
  }
})

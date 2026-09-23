import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '../src/stores/auth'
import * as client from '../src/api/client'

// Mocks
vi.mock('../src/api/client', () => ({
  fetchApi: vi.fn()
}))

describe('Auth Store (Pinia)', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.clearAllMocks()
  })

  it('Initializes with default empty state', () => {
    const store = useAuthStore()
    expect(store.user).toBeNull()
    expect(store.token).toBeNull()
    expect(store.isAuthenticated).toBe(false)
  })

  it('Successfully executes login flow', async () => {
    const store = useAuthStore()
    
    // Mock the API response
    client.fetchApi.mockResolvedValue({
      access_token: 'fake-jwt-token',
      user: { id: 1, email: 'test@ctf.com', role: 'admin' }
    })
    
    await store.login('test@ctf.com', 'pass123')
    
    expect(client.fetchApi).toHaveBeenCalledWith('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email: 'test@ctf.com', password: 'pass123' })
    })
    
    expect(store.token).toBe('fake-jwt-token')
    expect(store.user.email).toBe('test@ctf.com')
    expect(store.isAdmin).toBe(true)
    expect(localStorage.getItem('token')).toBe('fake-jwt-token')
  })

  it('Properly logs out and destroys token', async () => {
    const store = useAuthStore()
    store.token = 'existing-token'
    store.user = { id: 1 }
    localStorage.setItem('token', 'existing-token')
    
    store.logout()
    
    expect(store.token).toBeNull()
    expect(store.user).toBeNull()
    expect(localStorage.getItem('token')).toBeNull()
  })
})

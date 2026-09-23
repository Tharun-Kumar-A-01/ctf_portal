import { mount, flushPromises } from '@vue/test-utils'
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import Leaderboard from '../src/views/Leaderboard.vue'
import { useAuthStore } from '../src/stores/auth'
import * as client from '../src/api/client'
import { createRouter, createWebHistory } from 'vue-router'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', name: 'Login', component: { template: '<div></div>' } },
    { path: '/leaderboard', name: 'Leaderboard', component: { template: '<div></div>' } },
    { path: '/:pathMatch(.*)*', name: 'CatchAll', component: { template: '<div></div>' } }
  ]
})

// Mocks
vi.mock('../src/api/client', () => ({
  fetchApi: vi.fn()
}))

// Mock NavBar to isolate tests
vi.mock('../src/components/NavBar.vue', () => ({
  default: {
    name: 'NavBar',
    template: '<div>NavBar Mock</div>'
  }
}))

describe('Leaderboard.vue', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    vi.useFakeTimers()
  })
  
  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders podium and list correctly', async () => {
    const rankings = [
      { team_id: 1, rank: 1, team_name: 'Alpha', score: 1000 },
      { team_id: 2, rank: 2, team_name: 'Beta', score: 900 },
      { team_id: 3, rank: 3, team_name: 'Gamma', score: 800 },
      { team_id: 4, rank: 4, team_name: 'Delta', score: 700 }
    ]
    
    client.fetchApi.mockResolvedValue({ rankings })
    
    const wrapper = mount(Leaderboard, {
      global: { plugins: [router] }
    })
    
    await flushPromises()
    
    // Check podium spots
    expect(wrapper.find('.gold .team-name').text()).toBe('Alpha')
    expect(wrapper.find('.silver .team-name').text()).toBe('Beta')
    expect(wrapper.find('.bronze .team-name').text()).toBe('Gamma')
    
    // Check list item
    const listItems = wrapper.findAll('.data-item')
    expect(listItems.length).toBe(1)
    expect(listItems[0].text()).toContain('Delta')
  })

  it('highlights current users team', async () => {
    const authStore = useAuthStore()
    authStore.token = 'fake'
    authStore.user = { team_id: 4 }
    
    const rankings = [
      { team_id: 1, rank: 1, team_name: 'Alpha', score: 1000 },
      { team_id: 2, rank: 2, team_name: 'Beta', score: 900 },
      { team_id: 3, rank: 3, team_name: 'Gamma', score: 800 },
      { team_id: 4, rank: 4, team_name: 'Delta', score: 700 }
    ]
    
    client.fetchApi.mockResolvedValue({ rankings })
    
    const wrapper = mount(Leaderboard, {
      global: { plugins: [router] }
    })
    
    await flushPromises()
    
    const myTeamRow = wrapper.find('.my-team')
    expect(myTeamRow.exists()).toBe(true)
    expect(myTeamRow.text()).toContain('(YOU)')
  })

  it('prevents XSS injections in team names', async () => {
    const maliciousName = '<script>alert("xss")</script><img src="x" onerror="alert(1)">'
    
    const rankings = [
      { team_id: 1, rank: 1, team_name: maliciousName, score: 1000 }
    ]
    
    client.fetchApi.mockResolvedValue({ rankings })
    
    const wrapper = mount(Leaderboard, {
      global: { plugins: [router] }
    })
    
    await flushPromises()
    
    // Vue template binding {{ }} automatically escapes HTML
    // We assert that the literal script tags are in the text content, meaning they were NOT evaluated as HTML
    expect(wrapper.find('.gold .team-name').text()).toBe(maliciousName)
    
    // Assert no raw scripts were injected into the DOM
    expect(wrapper.element.innerHTML).not.toContain('<script>alert("xss")</script>')
  })
})

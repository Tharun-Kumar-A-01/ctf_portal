<template>
  <header class="user-header boxy-card">
    <h2 class="brand">{{ title }}</h2>
    <div class="actions">
      <!-- IF NOT AUTHENTICATED -->
      <template v-if="!authStore.isAuthenticated">
        <button v-if="route.name !== 'Leaderboard'" class="btn" @click="router.push('/leaderboard')">LEADERBOARD</button>
        <button v-if="route.name !== 'Login'" class="btn" @click="router.push('/login')">LOGIN</button>
      </template>

      <!-- IF ADMIN -->
      <template v-else-if="authStore.isAdmin">
        <button class="btn" @click="router.push('/leaderboard')" :class="{ active: route.name === 'Leaderboard' }">LEADERBOARD</button>
        
        <button class="btn" @click="router.push('/admin/users')" :class="{ active: route.name === 'AdminUsers' }">TEAMS & USERS</button>
        <button class="btn" @click="router.push('/admin/challenges')" :class="{ active: route.name === 'AdminChallenges' }">CHALLENGES</button>

        <button class="btn" @click="router.push('/admin/traffic')" :class="{ active: route.name === 'AdminTraffic' }">TRAFFIC</button>
        <button class="btn error-btn" @click="logout">LOGOUT</button>
      </template>

      <!-- IF NORMAL USER -->
      <template v-else>
        <button class="btn" @click="router.push('/leaderboard')" :class="{ active: route.name === 'Leaderboard' }">LEADERBOARD</button>
        <button class="btn" @click="router.push('/challenges')" :class="{ active: route.name === 'Challenges' || route.name === 'ChallengeDetail' }">CHALLENGES</button>
        <button class="btn" @click="router.push('/team')" :class="{ active: route.name === 'Team' }">TEAM</button>
        <button class="btn error-btn" @click="logout">LOGOUT</button>
      </template>
    </div>
  </header>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useUiStore } from '../stores/ui'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const uiStore = useUiStore()

function logout() {
  uiStore.showConfirm('Are you sure you want to log out?', 'CONFIRM LOGOUT', () => {
    authStore.logout()
    router.push('/login')
  })
}

const title = computed(() => {
  switch (route.name) {
    case 'Login': return 'CTF / LEADERBOARD'
    case 'Leaderboard': return authStore.isAdmin ? 'ROOT ACCESS // LEADERBOARD' : 'CTF / LEADERBOARD'
    case 'AdminUsers': return 'ROOT ACCESS // USERS & TEAMS'
    case 'AdminChallenges': return 'ROOT ACCESS // CHALLENGES'
    case 'AdminTraffic': return 'ROOT ACCESS // NETWORK TRAFFIC'
    case 'Challenges': return 'CTF / CHALLENGES'
    case 'ChallengeDetail': return 'CTF / CHALLENGE DETAIL'
    case 'Team': return 'CTF / TEAM'
    default: return 'CTF PLATFORM'
  }
})
</script>

<style scoped lang="scss">
.user-header {
  display: flex;
  justify-content: space-between;
  align-items: center;

  .actions {
    display: flex;
    flex-wrap: wrap;
    gap: 10px;
    justify-content: center;
    .btn {
      margin-left: 10px;

      &.active {
        background-color: var(--primary);
        color: var(--background);
      }
    }
  }

  @media (max-width: 846px) {
    flex-direction: column;
    align-items: center;
    gap: 15px;

    .actions {
      .btn {
        margin-left: 0;
      }
    }
  }
}
</style>

<template>
  <div>
    <NavBar />

    <CountdownTimer :timer="globalTimer" />

    <div class="boxy-card leaderboard-container">
      <h3>TOP TEAMS</h3>
      
      <div class="podium" v-if="podiumTeams.length >= 1">
        <div class="podium-spot silver" v-if="rankings[1] && rankings[1].score > 0">
          <div class="rank">#2</div>
          <div class="team-name">{{ rankings[1].team_name }}</div>
          <div class="score">{{ rankings[1].score }} PTS</div>
        </div>
        <div class="podium-spot gold" v-if="rankings[0] && rankings[0].score > 0">
          <div class="rank">#1</div>
          <div class="team-name">{{ rankings[0].team_name }}</div>
          <div class="score">{{ rankings[0].score }} PTS</div>
        </div>
        <div class="podium-spot bronze" v-if="rankings[2] && rankings[2].score > 0">
          <div class="rank">#3</div>
          <div class="team-name">{{ rankings[2].team_name }}</div>
          <div class="score">{{ rankings[2].score }} PTS</div>
        </div>
      </div>

      <div class="data-list" v-if="listTeams.length > 0">
        <div 
          class="data-item" 
          v-for="r in listTeams" 
          :key="r.team_id"
          :class="{ 'my-team': isMyTeam(r.team_id), 'dimmed': r.score === 0 }"
        >
          <div class="data-col rank-col">
            <span>#{{ r.rank }}</span>
          </div>
          <div class="data-col" style="flex-grow: 1">
            <span>{{ r.team_name }} <span v-if="isMyTeam(r.team_id)" class="indicator-you">(YOU)</span></span>
          </div>
          <div class="data-col score-col">
            <span class="points">{{ r.score }}</span>
          </div>
        </div>
      </div>
      
      <p v-if="rankings.length === 0">NO TEAMS ON THE LEADERBOARD YET.</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import NavBar from '../components/NavBar.vue'
import CountdownTimer from '../components/CountdownTimer.vue'
import { fetchApi } from '../api/client'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const rankings = ref([])
const error = ref('')

const globalTimer = ref(null)

const podiumTeams = computed(() => {
  return rankings.value.slice(0, 3).filter(r => r.score > 0)
})

const listTeams = computed(() => {
  const podiumIds = new Set(podiumTeams.value.map(r => r.team_id))
  return rankings.value.filter(r => !podiumIds.has(r.team_id))
})

function isMyTeam(team_id) {
  return authStore.user && authStore.user.team_id === team_id
}

async function fetchLeaderboard() {
  try {
    const data = await fetchApi('/leaderboard')
    rankings.value = data.rankings
    globalTimer.value = data.timer
  } catch (err) {
    error.value = err.message
  }
}

onMounted(() => {
  fetchLeaderboard()
  // Refresh leaderboard and timer state every 30s
  setInterval(fetchLeaderboard, 30000)
})

onUnmounted(() => {
})
</script>

<style scoped lang="scss">
.leaderboard-container {
  display: flex;
  flex-direction: column;
  gap: 20px;

  .podium {
    display: flex;
    justify-content: center;
    align-items: flex-end;
    gap: 15px;
    margin: 30px 0;
    min-height: 180px;

    @media (max-width: 846px) {
      flex-direction: column;
      align-items: center;
      min-height: auto;
    }

    .podium-spot {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      border: 1px solid var(--border);
      padding: 10px;
      width: 150px;
      text-align: center;
      position: relative;

      @media (max-width: 846px) {
        width: 100%;
        max-width: 300px;
        height: auto !important;
      }

      .rank {
        font-family: var(--font-heading);
        font-size: 2rem;
        font-weight: bold;
        margin-bottom: 6px;
      }

      .team-name {
        font-weight: bold;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        max-width: 100%;
        font-size: 0.9em;
        margin-bottom: 3px;
      }

      .score {
        color: var(--accent);
      }

      &.gold {
        height: 180px;
        border-color: var(--gold);
        box-shadow: 0 0 10px color-mix(in srgb, var(--gold) 20%, transparent);
        .rank { color: var(--gold); }
        @media (max-width: 846px) { order: 1; }
      }

      &.silver {
        height: 140px;
        border-color: var(--silver);
        .rank { color: var(--silver); font-size: 1.8rem; }
        @media (max-width: 846px) { order: 2; }
      }

      &.bronze {
        height: 110px;
        border-color: var(--bronze);
        .rank { color: var(--bronze); font-size: 1.4rem;}
        @media (max-width: 846px) { order: 3; }
      }
    }
  }

  .data-list {
    .data-item {
      &.my-team {
        border-color: var(--border) !important;
        background-color: color-mix(in srgb, var(--accent) 5%, transparent);
      }
      
      &.dimmed {
        border-color: var(--secondary);
        .rank-col span, .indicator-you, .score-col .points {
          color: var(--silver);
        }
        color: var(--silver);
      }

      .rank-col span {
        font-family: var(--font-heading);
        font-size: 1.5rem;
        color: var(--primary);
      }

      .indicator-you {
        color: var(--accent);
      }

      .score-col {
        .points {
          color: var(--accent);
          font-weight: bold;
          font-size: 1.5rem;
        }
      }
    }
  }
}
</style>

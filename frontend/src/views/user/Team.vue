<template>
  <div>
    <NavBar />

    <div v-if="team" class="boxy-card">
    	<h1>{{ team.name }}</h1>
      <div class="stats">
        <div class="stat-box">
          <label>RANK</label>
          <span class="rank-value">#{{ team.rank }}</span>
        </div>
        <div class="stat-box">
          <label>TOTAL SCORE</label>
          <span class="points">{{ team.score }}</span>
        </div>
        <div class="stat-box stat-stacked">
          <span class="status-earned">++{{ team.total_earned }}</span>
          <span class="status-deducted">--{{ team.total_deducted }}</span>
        </div>
      </div>
    </div>

    <div class="boxy-card team-section">
      <h3>MEMBERS</h3>
      <div class="data-table members-table" v-if="members.length">
        <div class="table-header">
          <div style="flex: 2">USERNAME</div>
          <div style="flex: 1">SCORE</div>
          <div style="flex: 1">ROLE</div>
          <div style="flex: 1">STATUS</div>
        </div>
        <div class="table-row" v-for="m in members" :key="m.id">
          <div style="flex: 2">
            {{ m.username }} 
            <span v-if="m.username === authStore.user.username" class="indicator-you">[YOU]</span>
          </div>
          <div style="flex: 1" class="points">{{ m.score ? m.score : 0 }} PTS</div>
          <div style="flex: 1">
            <span class="badge" :class="m.is_team_leader ? 'badge-success' : ''">{{ m.is_team_leader ? 'LEADER' : 'MEMBER' }}</span>
          </div>
          <div style="flex: 1">
            <span class="badge" :class="m.is_banned ? 'badge-error' : 'badge-success'">{{ m.is_banned ? 'BANNED' : 'ACTIVE' }}</span>
          </div>
        </div>
      </div>
    </div>

    <div class="boxy-card team-section" v-if="team && team.solved_challenges && team.solved_challenges.length">
      <h3>SOLVED CHALLENGES</h3>
      <div class="data-table">
        <div class="table-header">
          <div style="flex: 2">CHALLENGE</div>
          <div style="flex: 1">POINTS</div>
          <div style="flex: 1">SOLVE ORDER</div>
          <div style="flex: 2">TIME</div>
        </div>
        <div class="table-row" v-for="sc in team.solved_challenges" :key="sc.challenge_id">
          <div style="flex: 2; font-weight: bold;">{{ sc.challenge_title }}</div>
          <div style="flex: 1" class="status-earned">++{{ sc.points_awarded }} PTS</div>
          <div style="flex: 1">
            <span class="badge badge-success">#{{ sc.solve_order }}</span>
          </div>
          <div style="flex: 2" class="time-dim">{{ new Date(sc.timestamp).toLocaleString() }}</div>
        </div>
      </div>
    </div>

    <div class="boxy-card team-section" v-if="team && team.hint_reveals && team.hint_reveals.length">
      <h3>HINT REVEALS</h3>
      <div class="data-table">
        <div class="table-header">
          <div style="flex: 2">CHALLENGE</div>
          <div style="flex: 1">PENALTY</div>
          <div style="flex: 2">TIME</div>
        </div>
        <div class="table-row" v-for="hr in team.hint_reveals" :key="'hint_'+hr.challenge_id">
          <div style="flex: 2; font-weight: bold;">{{ hr.challenge_title }}</div>
          <div style="flex: 1" class="status-deducted">--{{ hr.penalty_deducted }} PTS</div>
          <div style="flex: 2" class="time-dim">{{ new Date(hr.timestamp).toLocaleString() }}</div>
        </div>
      </div>
    </div>

    <div class="boxy-card team-section" v-if="team && team.wrong_submissions && team.wrong_submissions.length">
      <h3>WRONG SUBMISSIONS ({{ team.wrong_attempts }})</h3>
      <div class="data-table">
        <div class="table-header">
          <div style="flex: 2">CHALLENGE</div>
          <div style="flex: 1">PENALTY</div>
          <div style="flex: 2">TIME</div>
        </div>
        <div class="table-row" v-for="ws in team.wrong_submissions" :key="'wrong_'+ws.challenge_id+'_'+ws.timestamp">
          <div style="flex: 2; font-weight: bold;">{{ ws.challenge_title }}</div>
          <div style="flex: 1" class="status-deducted">-{{ ws.penalty_deducted }} PTS</div>
          <div style="flex: 2" class="time-dim">{{ new Date(ws.timestamp).toLocaleString() }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import NavBar from '../../components/NavBar.vue'
import { fetchApi } from '../../api/client'
import { useAuthStore } from '../../stores/auth'
import { useUiStore } from '../../stores/ui'

const authStore = useAuthStore()
const uiStore = useUiStore()
const team = ref(null)
const members = ref([])

async function loadTeamData() {
  try {
    const data = await fetchApi('/team/me')
    team.value = data.team
    members.value = (data.team.members || []).sort((a,b) => b.is_team_leader - a.is_team_leader)
  } catch(e) {
    uiStore.showAlert(e.message)
  }
}

onMounted(() => {
  loadTeamData()
})
</script>

<style scoped lang="scss">
.stats {
  display: flex;
  gap: 30px;
  margin-top: 15px;

  .stat-box {
    display: flex;
    flex-direction: column;

    label {
      color: var(--secondary);
      font-size: 0.8rem;
      margin-bottom: 5px;
    }

    span {
      font-family: var(--font-heading);
      font-size: 2.5rem;
      font-weight: bold;

      &.points {
        color: var(--accent);
      }

      &.status-earned {
        color: var(--accent);
      }

      &.status-deducted {
        color: var(--error);
      }
    }

    &.stat-stacked {
      flex-direction: column;
      justify-content: flex-end;
      gap: 2px;
      padding-bottom: 12px;

      span {
        font-family: inherit;
        font-size: 0.65rem;
        font-weight: normal;
      }
    }
  }
}

.team-section {
  margin-top: 15px;

  h3 {
    font-size: 1.5rem;
    border-bottom: 1px solid var(--border);
    padding-bottom: 10px;
    margin-bottom: 15px;
  }

  .members-table {
    .indicator-you {
      color: var(--accent);
    }
    .points {
      color: var(--accent);
    }
  }

  .status-earned {
    color: var(--accent);
  }

  .status-deducted {
    color: var(--error);
  }

  .time-dim {
    color: var(--secondary);
  }
}
</style>

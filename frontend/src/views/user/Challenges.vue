<template>
  <div>
    <NavBar />

    <div class="challenges-grid">
      <div v-if="challenges.length === 0" class="boxy-card">
        <p>[DEBUG] NO ACTIVE CHALLENGES FOUND.</p>
      </div>

      <div 
        v-for="c in challenges" 
        :key="c.id" 
        class="boxy-card challenge-card clickable-card" 
        :class="{ 
          solved: c.is_solved,
          locked: !c.is_solved && (!c.is_open || c.is_locked_by_parent)
        }"
        @click="goToChallenge(c)"
      >
        <div class="challenge-header">
          <h3>{{ c.title }}</h3>
          <span class="points" v-if="c.is_solved">++{{ c.points_earned }} PTS</span>
          <span class="points" v-else-if="c.is_open && !c.is_locked_by_parent">{{ c.points }} PTS</span>
        </div>
        
        <div class="challenge-details" v-if="c.is_solved || (c.is_open && !c.is_locked_by_parent)">
          <div class="detail-item time-window">
            <span class="detail-label">[CLOSE]</span>
            <span class="detail-val">{{ new Date(c.close_time).toLocaleString() }}</span>
          </div>
          
          <div class="detail-item attempts">
            <span class="detail-label">[ATTEMPTS]</span>
            <span class="detail-val">{{ c.attempts }}</span>
          </div>
          
          <div class="detail-item status">
            <span v-if="c.is_solved" class="status-solved">[INFO] SOLVED</span>
            <span v-else class="status-unsolved">[WARN] UNSOLVED</span>
          </div>
        </div>

        <div class="challenge-details" v-else>
          <div class="detail-item status" style="text-align: left; margin-top: 5px;">
            <span class="status-error" style="font-weight: bold;">[ERR] CLOSED</span>
          </div>
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
import { useRouter } from 'vue-router'

const authStore = useAuthStore()
const uiStore = useUiStore()
const router = useRouter()
const challenges = ref([])

function goToChallenge(c) {
  // If we want, we can block navigation, but the requirements say 
  // they show up in error color and basic info. Clicking might still show the detail page with the same minimal info.
  router.push(`/challenges/${c.id}`)
}

async function loadChallenges() {
  try {
    const data = await fetchApi('/challenges')
    challenges.value = data.challenges
  } catch(e) {
    uiStore.showAlert(e.message)
  }
}

onMounted(() => {
  loadChallenges()
})
</script>

<style scoped lang="scss">
.challenges-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(450px, 1fr));
  gap: 20px;

  .challenge-card {
    display: flex;
    flex-direction: column;

    &.clickable-card {
      cursor: pointer;
      transition: border-color 0.2s;

      &:hover {
        border-color: var(--primary);
      }
    }

    &.solved {
      border-color: var(--border);
    }
    
    &.locked {
      border-color: var(--error);
      color: var(--error);
      
      .challenge-header {
        border-bottom-color: var(--error);
        h3 {
          color: var(--error);
        }
      }
    }

    .challenge-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--border);
      padding-bottom: 10px;
      margin-bottom: 10px;

      h3 {
        margin: 0;
      }

      .points {
        color: var(--accent);
        font-weight: bold;
      }
    }

    .challenge-details {
      display: flex;
      flex-direction: column;
      gap: 10px;

      .detail-item {
        color: var(--secondary);
        font-size: 0.9em;

        .detail-label {
          margin-right: 5px;
        }

        .status-solved {
          color: var(--accent);
          font-weight: bold;
        }

        .status-unsolved {
          color: var(--warning);
          font-weight: bold;
        }
        
        .status-error {
          color: var(--error);
        }
      }
    }
  }

  @media (max-width: 768px) {
    grid-template-columns: 1fr;
    
    .challenge-card {
      .challenge-header {
        flex-direction: column;
        align-items: flex-start;
        gap: 8px;
        
        .points {
          font-size: 0.9em;
          padding: 2px 8px;
          border-radius: 4px;
        }
      }

      .challenge-details {
        flex-direction: row;
        flex-wrap: wrap;
        justify-content: space-between;
        align-items: center;
        border-radius: 6px;

        .detail-item {
          // flex: 1 1 45%;
          margin-bottom: 5px;

          &.status {
            flex: 1 1 100%;
            text-align: right;
            margin-bottom: 0;
            padding-top: 8px;
            margin-top: 4px;
          }

          .detail-label {
            font-size: 0.8em;
            opacity: 0.7;
            margin-bottom: 2px;
          }
        }
      }
    }
  }
}
</style>


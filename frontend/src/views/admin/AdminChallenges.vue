<template>
  <div class="admin-wrapper">
    <NavBar />

    <div class="tab-content">
      <div class="controls boxy-card">
        <button class="btn" @click="showAddChallenge = true">CREATE CHALLENGE</button>
        <button class="btn" @click="showTimerModal = true">SET DOOMSDAY TIMER</button>
      </div>

      <div class="challenges-grid" v-if="challenges.length">
        <div class="boxy-card challenge-card" v-for="c in challenges" :key="c.id">
          <div class="challenge-header">
            <h3>{{ c.title }}</h3>
            <span class="points">{{ c.points }} PTS</span>
          </div>
          <div class="challenge-meta">
            <label>STATUS OVERRIDE:</label>
            <span :class="c.status_override !== 'AUTO' ? 'status-accent' : ''">{{ c.status_override }}</span>
          </div>
          <div class="challenge-meta">
            <label>ACTUAL STATE:</label>
            <span :class="c.is_open ? 'status-success' : 'status-error'">{{ c.is_open ? 'OPEN' : 'CLOSED' }}</span>
          </div>
          <div class="challenge-meta">
            <label>VISIBILITY:</label>
            <span :class="c.is_hidden ? 'status-error' : 'status-success'">{{ c.is_hidden ? 'HIDDEN' : 'VISIBLE' }}</span>
          </div>
          <div class="challenge-meta" v-if="c.parent_id">
            <label>PARENT ID:</label>
            <span>{{ c.parent_id }}</span>
          </div>
          <div class="challenge-actions actions-margin">
            <button class="btn" @click="openEditChallenge(c)">EDIT</button>
            <button class="btn" @click="viewHistory(c.id)">HISTORY</button>
            <button class="btn error-btn" @click="deleteChallenge(c.id)">DELETE</button>
          </div>
        </div>
      </div>
      <div v-else class="boxy-card">
        <p>NO CHALLENGES FOUND.</p>
      </div>
    </div>

    <!-- Timer Modal -->
    <div v-if="showTimerModal" class="admin-modal-overlay" @click.self="showTimerModal = false">
      <div class="boxy-card modal-content">
        <h3>DOOMSDAY TIMER CONFIGURATION</h3>
        <form @submit.prevent="setTimer">
          <label>NOTE</label>
          <input v-model="timerNote" placeholder="e.g. INVASION BEGINS IN" />
          <label>EXPIRATION TIME (Local)</label>
          <input type="datetime-local" v-model="timerExpiresAt" required />
          <div class="modal-actions">
            <button type="submit" class="btn">SET TIMER</button>
            <button type="button" class="btn error-btn" @click="clearTimer">CLEAR TIMER</button>
            <button type="button" class="btn" @click="showTimerModal = false">CANCEL</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Add Challenge Modal -->
    <div v-if="showAddChallenge" class="admin-modal-overlay" @click.self="showAddChallenge = false">
      <div class="boxy-card modal-content">
        <h3>CREATE CHALLENGE</h3>
        <form @submit.prevent="createChallenge">
          <input v-model="newChallenge.title" placeholder="TITLE" required />
          <textarea v-model="newChallenge.description" placeholder="DESCRIPTION" required></textarea>
          <input v-model="newChallenge.flag" placeholder="FLAG (e.g. flag{...})" required />
          <label>OPEN TIME (Local)</label>
          <input type="datetime-local" v-model="newChallenge.open_time" required />
          <label>CLOSE TIME (Local)</label>
          <input type="datetime-local" v-model="newChallenge.close_time" required />
          <label>BASE POINTS (Max)</label>
          <input type="number" v-model="newChallenge.max_points" required />
          <label>MIN POINTS</label>
          <input type="number" v-model="newChallenge.min_points" required />
          <label>DECAY STEP</label>
          <input type="number" v-model="newChallenge.step_value" required />
          <label>WRONG SUBMISSION PENALTY</label>
          <input type="number" v-model="newChallenge.penalty_value" required />
          
          <label>STATUS OVERRIDE</label>
          <select v-model="newChallenge.status_override">
            <option value="AUTO">AUTO (Use Timings)</option>
            <option value="OPEN">FORCE OPEN</option>
            <option value="CLOSED">FORCE CLOSED</option>
          </select>
          
          <label>PARENT CHALLENGE (Chain)</label>
          <select v-model="newChallenge.parent_id">
            <option :value="null">None (Independent)</option>
            <option v-for="c in challenges" :key="c.id" :value="c.id">{{ c.title }}</option>
          </select>

          <label style="display:flex; align-items:center; gap:10px; margin-top:5px; cursor:pointer;">
            <input type="checkbox" v-model="newChallenge.is_hidden" />
            HIDDEN (Secret Challenge)
          </label>
          
          <label>HINT TEXT (Optional)</label>
          <textarea v-model="newChallenge.hint_text" placeholder="Enter hint if any"></textarea>
          <label>HINT PENALTY</label>
          <input type="number" v-model="newChallenge.hint_penalty" />
          
          <label>ATTACHMENT (Optional)</label>
          <input type="file" ref="newChallengeFile" />

          <div class="modal-actions">
            <button type="submit" class="btn">CREATE</button>
            <button type="button" class="btn" @click="showAddChallenge = false">CANCEL</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Edit Challenge Modal -->
    <div v-if="showEditChallenge" class="admin-modal-overlay" @click.self="showEditChallenge = false">
      <div class="boxy-card modal-content">
        <h3>EDIT CHALLENGE</h3>
        <form @submit.prevent="updateChallenge">
          <label>TITLE</label>
          <input v-model="editingChallenge.title" required />
          <label>DESCRIPTION</label>
          <textarea v-model="editingChallenge.description" required></textarea>
          <label>NEW FLAG (Leave blank to keep unchanged)</label>
          <input v-model="editingChallenge.flag" />
          <label>BASE POINTS (Max)</label>
          <input type="number" v-model="editingChallenge.max_points" required />
          <label>MIN POINTS</label>
          <input type="number" v-model="editingChallenge.min_points" required />
          <label>DECAY STEP</label>
          <input type="number" v-model="editingChallenge.step_value" required />
          <label>WRONG SUBMISSION PENALTY</label>
          <input type="number" v-model="editingChallenge.penalty_value" required />
          <label>OPEN TIME (Local)</label>
          <input type="datetime-local" v-model="editingChallenge.open_time" required />
          <label>CLOSE TIME (Local)</label>
          <input type="datetime-local" v-model="editingChallenge.close_time" required />

          <label>STATUS OVERRIDE</label>
          <select v-model="editingChallenge.status_override">
            <option value="AUTO">AUTO (Use Timings)</option>
            <option value="OPEN">FORCE OPEN</option>
            <option value="CLOSED">FORCE CLOSED</option>
          </select>

          <label>PARENT CHALLENGE (Chain)</label>
          <select v-model="editingChallenge.parent_id">
            <option :value="null">None (Independent)</option>
            <option v-for="c in challenges" :key="c.id" :value="c.id" :disabled="c.id === editingChallenge.id">{{ c.title }}</option>
          </select>

          <label style="display:flex; align-items:center; gap:10px; margin-top:5px; cursor:pointer;">
            <input type="checkbox" v-model="editingChallenge.is_hidden" />
            HIDDEN (Secret Challenge)
          </label>
          
          <label>HINT TEXT (Optional)</label>
          <textarea v-model="editingChallenge.hint_text"></textarea>
          <label>HINT PENALTY</label>
          <input type="number" v-model="editingChallenge.hint_penalty" />
          
          <label>ATTACHMENT (Optional)</label>
          <input type="file" ref="editChallengeFile" />
          
          <div class="modal-actions">
            <button type="submit" class="btn">SAVE</button>
            <button type="button" class="btn" @click="showEditChallenge = false">CANCEL</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Challenge History Modal -->
    <div v-if="showHistoryModal" class="admin-modal-overlay" @click.self="showHistoryModal = false">
      <div class="boxy-card modal-content" style="max-width: 800px; width: 90%;">
        <h3>SUBMISSION HISTORY</h3>
        <div class="data-list" v-if="submissions.length" style="max-height: 400px; overflow-y: auto;">
          <div class="data-item" v-for="s in submissions" :key="s.timestamp">
            <div class="data-col" style="flex-grow: 1">
              <label>TEAM</label>
              <span>{{ s.team_name }}</span>
            </div>
            <div class="data-col" style="flex-grow: 1">
              <label>USER EMAIL</label>
              <span>{{ s.user_email }}</span>
            </div>
            <div class="data-col">
              <label>RESULT</label>
              <span :class="s.is_correct ? 'status-success' : 'status-error'">{{ s.is_correct ? 'CORRECT' : 'WRONG' }}</span>
            </div>
            <div class="data-col">
              <label>TIME (Local)</label>
              <span>{{ new Date(s.timestamp + 'Z').toLocaleString() }}</span>
            </div>
          </div>
        </div>
        <p v-else>NO SUBMISSIONS YET.</p>
        
        <div class="modal-actions actions-margin">
          <button type="button" class="btn block-btn" @click="showHistoryModal = false">CLOSE</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import NavBar from '../../components/NavBar.vue'
import { fetchApi } from '../../api/client'
import { useUiStore } from '../../stores/ui'

const uiStore = useUiStore()

const challenges = ref([])
const submissions = ref([])

const showAddChallenge = ref(false)
const showEditChallenge = ref(false)
const showHistoryModal = ref(false)
const showTimerModal = ref(false)

const newChallenge = ref({ title: '', description: '', flag: '', open_time: '', close_time: '', status_override: 'AUTO', max_points: 1000, min_points: 300, step_value: 100, penalty_value: 10, hint_text: '', hint_penalty: 0, parent_id: null, is_hidden: false })
const editingChallenge = ref(null)

const timerNote = ref('')
const timerExpiresAt = ref('')
const newChallengeFile = ref(null)
const editChallengeFile = ref(null)

function formatToLocal(isoString) {
  if (!isoString) return ''
  const d = new Date(isoString + 'Z')
  return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16)
}

function getBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.readAsDataURL(file)
    reader.onload = () => resolve(reader.result.split(',')[1])
    reader.onerror = error => reject(error)
  })
}

async function loadChallenges() {
  try {
    const data = await fetchApi('/admin/challenges')
    challenges.value = data.challenges
  } catch(e) {
    uiStore.showAlert(e.message)
  }
}

async function setTimer() {
  try {
    const expires = new Date(timerExpiresAt.value).toISOString()
    await fetchApi('/admin/timer', { method: 'POST', body: JSON.stringify({ note: timerNote.value, expires_at: expires }) })
    showTimerModal.value = false
  } catch(e) { uiStore.showAlert(e.message) }
}

async function clearTimer() {
  try {
    await fetchApi('/admin/timer', { method: 'DELETE' })
    timerNote.value = ''
    timerExpiresAt.value = ''
    showTimerModal.value = false
  } catch(e) { uiStore.showAlert(e.message) }
}

async function createChallenge() {
  try {
    const payload = { ...newChallenge.value }
    payload.open_time = new Date(payload.open_time).toISOString()
    payload.close_time = new Date(payload.close_time).toISOString()

    const res = await fetchApi('/admin/challenges', {
      method: 'POST',
      body: JSON.stringify(payload)
    })

    if (newChallengeFile.value && newChallengeFile.value.files.length > 0) {
       const file = newChallengeFile.value.files[0]
       const b64 = await getBase64(file)
       await fetchApi(`/admin/challenges/${res.challenge.id}/attachment`, {
         method: 'POST',
         body: JSON.stringify({ filename: file.name, data: b64 })
       })
    }

    showAddChallenge.value = false
    newChallenge.value = { title: '', description: '', flag: '', open_time: '', close_time: '', status_override: 'AUTO', max_points: 1000, min_points: 300, step_value: 100, penalty_value: 10, hint_text: '', hint_penalty: 0, parent_id: null, is_hidden: false }
    loadChallenges()
  } catch(e) {
    uiStore.showAlert(e.message)
  }
}

function openEditChallenge(c) {
  editingChallenge.value = { 
    ...c,
    flag: '', 
    open_time: formatToLocal(c.open_time),
    close_time: formatToLocal(c.close_time)
  }
  if (!editingChallenge.value.status_override) editingChallenge.value.status_override = 'AUTO'
  showEditChallenge.value = true
}

async function updateChallenge() {
  try {
    const payload = { ...editingChallenge.value }
    payload.open_time = new Date(payload.open_time).toISOString()
    payload.close_time = new Date(payload.close_time).toISOString()

    await fetchApi(`/admin/challenges/${payload.id}`, {
      method: 'PUT',
      body: JSON.stringify(payload)
    })

    if (editChallengeFile.value && editChallengeFile.value.files.length > 0) {
       const file = editChallengeFile.value.files[0]
       const b64 = await getBase64(file)
       await fetchApi(`/admin/challenges/${payload.id}/attachment`, {
         method: 'POST',
         body: JSON.stringify({ filename: file.name, data: b64 })
       })
    }

    showEditChallenge.value = false
    loadChallenges()
  } catch(e) {
    uiStore.showAlert(e.message)
  }
}

async function viewHistory(challengeId) {
  try {
    const data = await fetchApi(`/admin/challenges/${challengeId}/submissions`)
    submissions.value = data.submissions
    showHistoryModal.value = true
  } catch(e) {
    uiStore.showAlert(e.message)
  }
}

async function deleteChallenge(challengeId) {
  uiStore.showConfirm("Are you sure you want to permanently delete this challenge and all its submissions?", "DELETE CHALLENGE", async () => {
    try {
      await fetchApi(`/admin/challenges/${challengeId}`, { method: 'DELETE' })
      loadChallenges()
    } catch(e) {
      uiStore.showAlert(e.message)
    }
  })
}

onMounted(() => {
  loadChallenges()
})
</script>

<style scoped lang="scss">
.admin-wrapper {
  .controls {
    display: flex;
    gap: 15px;
  }

  .challenges-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
    gap: 20px;
    margin-top: 20px;

    @media (max-width: 768px) {
      grid-template-columns: 1fr;
    }

    .challenge-card {
      display: flex;
      flex-direction: column;

      .challenge-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        border-bottom: 1px solid var(--border);
        padding-bottom: 10px;
        margin-bottom: 10px;

        .points {
          color: var(--accent);
          font-weight: bold;
        }
      }

      .challenge-meta {
        display: flex;
        justify-content: space-between;
        margin-bottom: 10px;

        .status-accent {
          color: var(--accent);
        }

        .status-error {
          color: var(--error);
        }

        .status-success {
          color: var(--accent);
        }
      }

      .challenge-actions {
        display: flex;
        gap: 10px;
        flex-wrap: wrap;

        .btn {
          flex: 1;
        }
      }
    }
  }

  .admin-modal-overlay {
    position: fixed;
    top: 0; left: 0; right: 0; bottom: 0;
    background: var(--background);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 100;

    .modal-content {
      width: 90%;
      max-width: 500px;
      max-height: 90vh;
      overflow-y: auto;

      form {
        display: flex;
        flex-direction: column;
        gap: 10px;
        margin-top: 20px;

        label {
          font-size: 0.8rem;
          color: var(--primary);
          margin-bottom: -5px;
        }

        .modal-actions {
          display: flex;
          gap: 10px;
          margin-top: 15px;

          .btn {
            flex: 1;

            &.block-btn {
              width: 100%;
            }
          }
        }
      }

      .data-list {
        display: flex;
        flex-direction: column;
        gap: 10px;

        .data-item {
          display: flex;
          flex-wrap: wrap;
          gap: 15px;
          padding: 10px;
          background: var(--background);
          border: 1px solid var(--border);

          .data-col {
            display: flex;
            flex-direction: column;

            label {
              font-size: 0.7em;
              color: var(--secondary);
            }

            .status-error {
              color: var(--error);
            }

            .status-success {
              color: var(--accent);
            }
          }
        }
      }
    }
  }

  .actions-margin {
    margin-top: 15px;
  }
}
</style>


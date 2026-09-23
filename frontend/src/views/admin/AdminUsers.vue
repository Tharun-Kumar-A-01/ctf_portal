<template>
  <div class="admin-wrapper">
    <NavBar />

    <div class="tab-content">
      <div class="controls boxy-card">
        <button class="btn" @click="showAddUser = true">ADD USER</button>
        <button class="btn" @click="showImportCsv = true">IMPORT CSV</button>
      </div>
      
      <div v-if="sortedTeams.length">
        <div class="boxy-card team-card" v-for="t in sortedTeams" :key="t.id">
          <div class="team-header">
            <h3 :class="{'team-banned': t.is_banned}">{{ t.name }} <span class="id-dim">[ID: {{ t.id }}]</span></h3>
            <div class="team-meta">
              <span class="points">{{ t.score }} PTS</span>
              <button class="btn error-btn" @click="toggleTeamBan(t)">
                {{ t.is_banned ? 'UNBAN TEAM' : 'BAN TEAM' }}
              </button>
              <button class="btn error-btn" @click="deleteTeam(t)">
                DELETE TEAM
              </button>
            </div>
          </div>
          <div class="team-status" v-if="t.is_banned">
            <span class="status-banned">[ERROR] BANNED</span>
          </div>

          <div class="data-table actions-margin" v-if="getUsersByTeam(t.id).length > 0">
            <div class="table-header">
              <div style="flex: 2">USERNAME</div>
              <div style="flex: 3">EMAIL</div>
              <div style="flex: 1">ROLE</div>
              <div style="flex: 1">STATUS</div>
              <div style="flex: 1.5"></div>
            </div>
            <div class="table-row" v-for="u in getUsersByTeam(t.id)" :key="u.id">
              <div style="flex: 2">{{ u.username }}</div>
              <div style="flex: 3" class="id-dim">{{ u.email }}</div>
              <div style="flex: 1">
                <span class="badge" :class="u.is_team_leader ? 'badge-success' : ''">{{ u.is_team_leader ? 'LEADER' : 'MEMBER' }}</span>
              </div>
              <div style="flex: 1">
                <span class="badge" :class="u.is_banned ? 'badge-error' : 'badge-success'">{{ u.is_banned ? 'BANNED' : 'ACTIVE' }}</span>
              </div>
              <div style="flex: 1.5; display: flex; justify-content: flex-end; gap: 10px;">
                <button class="btn" @click="openEditUser(u)">EDIT</button>
                <button class="btn error-btn" @click="deleteUser(u.id)">DELETE</button>
              </div>
            </div>
          </div>
        </div>
      </div>
      <div v-else class="boxy-card">
        <p>NO TEAMS FOUND.</p>
      </div>
    </div>

    <!-- Add User Modal -->
    <div v-if="showAddUser" class="admin-modal-overlay" @click.self="showAddUser = false">
      <div class="boxy-card modal-content">
        <h3>CREATE USER</h3>
        <form @submit.prevent="createUser">
          <input v-model="newUser.username" placeholder="USERNAME" required />
          <input v-model="newUser.email" type="email" placeholder="EMAIL" required />
          <input v-model="newUser.password" type="password" placeholder="PASSWORD" required />
          <input v-model="newUser.team_name" placeholder="TEAM NAME" required />
          
          <div class="modal-actions">
            <button type="submit" class="btn">CREATE</button>
            <button type="button" class="btn" @click="showAddUser = false">CANCEL</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Edit User Modal -->
    <div v-if="showEditUser" class="admin-modal-overlay" @click.self="showEditUser = false">
      <div class="boxy-card modal-content">
        <h3>EDIT USER</h3>
        <form @submit.prevent="updateUser">
          <label>USERNAME</label>
          <input v-model="editingUser.username" required />
          <label>EMAIL</label>
          <input v-model="editingUser.email" type="email" required />
          <label>PASSWORD</label>
          <input v-model="editingUser.password" type="password" placeholder="Leave blank for unchanged" />
          <label>
            <input type="checkbox" v-model="editingUser.is_team_leader" /> TEAM LEADER
          </label>
          <label>
            <input type="checkbox" v-model="editingUser.is_banned" /> BANNED
          </label>
          
          <div class="modal-actions">
            <button type="submit" class="btn">SAVE</button>
            <button type="button" class="btn" @click="showEditUser = false">CANCEL</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Import CSV Modal -->
    <div v-if="showImportCsv" class="admin-modal-overlay" @click.self="showImportCsv = false">
      <div class="boxy-card modal-content">
        <h3>IMPORT CSV</h3>
        <p>Format: username,email,password,team_name,team_leader_name</p>
        <form @submit.prevent="importCsv">
          <input type="file" ref="csvFileInput" accept=".csv" required />
          
          <div class="modal-actions">
            <button type="submit" class="btn" :disabled="importing">UPLOAD</button>
            <button type="button" class="btn" @click="showImportCsv = false">CANCEL</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import NavBar from '../../components/NavBar.vue'
import { fetchApi } from '../../api/client'
import { useUiStore } from '../../stores/ui'

const uiStore = useUiStore()

const users = ref([])
const teams = ref([])

const showAddUser = ref(false)
const showEditUser = ref(false)
const showImportCsv = ref(false)
const importing = ref(false)

const newUser = ref({ username: '', email: '', password: '', team_name: '' })
const editingUser = ref(null)
const csvFileInput = ref(null)

const sortedTeams = computed(() => [...teams.value].sort((a,b) => b.score - a.score))

function getUsersByTeam(teamId) {
  return users.value.filter(u => u.team_id === teamId).sort((a,b) => b.is_team_leader - a.is_team_leader)
}

async function loadUsers() {
  try {
    const data = await fetchApi('/admin/users')
    users.value = data.users
    teams.value = data.teams
  } catch(e) {
    uiStore.showAlert(e.message)
  }
}

async function createUser() {
  try {
    await fetchApi('/admin/users', {
      method: 'POST',
      body: JSON.stringify(newUser.value)
    })
    showAddUser.value = false
    newUser.value = { username: '', email: '', password: '', team_name: '' }
    loadUsers()
  } catch(e) {
    uiStore.showAlert(e.message)
  }
}

function openEditUser(u) {
  editingUser.value = { ...u }
  showEditUser.value = true
}

async function updateUser() {
  try {
    await fetchApi(`/admin/users/${editingUser.value.id}`, {
      method: 'PUT',
      body: JSON.stringify(editingUser.value)
    })
    showEditUser.value = false
    loadUsers()
  } catch(e) {
    uiStore.showAlert(e.message)
  }
}

async function deleteUser(userId) {
  uiStore.showConfirm("Are you sure you want to permanently delete this user?", "DELETE USER", async () => {
    try {
      await fetchApi(`/admin/users/${userId}`, { method: 'DELETE' })
      loadUsers()
    } catch(e) {
      uiStore.showAlert(e.message)
    }
  })
}

async function toggleTeamBan(t) {
  uiStore.showConfirm(`Are you sure you want to ${t.is_banned ? 'unban' : 'ban'} the entire team?`, "TEAM STATUS", async () => {
    try {
      await fetchApi(`/admin/teams/${t.id}`, {
        method: 'PUT',
        body: JSON.stringify({ is_banned: !t.is_banned })
      })
      loadUsers()
    } catch(e) {
      uiStore.showAlert(e.message)
    }
  })
}

async function deleteTeam(t) {
  uiStore.showConfirm(`Are you sure you want to completely delete the team "${t.name}"? This action cannot be undone.`, "DELETE TEAM", async () => {
    try {
      await fetchApi(`/admin/teams/${t.id}`, {
        method: 'DELETE'
      })
      loadUsers()
    } catch(e) {
      uiStore.showAlert(e.message)
    }
  })
}

async function importCsv() {
  const file = csvFileInput.value?.files[0]
  if (!file) return
  
  importing.value = true
  try {
    const text = await file.text()
    await fetchApi('/admin/users/import-csv', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ file_content: text, filename: file.name })
    })
    showImportCsv.value = false
    loadUsers()
  } catch(e) {
    uiStore.showAlert(e.message)
  } finally {
    importing.value = false
  }
}

onMounted(() => {
  loadUsers()
})
</script>

<style scoped lang="scss">
.admin-wrapper {
  .controls {
    display: flex;
    gap: 15px;
  }

  .team-card {
    margin-top: 20px;
    border-color: var(--border);

    .team-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--border);
      padding-bottom: 10px;

      h3 {
        &.team-banned {
          color: var(--error);
        }
      }

      .id-dim {
        color: var(--secondary);
        font-size: 0.8em;
      }

      .team-meta {
        display: flex;
        align-items: center;
        gap: 15px;

        .points {
          color: var(--accent);
          font-weight: bold;
        }
      }

      @media (max-width: 768px) {
        flex-direction: column;
        align-items: flex-start;
        gap: 15px;

        .team-meta {
          width: 100%;
          justify-content: space-between;
        }
      }
    }

    .team-status {
      .status-banned {
        color: var(--error);
      }
    }

    .actions-margin {
      margin-top: 15px;

      .id-dim {
        color: var(--secondary);
        font-size: 0.8em;
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
          }
        }
      }
    }
  }
}
</style>

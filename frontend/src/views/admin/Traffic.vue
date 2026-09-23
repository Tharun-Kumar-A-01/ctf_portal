<template>
  <div class="admin-wrapper">
    <NavBar />
    
    <div class="tab-content">
      <h2>Network Traffic Monitor</h2>
      <div class="metrics-summary">
        <div class="metric-card">
          <label>TOTAL LOGGED REQUESTS</label>
          <span class="value">{{ totalRequests }}</span>
        </div>
        <div class="metric-card">
          <label>RATE LIMITED (DOS BLOCKED)</label>
          <span class="value status-error">{{ rateLimitedRequests }}</span>
        </div>
        <div class="metric-card">
          <label>AUTHENTICATED RATIO</label>
          <span class="value">{{ authRatio }}%</span>
        </div>
      </div>
      
      <div class="charts-container">
        <div class="chart-box">
        <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px;">
          <h3 style="margin: 0;">Traffic Volume (Last {{ timeWindow }} mins)</h3>
          <select v-model="timeWindow" class="input" style="width: auto; padding: 5px;">
            <option :value="10">Last 10 Mins</option>
            <option :value="30">Last 30 Mins</option>
            <option :value="60">Last 60 Mins</option>
          </select>
        </div>
          <div style="height: 300px">
            <Line v-if="loaded" :data="volumeChartData" :options="chartOptions" />
          </div>
        </div>
      </div>

      <div class="activity-history boxy-card" style="margin-bottom: 20px;">
        <h3>Detailed Team Activity History</h3>
        <div class="table-container" style="max-height: 300px">
          <table class="traffic-table">
            <thead>
              <tr>
                <th>TIME</th>
                <th>TEAM</th>
                <th>USER</th>
                <th>ACTION</th>
                <th>DESCRIPTION</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="activities.length === 0">
                <td colspan="5" style="text-align: center; color: var(--secondary)">No activity yet.</td>
              </tr>
              <tr v-for="act in activities" :key="act.id">
                <td style="white-space: nowrap">{{ new Date(act.timestamp + 'Z').toLocaleString() }}</td>
                <td>{{ act.team_name }}</td>
                <td>{{ act.username }}</td>
                <td><span class="badge" :class="{'badge-error': act.action_type==='auto_ban', 'badge-success': act.action_type==='submission', 'badge-accent': act.action_type==='hint_reveal'}">{{ act.action_type.toUpperCase() }}</span></td>
                <td>{{ act.description }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="banned-ips boxy-card">
        <h3>Banned IPs (Firewall)</h3>
        <div style="display: flex; gap: 10px; margin-bottom: 15px;">
          <input v-model="newBanIp" type="text" class="input" placeholder="Enter IP address to ban" style="flex: 1;" />
          <button class="btn" @click="banIp">BAN IP</button>
        </div>
        <div class="table-container" style="max-height: 200px">
          <table class="traffic-table">
            <thead>
              <tr>
                <th>BANNED IP</th>
                <th style="width: 100px;">ACTION</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="bannedIps.length === 0">
                <td colspan="2" style="text-align: center; color: var(--secondary)">No IPs currently banned.</td>
              </tr>
              <tr v-for="ip in bannedIps" :key="ip">
                <td style="color: var(--error)">{{ ip }}</td>
                <td><button class="btn" style="padding: 4px 8px; font-size: 0.8em" @click="unbanIp(ip)">UNBAN</button></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="wireshark-log boxy-card">
        <h3>Live Traffic Stream</h3>
        <div class="table-container">
          <table class="traffic-table">
            <thead>
              <tr>
                <th>TIME</th>
                <th>IP SOURCE</th>
                <th>METHOD</th>
                <th>ENDPOINT</th>
                <th>STATUS</th>
                <th>AUTH</th>
                <th>COUNT</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(group, idx) in groupedLogs" :key="idx" :class="{'rate-limited': group.is_rate_limited}">
                <td>{{ new Date(group.timestamp * 1000).toLocaleTimeString() }}</td>
                <td>{{ group.ip || 'Unknown' }}</td>
                <td :class="group.method.toLowerCase() + '-method'">{{ group.method }}</td>
                <td>{{ group.path }}</td>
                <td>{{ group.status_code }}</td>
                <td :class="group.is_authenticated ? 'authenticated' : 'not-authenticated'">{{ group.is_authenticated ? 'YES' : 'NO' }}</td>
                <td>{{ group.count > 1 ? group.count : '' }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed, onUnmounted } from 'vue'
import { fetchApi, decryptPayload, encryptPayload, rsaEncryptUserId } from '../../api/client'
import NavBar from '../../components/NavBar.vue'
import { Line } from 'vue-chartjs'
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler } from 'chart.js'
import { useUiStore } from '../../stores/ui'

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend, Filler)

const uiStore = useUiStore()

const logs = ref([])
const loaded = ref(false)
const bannedIps = ref([])
const activities = ref([])
const newBanIp = ref('')
const currentTime = ref(Math.floor(Date.now() / 1000))

async function loadActivities() {
  try {
    const data = await fetchApi('/admin/activity')
    activities.value = data.activities
  } catch(e) {
    console.error('Failed to load activities:', e)
  }
}

const timeWindow = ref(60)

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  elements: {
    point: {
      radius: 0,
      hoverRadius: 5
    }
  },
  plugins: {
    legend: {
      labels: { color: '#a0a0a0' }
    }
  },
  scales: {
    x: {
      ticks: { 
        color: '#888',
        maxTicksLimit: Math.floor(timeWindow.value / 2),
        maxRotation: 45,
        minRotation: 45
      },
      grid: { color: '#2a2a2a' }
    },
    y: {
      ticks: { color: '#888' },
      grid: { color: '#2a2a2a' }
    }
  }
}))

const totalRequests = computed(() => logs.value.reduce((sum, l) => sum + (l.count || 1), 0))
const rateLimitedRequests = computed(() => logs.value.filter(l => l.is_rate_limited).reduce((sum, l) => sum + (l.count || 1), 0))
const authRatio = computed(() => {
  const total = totalRequests.value
  if (!total) return 0
  const auth = logs.value.filter(l => l.is_authenticated).reduce((sum, l) => sum + (l.count || 1), 0)
  return Math.round((auth / total) * 100)
})

const groupedLogs = computed(() => {
  const sorted = [...logs.value].sort((a, b) => b.timestamp - a.timestamp)
  const groups = []
  const seen = new Map()

  for (const log of sorted) {
    const key = `${log.ip}|${log.method}|${log.path}|${log.status_code}|${log.is_authenticated}`
    if (seen.has(key)) {
      seen.get(key).count += (log.count || 1)
    } else {
      const entry = { ...log, count: log.count || 1 }
      seen.set(key, entry)
      groups.push(entry)
    }
  }

  return groups.slice(0, 100)
})

const volumeChartData = computed(() => {
  const now = currentTime.value
  const buckets = {}
  const windowMins = timeWindow.value
  
  for (let i = windowMins - 1; i >= 0; i--) {
    const minTime = now - (i * 60)
    const label = new Date(minTime * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    buckets[label] = { total: 0, limited: 0, auth: 0, unauth: 0 }
  }
  
  logs.value.forEach(log => {
    if (now - log.timestamp <= windowMins * 60) {
      const label = new Date(log.timestamp * 1000).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      const count = log.count || 1
      if (buckets[label]) {
        buckets[label].total += count
        if (log.is_rate_limited) buckets[label].limited += count
        if (log.is_authenticated) buckets[label].auth += count
        if (!log.is_authenticated) buckets[label].unauth += count
      }
    }
  })
  
  return {
    labels: Object.keys(buckets),
    datasets: [
      {
        label: 'Authenticated',
        data: Object.values(buckets).map(b => b.auth),
        borderColor: '#2196f3', // Blue
        backgroundColor: 'rgba(33, 150, 243, 0.1)',
        fill: true,
        tension: 0.4
      },
      {
        label: 'Unauthenticated',
        data: Object.values(buckets).map(b => b.unauth),
        borderColor: '#ff9800', // Orange
        backgroundColor: 'rgba(255, 152, 0, 0.1)',
        fill: true,
        tension: 0.4
      },
      {
        label: 'Blocked (DOS)',
        data: Object.values(buckets).map(b => b.limited),
        borderColor: '#f44336', // Red
        backgroundColor: 'rgba(244, 67, 54, 0.1)',
        fill: true,
        tension: 0.4
      }
    ]
  }
})

async function banIp() {
  if (!newBanIp.value) return
  try {
    await fetchApi('/admin/banned-ips', {
      method: 'POST',
      body: JSON.stringify({ ip: newBanIp.value })
    })
    newBanIp.value = ''
  } catch(e) {
    uiStore.showAlert(e.message)
  }
}

async function unbanIp(ip) {
  try {
    await fetchApi(`/admin/banned-ips/${encodeURIComponent(ip)}`, { method: 'DELETE' })
  } catch(e) {
    uiStore.showAlert(e.message)
  }
}

let ws = null
let isComponentMounted = false

function connectWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
  ws = new WebSocket(`${protocol}//${window.location.host}/api/admin/traffic/stream`)
  
  ws.onopen = async () => {
    const token = localStorage.getItem('token')
    const userStr = localStorage.getItem('user')
    if (token && userStr) {
      try {
        const user = JSON.parse(userStr)
        const payload = await encryptPayload({ token })
        ws.send(JSON.stringify(payload))
      } catch (e) {
        ws.send(JSON.stringify({ token }))
      }
    } else {
      ws.send(JSON.stringify({ token }))
    }
  }
  
  ws.onmessage = async (event) => {
    if (event.data === 'ping') return
    try {
      const data = JSON.parse(event.data)
      let parsed = data
      
      if (data.e2e_payload) {
        const decrypted = await decryptPayload(data.e2e_payload)
        if (decrypted) parsed = decrypted
      }
      
      if (parsed.type === 'init') {
        logs.value = parsed.logs || []
        bannedIps.value = parsed.banned_ips || []
        loaded.value = true
      } else if (parsed.type === 'batch') {
        // Server sends batched logs every ~1 second during high traffic
        const batchLogs = parsed.logs || []
        if (batchLogs.length > 0) {
          logs.value = [...batchLogs, ...logs.value].slice(0, 1000)
        }
      } else if (parsed.type === 'log') {
        logs.value.unshift(parsed.data)
        if (logs.value.length > 1000) logs.value.pop()
      } else if (parsed.type === 'ban') {
        if (!bannedIps.value.includes(parsed.ip)) {
          bannedIps.value.unshift(parsed.ip)
        }
      } else if (parsed.type === 'unban') {
        bannedIps.value = bannedIps.value.filter(ip => ip !== parsed.ip)
      }
    } catch(e) {
      console.error("WS parse error", e)
    }
  }
  
  ws.onclose = () => {
    if (isComponentMounted) {
      setTimeout(connectWebSocket, 3000)
    }
  }
}

let timerInterval = null

onMounted(() => {
  isComponentMounted = true
  loadActivities()
  connectWebSocket()
  timerInterval = setInterval(() => {
    currentTime.value = Math.floor(Date.now() / 1000)
  }, 1000)
})

onUnmounted(() => {
  isComponentMounted = false
  if (ws) ws.close()
  if (timerInterval) clearInterval(timerInterval)
})
</script>

<style scoped lang="scss">
.admin-wrapper {
  .metrics-summary {
    display: flex;
    gap: 20px;
    margin: 20px 0;
    
    @media (max-width: 768px) {
      flex-direction: column;
    }

    .metric-card {
      flex: 1;
      background: color-mix(in srgb, var(--border) 10%, transparent);
      padding: 20px;
      border-radius: 8px;
      border: 1px solid var(--border);
      display: flex;
      flex-direction: column;
      align-items: center;

      label {
        color: var(--secondary);
        font-size: 0.9rem;
        margin-bottom: 10px;
      }

      .value {
        font-size: 2.5rem;
        font-family: var(--font-heading);
        color: var(--primary);

        &.status-error {
          color: var(--error);
        }
      }
    }
  }

  .charts-container {
    display: flex;
    flex-direction: column;
    gap: 20px;
    max-width: 100%;
    margin-bottom: 20px;

    .chart-box {
      background: color-mix(in srgb, var(--border) 10%, transparent);
      padding: 20px;
      border-radius: 8px;
      border: 1px solid var(--border);

      h3 {
        margin-bottom: 20px;
        color: var(--primary);
      }
    }
  }

  .wireshark-log {
    margin-top: 20px;
    border-color: var(--border);

    h3 {
      margin-bottom: 15px;
      color: var(--primary);
    }
  }

  .table-container {
    max-height: 400px;
    overflow-y: auto;
    overflow-x: auto;

    .traffic-table {
      width: 100%;
      border-collapse: collapse;
      font-family: monospace;
      font-size: 0.9em;

      th {
        padding: 10px;
        text-align: left;
        border-bottom: 1px solid var(--border);
        color: var(--secondary);
        position: sticky;
        top: 0;
        background: var(--background);
      }

      td {
        padding: 8px 10px;
        text-align: left;
        border-bottom: 1px solid color-mix(in srgb, var(--text) 10%, transparent);
      }

      tr {
        &:hover {
          background: color-mix(in srgb, var(--text) 5%, transparent);
        }
        
        &.rate-limited {
          background-color: color-mix(in srgb, var(--error) 15%, transparent);
          color: var(--error);
          
          &:hover {
            background-color: color-mix(in srgb, var(--error) 25%, transparent);
          }
        }
      }
    }
  }
}
</style>

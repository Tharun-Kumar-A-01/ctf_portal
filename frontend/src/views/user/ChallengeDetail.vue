<template>
  <div>
    <NavBar />

    <div v-if="loading" class="boxy-card">
      <p>[INFO] LOADING...</p>
    </div>
    
    <div v-else-if="error" class="boxy-card error-card">
      <p>[ERROR] {{ error }}</p>
    </div>

    <div v-else-if="challenge" class="challenge-detail-container">
      <div class="boxy-card main-info" :class="{ solved: challenge.is_solved }">
        <div class="header-row">
          <h2>{{ challenge.title }}</h2>
          <span class="points" v-if="challenge.is_solved">++{{ challenge.points_earned }} PTS</span>
          <span class="points" v-else>{{ challenge.points }} PTS</span>
        </div>
        
        <div class="meta-row">
          <span class="time">[OPEN] {{ new Date(challenge.open_time).toLocaleString() }}</span>
          <span class="time">[CLOSE] {{ new Date(challenge.close_time).toLocaleString() }}</span>
        </div>

        <div class="description markdown-body" v-html="renderMarkdown(challenge.description)"></div>
        
        <div v-if="challenge.has_attachment" class="attachment-section" style="margin-bottom: 20px;">
          <button v-if="challenge.is_solved" class="btn" disabled>
            ATTACHMENT DOWNLOAD DISABLED [SOLVED]
          </button>
          <button v-else class="btn" @click="downloadAttachment" :disabled="downloading">
            {{ downloading ? 'DOWNLOADING...' : 'DOWNLOAD ATTACHMENT' }}
          </button>
        </div>

        <div class="stats-row">
          <div class="stat">
            <label>TEAM ATTEMPTS</label>
            <span :class="challenge.attempts > 0 ? (challenge.is_solved ? 'status-success' : 'status-error') : ''">
              {{ challenge.attempts }}
            </span>
          </div>
          <div class="stat" v-if="challenge.is_solved">
            <label>STATUS</label>
            <span class="status-success">SOLVED</span>
          </div>
        </div>
      </div>

      <div class="lower-panels">
        <div class="boxy-card submission-panel">
          <h3>SUBMIT FLAG</h3>
          <div v-if="challenge.is_solved" class="status-success">
            <br/>[INFO] SOLVED
          </div>
          <div v-else>
            <form @submit.prevent="submitFlag">
              <label class="flag-label">FLAG FORMAT: flag{...}</label>
              <div class="submit-row">
                <input v-model="flagInput" placeholder="ENTER FLAG HERE" required class="flex-input" />
                <button class="btn" type="submit" :disabled="submitting">
                  {{ submitting ? 'VERIFYING...' : 'SUBMIT' }}
                </button>
              </div>
            </form>
            
            <div v-if="submitMessage" class="submission-result" :class="{ 'status-success': isCorrect, 'status-error': !isCorrect }">
              > {{ submitMessage }}
            </div>
          </div>
        </div>
        
        <div v-if="challenge.has_hint && !challenge.is_solved" class="boxy-card hint-panel">
          <h3 class="hint-title">HINT</h3>
          <div v-if="challenge.hint_unlocked" class="hint-unlocked">
            <p><i>{{ challenge.hint_text }}</i></p>
          </div>
          <div v-else class="hint-locked">
            <button class="btn reveal-hint-btn" @click="unlockHint" :disabled="unlocking">
              REVEAL HINT (-{{ challenge.hint_penalty }} PTS)
            </button>
          </div>
        </div>
      </div>

      <div v-if="challenge.unlocks_children && challenge.unlocks_children.length > 0" class="boxy-card unlocks-panel" style="margin-top: 20px;">
        <h3 style="color: var(--primary);">UNLOCKS</h3>
        <p style="color: var(--secondary);">Solving this challenge will unlock the following problems:</p>
        <ul style="margin-top: 10px; list-style-type: square; margin-left: 20px; color: var(--text);">
          <li v-for="child in challenge.unlocks_children" :key="child">{{ child }}</li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script>
import { marked } from 'marked'
import { markedHighlight } from 'marked-highlight'
import hljs from 'highlight.js'

let markedConfigured = false;
if (!markedConfigured) {
  marked.use(markedHighlight({
    langPrefix: 'hljs language-',
    highlight(code, lang) {
      const language = hljs.getLanguage(lang) ? lang : 'plaintext'
      return hljs.highlight(code, { language }).value
    }
  }))
  markedConfigured = true;
}
</script>

<script setup>
import { ref, onMounted, onUnmounted, computed, nextTick } from 'vue'
import NavBar from '../../components/NavBar.vue'
import { useRoute } from 'vue-router'
import { fetchApi } from '../../api/client'
import DOMPurify from 'dompurify'
import { useUiStore } from '../../stores/ui'

const route = useRoute()
const uiStore = useUiStore()
const challenge = ref(null)
const loading = ref(true)
const error = ref('')

const flagInput = ref('')
const submitting = ref(false)
const submitMessage = ref('')
const isCorrect = ref(false)

const nextPenalty = computed(() => {
  if (!challenge.value) return 0
  const nextAttempt = challenge.value.attempts + 1
  if (nextAttempt <= 2) return 0
  return (nextAttempt - 2) * challenge.value.penalty_value
})

function renderMarkdown(text) {
  if (!text) return ''
  return DOMPurify.sanitize(marked.parse(text))
}

function addCopyButtons() {
  const pres = document.querySelectorAll('.markdown-body pre')
  pres.forEach(pre => {
    if (pre.querySelector('.copy-code-btn')) return
    
    const code = pre.querySelector('code')
    if (code) {
      const classList = Array.from(code.classList)
      const langClass = classList.find(c => c.startsWith('language-'))
      const lang = langClass ? langClass.replace('language-', '').toUpperCase() : 'TEXT'
      
      const langSpan = document.createElement('span')
      langSpan.className = 'code-lang'
      langSpan.innerText = lang
      
      const btn = document.createElement('button')
      btn.className = 'copy-code-btn'
      btn.innerText = 'COPY'
      btn.onclick = () => {
        navigator.clipboard.writeText(code.textContent).then(() => {
          btn.innerText = 'COPIED!'
          setTimeout(() => { btn.innerText = 'COPY' }, 2000)
        })
      }
      
      pre.insertBefore(langSpan, pre.firstChild)
      pre.insertBefore(btn, pre.firstChild)
    }
  })
}

async function loadChallengeDetails() {
  try {
    const data = await fetchApi(`/challenges/${route.params.id}`)
    challenge.value = data.challenge
    if (challenge.value.hint_unlocked && !challenge.value.is_solved) {
      fetchHint()
    }
  } catch(e) {
    error.value = e.message
  } finally {
    loading.value = false
    await nextTick()
    addCopyButtons()
  }
}

async function fetchHint() {
  try {
    const res = await fetchApi(`/challenges/${challenge.value.id}/hint`, { method: 'POST' })
    challenge.value.hint_text = res.hint_text
  } catch(e) {
    uiStore.showAlert(e.message)
  }
}

const downloading = ref(false)
const unlocking = ref(false)

async function downloadAttachment() {
  downloading.value = true
  try {
    const res = await fetchApi(`/challenges/${challenge.value.id}/attachment`)
    const base64Data = res.data
    const byteCharacters = atob(base64Data)
    const byteNumbers = new Array(byteCharacters.length)
    for (let i = 0; i < byteCharacters.length; i++) {
      byteNumbers[i] = byteCharacters.charCodeAt(i)
    }
    const byteArray = new Uint8Array(byteNumbers)
    const blob = new Blob([byteArray])
    
    const link = document.createElement('a')
    link.href = window.URL.createObjectURL(blob)
    link.download = res.filename
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  } catch(e) {
    uiStore.showAlert(e.message)
  } finally {
    downloading.value = false
  }
}

async function unlockHint() {
  uiStore.showConfirm(`Are you sure you want to unlock this hint? It will deduct ${challenge.value.hint_penalty} points from your team.`, 'REVEAL HINT', async () => {
    unlocking.value = true
    try {
      const res = await fetchApi(`/challenges/${challenge.value.id}/hint`, { method: 'POST' })
      challenge.value.hint_unlocked = true
      challenge.value.hint_text = res.hint_text
    } catch(e) {
      uiStore.showAlert(e.message)
    } finally {
      unlocking.value = false
    }
  })
}

async function submitFlag() {
  if (!flagInput.value) return
  
  const freeAttemptsLeft = Math.max(0, 2 - challenge.value.attempts)
  let confirmMessage = "Do you want to submit? "
  
  if (nextPenalty.value > 0) {
    confirmMessage += `wrong submission will cost ${nextPenalty.value} PTS.`
  } else {
    confirmMessage += `you have ${freeAttemptsLeft} attempts left.`
  }
  
  uiStore.showConfirm(confirmMessage, "SUBMIT FLAG", async () => {
    submitting.value = true
    submitMessage.value = ''
    
    try {
      const res = await fetchApi(`/challenges/${challenge.value.id}/submit`, {
        method: 'POST',
        body: JSON.stringify({ flag: flagInput.value })
      })
      submitMessage.value = res.message
      isCorrect.value = true
      challenge.value.is_solved = true
      challenge.value.attempts++
    } catch(e) {
      submitMessage.value = e.message
      isCorrect.value = false
      challenge.value.attempts++
    } finally {
      submitting.value = false
      flagInput.value = ''
    }
  })
}

onMounted(() => {
  loadChallengeDetails()
})
</script>

<style scoped lang="scss">
.error-card {
  color: var(--error);
}

.challenge-detail-container {
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-width: 900px;
  margin: 0 auto;

  .main-info {
    display: flex;
    flex-direction: column;
    
    &.solved {
      border-color: var(--border);
    }

    .header-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      border-bottom: 1px solid var(--border);
      padding-bottom: 15px;
      margin-bottom: 15px;

      .points {
        color: var(--accent);
        font-family: var(--font-heading);
        font-size: 1.5rem;
      }
    }

    .meta-row {
      display: flex;
      gap: 20px;
      color: var(--secondary);
      font-size: 0.9rem;
      margin-bottom: 20px;
    }

    .description {
      margin-bottom: 30px;
    }

    .stats-row {
      display: flex;
      gap: 30px;
      border-top: 1px solid var(--border);
      padding-top: 15px;

      .stat {
        display: flex;
        flex-direction: column;
        
        label {
          font-size: 0.8rem;
          color: var(--secondary);
        }
        
        span {
          font-size: 1.5rem;
          font-family: var(--font-heading);
          font-weight: bold;
        }

        .status-success {
          color: var(--accent);
        }

        .status-error {
          color: var(--error);
        }
      }
    }
  }

  .lower-panels {
    display: flex;
    gap: 20px;
    flex-direction: column-reverse; /* Stack hint above submit on mobile */

    @media (min-width: 768px) {
      flex-direction: row;
    }

    .submission-panel {
      flex: 1;
      display: flex;
      flex-direction: column;

      .status-success {
        color: var(--accent);
      }

      .status-error {
        color: var(--error);
      }

      .flag-label {
        color: var(--secondary);
        display: block;
        margin-bottom: 5px;
        margin-top: 15px;
      }

      .submit-row {
        display: flex;
        gap: 10px;

        .flex-input {
          flex: 1;
        }
      }

      .submission-result {
        margin-top: 15px;
      }
    }

    .hint-panel {
      flex: 1;
      display: flex;
      flex-direction: column;

      .hint-title {
        margin-top: 0;
        color: var(--primary);
      }

      .hint-unlocked {
        color: var(--text);
      }

      .hint-locked {
        display: flex;
        flex-direction: column;
        justify-content: flex-end;
        height: 100%;

        .reveal-hint-btn {
          width: fit-content;
          margin-left: auto;
          margin-top: auto;
        }
      }
    }
  }
}

.markdown-body :deep(h1), .markdown-body :deep(h2), .markdown-body :deep(h3) {
  margin-top: 1rem;
  margin-bottom: 0.5rem;
}

.markdown-body :deep(a) {
  color: var(--primary);
}
</style>

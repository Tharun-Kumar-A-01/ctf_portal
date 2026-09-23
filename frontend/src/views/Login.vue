<template>
  <div class="login-wrapper">
    <NavBar />
    
    <div class="login-container">
      <div class="boxy-card login-box">
      <h1 class="brand">LOGIN</h1>
      
      <form @submit.prevent="handleLogin">
        <div class="form-group">
          <label>EMAIL</label>
          <input type="email" v-model="email" required autocomplete="email" spellcheck="false" />
        </div>
        
        <div class="form-group">
          <label>PASSWORD</label>
          <input type="password" v-model="password" required autocomplete="current-password" />
        </div>
        
        <div v-if="error" class="login-error terminal-output">
          [ERROR] {{ error }}
        </div>
        
        <button type="submit" :disabled="loading" class="btn block-btn">
          {{ loading ? '[INFO] AUTHENTICATING' : 'LOGIN' }}
        </button>
      </form>
    </div>
  </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import NavBar from '../components/NavBar.vue'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const email = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function handleLogin() {
  loading.value = true
  error.value = ''
  
  try {
    await authStore.login(email.value, password.value)
    if (authStore.isAdmin) {
      router.push('/admin')
    } else {
      router.push('/challenges')
    }
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}
</script>

<style scoped lang="scss">
.login-wrapper {
  display: flex;
  flex-direction: column;

  .login-container {
    display: flex;
    justify-content: center;
    align-items: center;
    min-height: calc(80vh - 80px); /* Adjust for header */

    .login-box {
      width: 100%;
      max-width: 400px;

      .brand {
        margin-bottom: 30px;
        text-align: center;
        word-break: break-word;
        white-space: normal;
        font-size: clamp(1.2rem, 5vw, 2rem);
      }

      .form-group {
        margin-bottom: 20px;
        display: flex;
        flex-direction: column;

        label {
          margin-bottom: 5px;
          font-weight: bold;
          color: var(--secondary);
        }
      }

      .login-error {
        color: var(--error);
      }

      .terminal-output {
        margin: 10px 0;
        font-size: 0.9em;
      }

      .block-btn {
        width: 100%;
        margin-top: 10px;
      }
    }
  }
}
</style>

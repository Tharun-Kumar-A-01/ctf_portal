<template>
  <div class="banned-container">
    <div class="boxy-card error-card">
      <h1 class="banned-error-text">ACCESS_DENIED</h1>
      <p class="banned-error-text">[ERROR] USER IS NOT IN SUDOERS FILE.</p>
      
      <p class="spaced">
        Your account or team has been permanently banned from the CTF platform due to any of the following reasons 
      </p>
      
      <ul class="reasons">
        <li>[WARN] EXCEEDED_MAXIMUM_WRONG_ATTEMPTS (50)</li>
        <li>[WARN] MANUAL_ADMIN_BAN</li>
        <li>[WARN] FLAG_SHARING_OR_EXPLOITATION</li>
      </ul>
      
      <p class="spaced banned-dim-text">
        If you believe this is an error, please contact the coordinators.
      </p>

      <button class="btn spaced" @click="authStore.logout(); $router.push('/login')">RETURN TO LOGIN</button>
    </div>
  </div>
</template>

<script setup>
import { useAuthStore } from '../stores/auth'
const authStore = useAuthStore()
</script>

<style scoped lang="scss">
.banned-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 80vh;

  .error-card {
    max-width: 600px;
    text-align: center;
    border-color: var(--error);
    box-shadow: 0 0 10px var(--error-dark);

    .banned-error-text {
      color: var(--error);
    }

    .spaced {
      margin-top: 15px;
    }

    .reasons {
      text-align: left;
      margin-top: 20px;
      color: var(--warning);
      font-family: var(--font-body); /* Used font-body instead of font-mono since font-mono isn't in main.scss */
      list-style: none;
      padding: 0;

      li {
        margin-bottom: 10px;
      }
    }

    .banned-dim-text {
      color: var(--secondary);
      font-size: 0.9em;
    }
  }
}
</style>

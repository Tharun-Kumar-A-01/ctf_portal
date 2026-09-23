<template>
  <div v-if="timer" class="countdown-wrapper boxy-card" :class="stateClass">
    <div class="note" v-if="timer.note">[{{ timer.note }}]</div>
    <div class="timer-display">
      <span v-if="sign" class="sign">{{ sign }}</span>
      <div class="time-box">
        <span class="digit">{{ hours[0] }}</span><span class="digit">{{ hours[1] }}</span>
      </div>
      <span class="separator">:</span>
      <div class="time-box">
        <span class="digit">{{ minutes[0] }}</span><span class="digit">{{ minutes[1] }}</span>
      </div>
      <span class="separator">:</span>
      <div class="time-box">
        <span class="digit">{{ seconds[0] }}</span><span class="digit">{{ seconds[1] }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch, computed } from 'vue'

const props = defineProps({
  timer: Object
})

const hours = ref('00')
const minutes = ref('00')
const seconds = ref('00')
const sign = ref('')
const isExpired = ref(false)
const isWarning = ref(false)

let interval = null

function updateTimer() {
  if (!props.timer || !props.timer.expires_at) {
    isExpired.value = false
    isWarning.value = false
    sign.value = ''
    return
  }

  const target = new Date(props.timer.expires_at).getTime()
  if (isNaN(target)) {
    isExpired.value = false
    isWarning.value = false
    sign.value = ''
    return
  }
  const now = new Date().getTime()
  let diff = target - now

  if (diff < 0) {
    isExpired.value = true
    isWarning.value = false
    sign.value = '-'
    diff = Math.abs(diff)
  } else {
    isExpired.value = false
    sign.value = ''
    isWarning.value = diff <= 5 * 60 * 1000 // 5 minutes
  }
  
  const h = Math.floor(diff / (1000 * 60 * 60))
  const m = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))
  const s = Math.floor((diff % (1000 * 60)) / 1000)
  
  hours.value = h.toString().padStart(2, '0')
  minutes.value = m.toString().padStart(2, '0')
  seconds.value = s.toString().padStart(2, '0')
}

const stateClass = computed(() => {
  if (isExpired.value) return 'expired'
  if (isWarning.value) return 'warning'
  return 'normal'
})

watch(() => props.timer, () => {
  updateTimer()
}, { deep: true })

onMounted(() => {
  updateTimer()
  interval = setInterval(updateTimer, 1000)
})

onUnmounted(() => {
  if (interval) clearInterval(interval)
})
</script>

<style scoped lang="scss">
.countdown-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 15px;
  padding: 20px;
  margin-bottom: 20px;
  background: linear-gradient(180deg, color-mix(in srgb, var(--primary) 10%, transparent) 0%, var(--background) 100%);
  border-top: 2px solid var(--primary);

  &.warning {
    border-top-color: var(--warning);
    background: linear-gradient(180deg, color-mix(in srgb, var(--warning) 10%, transparent) 0%, var(--background) 100%);
  }

  &.expired {
    border-top-color: var(--error);
    background: linear-gradient(180deg, color-mix(in srgb, var(--error) 15%, transparent) 0%, var(--background) 100%);
  }

  &.normal {
    .note,
    .time-box,
    .separator,
    .sign {
      color: var(--primary);
      border-color: var(--primary);
    }
  }

  &.warning {
    .note,
    .time-box,
    .separator,
    .sign {
      color: var(--warning);
      border-color: var(--warning);
    }
  }

  &.expired {
    .note,
    .time-box,
    .separator,
    .sign {
      color: var(--error);
      border-color: var(--error);
      text-shadow: 0 0 10px rgba(255, 85, 85, 0.3);
    }
  }

  .note {
    font-weight: bold;
    letter-spacing: 2px;
    font-size: 0.9rem;
    text-transform: uppercase;
  }

  .timer-display {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 8px;

    .sign {
      font-family: var(--font-heading), monospace;
      font-size: 40px;
      font-weight: 700;
      margin-right: 10px;
    }

    .time-box {
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 10px 15px;
      background: rgba(0, 0, 0, 0.4);
      border: 1px solid;
      gap: 5px;

      .digit {
        display: inline-block;
        width: 24px;
        text-align: center;
        font-family: var(--font-heading), monospace;
        font-variant-numeric: tabular-nums;
        font-size: 32px;
        font-weight: 700;
        letter-spacing: 0px;
      }
    }

    .separator {
      font-family: var(--font-heading), monospace;
      font-size: 32px;
      font-weight: 700;
      margin: 0 4px;
    }
  }

  @media (max-width: 420px) {
    padding: 15px;
    
    .timer-display {
      gap: 4px;

      .sign {
        font-size: 30px;
        margin-right: 4px;
      }

      .time-box {
        padding: 8px 10px;

        .digit {
          width: 18px;
          font-size: 24px;
        }
      }

      .separator {
        font-size: 24px;
        margin: 0 2px;
      }
    }
  }
}
</style>

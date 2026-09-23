<template>
  <div v-if="uiStore.modalOpen" class="modal-overlay" @click.self="uiStore.closeModal">
    <div class="boxy-card modal-content">
      <h3 v-if="uiStore.modalTitle" class="modal-title">{{ uiStore.modalTitle }}</h3>
      
      <div class="modal-body">
        <p>{{ uiStore.modalMessage }}</p>
      </div>

      <div class="modal-actions">
        <button v-if="uiStore.isConfirm" class="btn" @click="uiStore.confirmAction">OK</button>
        <button v-if="uiStore.isConfirm" class="btn modal-btn-cancel" @click="uiStore.closeModal">CANCEL</button>
        <button v-else class="btn" @click="uiStore.closeModal">OK</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { useUiStore } from '../stores/ui'
const uiStore = useUiStore()
</script>

<style scoped lang="scss">
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: var(--background);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;

  .modal-content {
    width: 90%;
    max-width: 400px;

    .modal-title {
      margin-top: 0;
      color: var(--primary);
    }

    .modal-body {
      margin: 20px 0;
      color: var(--text);
    }

    .modal-actions {
      display: flex;
      justify-content: flex-end;
      gap: 10px;

      .modal-btn-cancel {
        border-color: var(--error) !important;
        color: var(--error) !important;

        &:hover {
          background-color: var(--error) !important;
          color: var(--background) !important;
        }
      }
    }
  }
}
</style>

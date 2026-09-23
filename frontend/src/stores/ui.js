import { defineStore } from 'pinia'

export const useUiStore = defineStore('ui', {
  state: () => ({
    modalOpen: false,
    modalTitle: '',
    modalMessage: '',
    isConfirm: false,
    onConfirmCallback: null
  }),
  actions: {
    showAlert(message, title = 'ALERT') {
      this.modalMessage = message
      this.modalTitle = title
      this.isConfirm = false
      this.modalOpen = true
    },
    showConfirm(message, title = 'CONFIRM', callback) {
      this.modalMessage = message
      this.modalTitle = title
      this.isConfirm = true
      this.onConfirmCallback = callback
      this.modalOpen = true
    },
    confirmAction() {
      if (this.onConfirmCallback) {
        this.onConfirmCallback()
      }
      this.closeModal()
    },
    closeModal() {
      this.modalOpen = false
      this.isConfirm = false
      this.onConfirmCallback = null
    }
  }
})

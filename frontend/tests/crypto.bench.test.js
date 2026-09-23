import { it, describe, expect } from 'vitest'
import { TextEncoder, TextDecoder } from 'util'

// JSDOM doesn't have TextEncoder/Decoder by default
global.TextEncoder = TextEncoder
global.TextDecoder = TextDecoder

// Basic AES-GCM simulation using WebCrypto (available in Node.js >= 15 as global.crypto)
describe('WebCrypto AES-GCM Performance', () => {
  it('AES-GCM Encryption Throughput', async () => {
    const key = await crypto.subtle.generateKey(
      { name: "AES-GCM", length: 256 },
      true,
      ["encrypt", "decrypt"]
    )
    const plaintext = new TextEncoder().encode("benchmark payload data " + "a".repeat(100))
    const localIv = crypto.getRandomValues(new Uint8Array(12))
    
    const start = performance.now()
    for (let i = 0; i < 1000; i++) {
      await crypto.subtle.encrypt(
        { name: "AES-GCM", iv: localIv },
        key,
        plaintext
      )
    }
    const elapsed = performance.now() - start
    
    // Ensure 1000 encryptions take less than 500ms
    expect(elapsed).toBeLessThan(500)
    console.log(`[Benchmark] AES-GCM 1000 Encrypts took: ${elapsed.toFixed(2)}ms`)
  })

  it('AES-GCM Decryption Throughput', async () => {
    const key = await crypto.subtle.generateKey(
      { name: "AES-GCM", length: 256 },
      true,
      ["encrypt", "decrypt"]
    )
    const plaintext = new TextEncoder().encode("benchmark payload data " + "a".repeat(100))
    const iv = crypto.getRandomValues(new Uint8Array(12))
    const ciphertext = await crypto.subtle.encrypt(
      { name: "AES-GCM", iv: iv },
      key,
      plaintext
    )

    const start = performance.now()
    for (let i = 0; i < 1000; i++) {
      await crypto.subtle.decrypt(
        { name: "AES-GCM", iv: iv },
        key,
        ciphertext
      )
    }
    const elapsed = performance.now() - start
    expect(elapsed).toBeLessThan(500)
    console.log(`[Benchmark] AES-GCM 1000 Decrypts took: ${elapsed.toFixed(2)}ms`)
  })
  
  it('PBKDF2 Key Derivation penalty', async () => {
    const passwordBytes = new TextEncoder().encode("user-password-1234")
    const salt = new Uint8Array(16) // Mock static salt
    
    const keyMaterial = await crypto.subtle.importKey(
      "raw",
      passwordBytes,
      { name: "PBKDF2" },
      false,
      ["deriveBits", "deriveKey"]
    )
    
    const start = performance.now()
    for (let i = 0; i < 10; i++) {
      await crypto.subtle.deriveKey(
        {
          name: "PBKDF2",
          salt: salt,
          iterations: 100000,
          hash: "SHA-256"
        },
        keyMaterial,
        { name: "AES-GCM", length: 256 },
        true,
        ["encrypt", "decrypt"]
      )
    }
    const elapsed = performance.now() - start
    console.log(`[Benchmark] PBKDF2 10 derivations took: ${elapsed.toFixed(2)}ms`)
    expect(elapsed).toBeLessThan(2000)
  })
})

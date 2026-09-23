import { describe, it, expect, vi } from 'vitest'

// Create a basic polyfill for TextEncoder/TextDecoder in jsdom
import { TextEncoder, TextDecoder } from 'util'
global.TextEncoder = TextEncoder
global.TextDecoder = TextDecoder

// We mock fetch for initE2E fallback test if needed.
let mockFetch = vi.fn()
global.fetch = mockFetch

describe('E2E Cryptography Utilities', () => {
  it('Math dependencies verify natively (Node.js WebCrypto)', async () => {
    // Assert subtle crypto is available in the testing environment
    expect(crypto.subtle).toBeDefined()
    
    // Generate an ephemeral AES key
    const rawAesKey = await crypto.subtle.generateKey(
      { name: "AES-GCM", length: 256 },
      true,
      ["encrypt", "decrypt"]
    )
    
    // Verify properties
    expect(rawAesKey.algorithm.name).toBe("AES-GCM")
  })
})

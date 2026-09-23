const API_URL = '/api';

// --- E2E Cryptography State ---
/** @type {CryptoKey|null} */
let aesKey = null;
/** @type {CryptoKey|null} */
let rsaPublicKey = null;
/** @type {Promise<void>|null} */
let e2eInitPromise = null;

/**
 * @param {ArrayBuffer} buffer
 * @returns {string}
 */
function arrayBufferToBase64(buffer) {
  let binary = '';
  const bytes = new Uint8Array(buffer);
  for (let i = 0; i < bytes.byteLength; i++) binary += String.fromCharCode(bytes[i]);
  return btoa(binary);
}

/**
 * @param {string} base64
 * @returns {ArrayBuffer}
 */
function base64ToArrayBuffer(base64) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  return bytes.buffer;
}

/**
 * @param {string} str
 * @returns {ArrayBuffer}
 */
function str2ab(str) {
  const buf = new ArrayBuffer(str.length);
  const bufView = new Uint8Array(buf);
  for (let i = 0; i < str.length; i++) bufView[i] = str.charCodeAt(i);
  return buf;
}

/**
 * Imports a PEM-encoded RSA public key for OAEP encryption.
 * @param {string} pem
 * @returns {Promise<CryptoKey>}
 */
async function importRsaKey(pem) {
  const pemHeader = "-----BEGIN PUBLIC KEY-----";
  const pemFooter = "-----END PUBLIC KEY-----";
  const pemContents = pem.substring(pem.indexOf(pemHeader) + pemHeader.length, pem.indexOf(pemFooter)).replace(/\s/g, '');
  return await crypto.subtle.importKey(
    "spki", str2ab(atob(pemContents)),
    { name: "RSA-OAEP", hash: "SHA-256" },
    true, ["encrypt"]
  );
}

/**
 * Initializes the mandatory E2E encryption tunnel.
 * Requires a secure context (HTTPS or localhost).
 * @returns {Promise<void>}
 */
async function initE2E() {
  if (e2eInitPromise) return e2eInitPromise;

  e2eInitPromise = (async () => {
    try {
      if (!window.crypto || !window.crypto.subtle) {
        throw new Error("E2E encryption requires a Secure Context (HTTPS or localhost).");
      }

      aesKey = await crypto.subtle.generateKey({ name: "AES-GCM", length: 256 }, true, ["encrypt", "decrypt"]);
      const pubKeyRes = await fetch(`${API_URL}/e2e/public-key`);
      if (!pubKeyRes.ok) throw new Error(`E2E public key fetch failed: ${pubKeyRes.status}`);
      const pubKeyData = await pubKeyRes.json();
      rsaPublicKey = await importRsaKey(pubKeyData.public_key);
      const rawAesKey = await crypto.subtle.exportKey("raw", aesKey);
      const encryptedAesKey = await crypto.subtle.encrypt({ name: "RSA-OAEP" }, rsaPublicKey, rawAesKey);

      const handshakeRes = await fetch(`${API_URL}/e2e/handshake`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ encrypted_aes_key: arrayBufferToBase64(encryptedAesKey) })
      });
      if (!handshakeRes.ok) throw new Error("E2E handshake failed");
      console.log("[E2E] Secure tunnel established");
    } catch (e) {
      console.warn("[E2E] Initialization failed, falling back to plaintext (SSL only):", e.message);
      aesKey = null;
      rsaPublicKey = null;
    }
  })();

  return e2eInitPromise;
}


/**
 * Encrypts a user ID using the server's RSA public key.
 * @param {string|number} userId
 * @returns {Promise<string|null>}
 */
export async function rsaEncryptUserId(userId) {
  if (!rsaPublicKey) return null;
  const data = new TextEncoder().encode(userId.toString());
  const encrypted = await crypto.subtle.encrypt({ name: "RSA-OAEP" }, rsaPublicKey, data);
  return arrayBufferToBase64(encrypted);
}

/**
 * Encrypts a JSON-serializable payload using AES-GCM.
 * @param {Object} data
 * @returns {Promise<Object>}
 */
export async function encryptPayload(data) {
  if (!aesKey) return data;
  const iv = crypto.getRandomValues(new Uint8Array(12));
  const ciphertextWithTag = await crypto.subtle.encrypt(
    { name: "AES-GCM", iv: iv }, aesKey, new TextEncoder().encode(JSON.stringify(data))
  );
  const ciphertext = ciphertextWithTag.slice(0, ciphertextWithTag.byteLength - 16);
  const tag = ciphertextWithTag.slice(ciphertextWithTag.byteLength - 16);
  return { e2e_payload: `${arrayBufferToBase64(iv)}.${arrayBufferToBase64(ciphertext)}.${arrayBufferToBase64(tag)}` };
}

/**
 * Decrypts an E2E payload string (iv.ciphertext.tag format).
 * @param {string} payloadStr
 * @returns {Promise<Object|null>}
 */
export async function decryptPayload(payloadStr) {
  if (!aesKey) return null;
  if (!payloadStr || typeof payloadStr !== 'string') return null;
  const parts = payloadStr.split('.');
  if (parts.length !== 3) return null;
  const iv = base64ToArrayBuffer(parts[0]);
  const ciphertext = base64ToArrayBuffer(parts[1]);
  const tag = base64ToArrayBuffer(parts[2]);

  const combined = new Uint8Array(ciphertext.byteLength + tag.byteLength);
  combined.set(new Uint8Array(ciphertext), 0);
  combined.set(new Uint8Array(tag), ciphertext.byteLength);

  try {
    const decrypted = await crypto.subtle.decrypt({ name: "AES-GCM", iv: new Uint8Array(iv) }, aesKey, combined.buffer);
    return JSON.parse(new TextDecoder().decode(decrypted));
  } catch (e) {
    console.error("[E2E] Decryption failed:", e);
    return null;
  }
}

/**
 * Makes an API request with mandatory E2E encryption/decryption.
 * @param {string} endpoint
 * @param {RequestInit} [options={}]
 * @returns {Promise<Object>}
 */
export async function fetchApi(endpoint, options = {}) {
  if (!endpoint.startsWith('/e2e/')) await initE2E();

  const token = localStorage.getItem('token');
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  if (options.body instanceof FormData) delete headers['Content-Type'];

  let body = options.body;
  const skipEncryption = endpoint.startsWith('/leaderboard') || endpoint.startsWith('/e2e/');

  if (body && typeof body === 'string' && headers['Content-Type'] === 'application/json' && !skipEncryption && aesKey) {
    try {
      body = JSON.stringify(await encryptPayload(JSON.parse(body)));
    } catch (e) {
      console.warn("Could not encrypt payload, sending plain", e);
    }
  }

  const response = await fetch(`${API_URL}${endpoint}`, { ...options, headers, body });
  let data = await response.json().catch(() => ({}));

  if (data.e2e_payload && !skipEncryption && aesKey) {
    const decrypted = await decryptPayload(data.e2e_payload);
    if (decrypted) data = decrypted;
  }

  if (!response.ok) {
    if (response.status === 403 || response.status === 429) {
      const msg = (data.error || data.description || '').toLowerCase();
      if (msg.includes('banned') || msg.includes('exceeded')) {
        window.location.href = '/banned';
      }
    }
    throw new Error(data.error || 'API Request Failed');
  }
  return data;
}

import { vi } from 'vitest'

const originalFetch = global.fetch;
global.fetch = async (url, options) => {
  // Fix relative URLs for Node.js fetch
  const parsedUrl = typeof url === 'string' && url.startsWith('/') 
    ? `http://localhost${url}` 
    : url;
  
  // Return a mock response for the E2E public key to prevent connection refused errors in unit tests
  if (typeof parsedUrl === 'string' && parsedUrl.includes('/api/e2e/public-key')) {
    return {
      ok: true,
      json: async () => ({ public_key: '-----BEGIN PUBLIC KEY-----\nMockKey\n-----END PUBLIC KEY-----' })
    };
  }
  
  return originalFetch(parsedUrl, options);
};

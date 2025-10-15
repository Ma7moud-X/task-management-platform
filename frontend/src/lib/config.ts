
export const config = {
  apiBaseUrl: '/api',  // Proxied API calls
  backendBaseUrl: process.env.NEXT_PUBLIC_BACKEND_BASE_URL || 'http://localhost:8000',  // Direct backend URL for OAuth
  websocketBaseUrl: process.env.NEXT_PUBLIC_WEBSOCKET_BASE_URL || 'ws://localhost:8000',
} as const;

export const config = {
  apiBaseUrl: '/api',
  websocketBaseUrl: process.env.NEXT_PUBLIC_WEBSOCKET_BASE_URL || 'ws://localhost:8000',
} as const;
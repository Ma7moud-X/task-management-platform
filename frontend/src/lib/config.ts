
export const config = {
  apiBaseUrl: process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000',
  websocketBaseUrl: process.env.NEXT_PUBLIC_WEBSOCKET_BASE_URL || 'ws://localhost:8000',
} as const;
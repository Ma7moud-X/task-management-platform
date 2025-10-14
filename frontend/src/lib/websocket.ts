import { config } from '@/lib/config';
import { Task } from '@/types';
import { getAccessToken } from '@/lib/auth';

type WSEvent = 'created' | 'updated' | 'deleted';
type WSCallback = (event: WSEvent, task: Task) => void;

export class WebSocketManager {
  private socket: WebSocket | null = null;
  private orgId: string | null = null;
  private callbacks: WSCallback[] = [];
  private retryTimeout: ReturnType<typeof setTimeout> | null = null;

  connect(orgId: string) {
    if (this.socket?.readyState === WebSocket.OPEN && this.orgId === orgId) {
      return; // already connected to same org
    }

    this.disconnect();

    this.orgId = orgId;
    const token = getAccessToken();
    if (!token) {
      console.error('Cannot connect WebSocket: No access token available');
      return;
    }
    
    const url = `${config.websocketBaseUrl}/ws/${orgId}?token=${encodeURIComponent(token)}`;

    this.socket = new WebSocket(url);

    this.socket.onopen = () => {
      console.log('WebSocket connected');
      if (this.retryTimeout) {
        clearTimeout(this.retryTimeout);
        this.retryTimeout = null;
      }
    };

    this.socket.onmessage = (event) => {
      try {
        const message = JSON.parse(event.data);
        const { event: eventType, data: task } = message;

        if (eventType === 'created' || eventType === 'updated' || eventType === 'deleted') {
          this.callbacks.forEach((cb) => cb(eventType, task));
        }
      } catch (e) {
        console.error('WebSocket message parse error:', e);
      }
    };

    this.socket.onclose = () => {
      console.log('WebSocket disconnected');
      this.socket = null;
      // Auto-reconnect after 3s (basic resilience)
      if (this.orgId) {
        this.retryTimeout = setTimeout(() => this.connect(this.orgId!), 3000);
      }
    };

    this.socket.onerror = (error) => {
      console.error('WebSocket error:', error);
    };
  }

  disconnect() {
    if (this.retryTimeout) {
      clearTimeout(this.retryTimeout);
      this.retryTimeout = null;
    }
    if (this.socket) {
      this.socket.close();
      this.socket = null;
    }
    this.orgId = null;
  }

  subscribe(callback: WSCallback) {
    this.callbacks.push(callback);
    return () => {
      this.callbacks = this.callbacks.filter((cb) => cb !== callback);
    };
  }
}

export const wsManager = new WebSocketManager();
import { config } from '@/lib/config';

export async function api<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  // Build URL using the API base (which is now /api for proxy)
  const url = `${config.apiBaseUrl}${endpoint}`;

  const headers = {
    'Content-Type': 'application/json',
    ...options.headers,
  };

  const response = await fetch(url, {
    ...options,
    headers,
    credentials: 'include',  // This sends cookies automatically
  });

  // Handle 401 errors by attempting to refresh the token
  if (response.status === 401 && endpoint !== '/auth/refresh' && endpoint !== '/auth/me') {
    try {
      const refreshResponse = await fetch(`${config.apiBaseUrl}/auth/refresh`, {
        method: 'POST',
        credentials: 'include',
      });

      if (refreshResponse.ok) {
        // Retry original request
        return fetch(url, {
          ...options,
          headers,
          credentials: 'include',
        }).then(async (retryResponse) => {
          if (!retryResponse.ok) {
            const errorData = await retryResponse.json().catch(() => ({}));
            throw new Error(errorData.detail || 'An error occurred');
          }

          if (retryResponse.status === 204 || retryResponse.headers.get('content-length') === '0') {
            return {} as T;
          }

          const contentType = retryResponse.headers.get('content-type');
          if (contentType && contentType.includes('application/json')) {
            return retryResponse.json() as Promise<T>;
          }

          return {} as T;
        });
      } else {
        // Refresh failed, redirect to login
        if (typeof window !== 'undefined') {
          window.location.href = '/auth/login';
        }
        throw new Error('Session expired');
      }
    } catch (error) {
      // Refresh failed, redirect to login
      if (typeof window !== 'undefined') {
        window.location.href = '/auth/login';
      }
      throw error;
    }
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'An error occurred');
  }

  // Handle responses with no content (e.g., 204 No Content from DELETE requests)
  if (response.status === 204 || response.headers.get('content-length') === '0') {
    return {} as T;
  }

  // Check if response has JSON content
  const contentType = response.headers.get('content-type');
  if (contentType && contentType.includes('application/json')) {
    return response.json() as Promise<T>;
  }

  // For non-JSON responses, return empty object
  return {} as T;
}

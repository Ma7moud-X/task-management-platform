import { getAccessToken } from '@/lib/auth';

export async function api<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const url = `/api${endpoint}`;

  // Auto-attach auth header if token exists
  const token = getAccessToken();
  const headers = {
    'Content-Type': 'application/json',
    ...(token && { Authorization: `Bearer ${token}` }), // conditionally adding the token
    ...options.headers, // conditionally adding options (if not null)
  };

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new Error(errorData.detail || 'An error occurred');
  }

  return response.json() as Promise<T>;
}
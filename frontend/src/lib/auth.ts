import { AuthUser } from '@/types';
import { api } from './api';

const EMAIL_OTP_KEY = 'email_for_otp';

// Helper to check if we're in browser environment
const isBrowser = typeof window !== 'undefined';

export async function getCurrentUser(): Promise<AuthUser | null> {
  try {
    const response = await api<AuthUser>('/auth/me');
    return response;
  } catch (error) {
    console.error('Failed to get current user:', error);
    return null;
  }
}

export function setEmailForOtp(email: string) {
  if (isBrowser) {
    localStorage.setItem(EMAIL_OTP_KEY, email);
  }
}

export function getEmailForOtp(): string | null {
  if (!isBrowser) return null;
  return localStorage.getItem(EMAIL_OTP_KEY);
}

export function clearEmailForOtp() {
  if (isBrowser) {
    localStorage.removeItem(EMAIL_OTP_KEY);
  }
}

export async function logout(): Promise<void> {
  try {
    await api('/auth/logout', { method: 'POST' });
  } catch (error) {
    console.error('Logout failed:', error);
  } finally {
    // Clear any stored data
    clearEmailForOtp();
  }
}


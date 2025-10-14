import { AuthUser } from '@/types';
import { parseJwt } from './jwt';

const TOKEN_KEY = 'access_token';
const EMAIL_OTP_KEY = 'email_for_otp';

// Helper to check if we're in browser environment
const isBrowser = typeof window !== 'undefined';

export function setAuth(token: string) {
  if (isBrowser) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.removeItem(EMAIL_OTP_KEY);
  }
}

export function clearAuth() {
  if (isBrowser) {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(EMAIL_OTP_KEY);
  }
}

export function getAccessToken(): string | null {
  if (!isBrowser) return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getCurrentUser(): AuthUser | null {
  const token = getAccessToken();
  if (!token) return null;
  
  const payload = parseJwt(token);
  if (!payload) return null;
  
  return {
    id: payload.sub,
    email: payload.email,
    role: payload.role,
    org_id: payload.org_id,
  };
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

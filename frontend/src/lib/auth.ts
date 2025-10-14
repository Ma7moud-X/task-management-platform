import { AuthUser } from '@/types';
import { parseJwt } from './jwt';

const TOKEN_KEY = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';
const EMAIL_OTP_KEY = 'email_for_otp';

// Helper to check if we're in browser environment
const isBrowser = typeof window !== 'undefined';

export function setAuth(token: string, refreshToken?: string) {
  if (isBrowser) {
    localStorage.setItem(TOKEN_KEY, token);
    if (refreshToken) {
      localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
    }
    localStorage.removeItem(EMAIL_OTP_KEY);
  }
}

export function setTokens(accessToken: string, refreshToken: string) {
  if (isBrowser) {
    localStorage.setItem(TOKEN_KEY, accessToken);
    localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
  }
}

export function clearAuth() {
  if (isBrowser) {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    localStorage.removeItem(EMAIL_OTP_KEY);
  }
}

export function getAccessToken(): string | null {
  if (!isBrowser) return null;
  return localStorage.getItem(TOKEN_KEY);
}

export function getRefreshToken(): string | null {
  if (!isBrowser) return null;
  return localStorage.getItem(REFRESH_TOKEN_KEY);
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

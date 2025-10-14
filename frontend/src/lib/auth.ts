import { AuthUser } from '@/types';
import { parseJwt } from './jwt';

let currentUser: AuthUser | null = null;
let currentToken: string | null = null;
let userEmailForOtp: string | null = null;

export function setAuth(token: string, user: AuthUser) {
  currentToken = token;
  currentUser = user;
  userEmailForOtp = null; // clear after login
}

export function clearAuth() {
  currentToken = null;
  currentUser = null;
  userEmailForOtp = null;
}

export function getAccessToken(): string | null {
  return currentToken;
}

export function getCurrentUser(): AuthUser | null {
  if (!currentToken) return null;
  const payload = parseJwt(currentToken);
  if (!payload) return null;
  
  return {
    id: payload.sub,
    email: payload.email,
    role: payload.role,
    org_id: payload.org_id,
  };
}

export function setEmailForOtp(email: string) {
  userEmailForOtp = email;
}

export function getEmailForOtp(): string | null {
  return userEmailForOtp;
}

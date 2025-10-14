import { User } from '@/types';

let currentUser: User | null = null;
let currentToken: string | null = null;
let userEmailForOtp: string | null = null;

export function setAuth(token: string, user: User) {
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

export function getCurrentUser(): User | null {
  return currentUser;
}

export function setEmailForOtp(email: string) {
  userEmailForOtp = email;
}

export function getEmailForOtp(): string | null {
  return userEmailForOtp;
}


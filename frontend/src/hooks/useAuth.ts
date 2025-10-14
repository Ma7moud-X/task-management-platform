'use client';

import { useState, useEffect } from 'react';
import { AuthUser } from '@/types';
import { getCurrentUser } from '@/lib/auth';

export function useAuth() {
  const [user, setUser] = useState<AuthUser | null>(getCurrentUser());
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // On mount, check if user is already logged in (e.g., from another tab)
    const currentUser = getCurrentUser();
    setUser(currentUser);
    setLoading(false);
  }, []);

  return { user, loading };
}
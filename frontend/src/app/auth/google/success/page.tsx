'use client';

import { useEffect, useState } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { api } from '@/lib/api';

export default function GoogleSuccessPage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [error, setError] = useState('');

  useEffect(() => {
    async function completeGoogleLogin() {
      const errorParam = searchParams.get('error');
      
      if (errorParam) {
        // If there's an error from OAuth, redirect to login
        router.push('/auth/login?error=oauth_failed');
        return;
      }

      const accessToken = searchParams.get('access_token');
      const refreshToken = searchParams.get('refresh_token');

      if (!accessToken || !refreshToken) {
        router.push('/auth/login?error=oauth_failed');
        return;
      }

      try {
        // Exchange tokens for HttpOnly cookies via backend
        await api('/auth/google/complete', {
          method: 'POST',
          body: JSON.stringify({
            access_token: accessToken,
            refresh_token: refreshToken,
            token_type: 'bearer'
          }),
        });

        router.push('/dashboard');
      } catch (err: any) {
        console.error('Failed to complete Google login:', err);
        setError('Failed to complete sign in. Please try again.');
        setTimeout(() => {
          router.push('/auth/login');
        }, 2000);
      }
    }

    completeGoogleLogin();
  }, [searchParams, router]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-900">
      <div className="text-center">
        {error ? (
          <>
            <p className="text-red-400 mb-4">{error}</p>
            <p className="text-gray-400 text-sm">Redirecting to login...</p>
          </>
        ) : (
          <>
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
            <p className="text-gray-300">Completing sign in...</p>
          </>
        )}
      </div>
    </div>
  );
}

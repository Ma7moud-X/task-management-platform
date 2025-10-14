'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { getAccessToken, getCurrentUser, clearAuth } from '@/lib/auth';
import { Task } from '@/types';

export default function DashboardPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const router = useRouter();

  useEffect(() => {
    const token = getAccessToken();
    if (!token) {
      router.push('/auth/login');
      return;
    }

    const user = getCurrentUser();
    if (!user) {
      clearAuth();
      router.push('/auth/login');
      return;
    }

    // Fetch tasks
    const fetchTasks = async () => {
      try {
        const data = await api<Task[]>('/organizations/' + user.org_id + '/tasks', {
          method: 'GET',
        });
        setTasks(data);
      } catch (err: any) {
        if (err.message?.includes('401') || err.message?.includes('403')) {
          clearAuth();
          router.push('/auth/login');
        } else {
          setError('Failed to load tasks');
        }
      } finally {
        setLoading(false);
      }
    };

    fetchTasks();
  }, [router]);

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <p className="text-white">Loading tasks...</p>
      </div>
    );
  }

  const user = getCurrentUser();

  return (
    <div className="min-h-screen bg-gray-900 p-6">
      <header className="mb-6">
        <h1 className="text-2xl font-bold text-white">Dashboard</h1>
        {user && (
          <p className="text-sm text-gray-300">
            Organization: {user.org_id} | Role: {user.role}
          </p>
        )}
      </header>

      {error && <div className="p-2 mb-4 text-red-200 bg-red-900/50 rounded border border-red-700">{error}</div>}

      <div className="bg-gray-800 rounded-lg shadow-xl border border-gray-700 overflow-hidden">
        {tasks.length === 0 ? (
          <div className="p-8 text-center text-gray-400">No tasks yet</div>
        ) : (
          <ul className="divide-y divide-gray-700">
            {tasks.map((task) => (
              <li key={task.id} className="p-4 hover:bg-gray-700 transition-colors">
                <h3 className="font-medium text-white">{task.title}</h3>
                <p className="text-sm text-gray-300 mt-1">
                  Status: <span className="capitalize">{task.status}</span>
                  {task.due_date && <> • Due: {new Date(task.due_date).toLocaleDateString()}</>}
                </p>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
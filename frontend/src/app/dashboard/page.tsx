'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import { api } from '@/lib/api';
import { logout } from '@/lib/auth';
import { useAuth } from '@/hooks/useAuth';
import { Task } from '@/types';
import { useWebSocketTasks } from '@/hooks/useWebSocketTasks';
import TaskForm from '@/components/tasks/TaskForm';


export default function DashboardPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editingTask, setEditingTask] = useState<Task | null>(null);
  const [exporting, setExporting] = useState(false);
  const [loggingOut, setLoggingOut] = useState(false);
  const router = useRouter();
  const { user, loading: authLoading } = useAuth();

  // Fetch initial tasks
  const fetchTasks = useCallback(async () => {
    if (!user) {
      router.push('/auth/login');
      return;
    }

    try {
      const data = await api<Task[]>('/organizations/' + user.org_id + '/tasks', {
        method: 'GET',
      });
      setTasks(data);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : '';
      if (message.includes('Session expired') || message.includes('401') || message.includes('403')) {
        router.push('/auth/login');
      } else {
        setError('Failed to load tasks');
      }
    } finally {
      setLoading(false);
    }
  }, [router, user]);

  useEffect(() => {
    if (!authLoading) {
      fetchTasks();
    }
  }, [fetchTasks, authLoading]);

  // Real-time updates via WebSocket
  const handleTaskCreated = useCallback((task: Task) => {
    setTasks((prev) => {
      // Prevent duplicates - check if task already exists
      if (prev.some(t => t.id === task.id)) {
        return prev;
      }
      return [task, ...prev];
    });
  }, []);

  const handleTaskUpdated = useCallback((updatedTask: Task) => {
    setTasks((prev) => {
      // Only update if task exists in list
      const exists = prev.some(t => t.id === updatedTask.id);
      if (!exists) return prev;
      
      return prev.map((task) => (task.id === updatedTask.id ? updatedTask : task));
    });
  }, []);

  const handleTaskDeleted = useCallback((taskId: string) => {
    setTasks((prev) => prev.filter((task) => task.id !== taskId));
  }, []);
  
  // Subscribe to WebSocket updates (hooks must be called unconditionally)
  useWebSocketTasks(
    user?.org_id || '', 
    handleTaskCreated, 
    handleTaskUpdated, 
    handleTaskDeleted
  );

  // Handle export functionality
  const handleExport = async (taskId: string) => {
    setExporting(true);
    try {
      await api(`/tasks/${taskId}/export`, {
        method: 'POST',
      });
      alert('Export started. You will receive an email shortly.');
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      alert('Export failed: ' + message);
    } finally {
      setExporting(false);
    }
  };

  // Handle edit task
  const handleEdit = (task: Task) => {
    setEditingTask(task);
    setShowForm(true);
  };

  // Handle delete task
  const handleDelete = async (taskId: string) => {
    if (!window.confirm('Are you sure you want to delete this task?')) {
      return;
    }

    try {
      await api(`/tasks/${taskId}`, {
        method: 'DELETE',
      });
      // WebSocket will handle removing the task from the list
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Unknown error';
      alert('Failed to delete task: ' + message);
    }
  };

  // Handle logout
  const handleLogout = async () => {
    setLoggingOut(true);
    try {
      await logout();
      router.push('/auth/login');
    } catch (err: unknown) {
      console.error('Logout error:', err);
      // Still redirect even if logout fails
      router.push('/auth/login');
    }
  };

  if (authLoading || loading) {
    return (
      <div className="min-h-screen bg-gray-900 flex items-center justify-center">
        <p className="text-white">Loading tasks...</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-900 p-6">
      <header className="mb-6 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-white">Dashboard</h1>
          {user && (
            <p className="text-sm text-gray-300">
              Organization: {user.org_id} | Role: {user.role}
            </p>
          )}
        </div>
        <button
          onClick={handleLogout}
          disabled={loggingOut}
          className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer transition-colors"
        >
          {loggingOut ? 'Logging out...' : 'Logout'}
        </button>
      </header>

      {error && <div className="p-2 mb-4 text-red-200 bg-red-900/50 rounded border border-red-700">{error}</div>}

      {user && user.role === 'admin' && (
        <div className="flex justify-end items-center mb-4">
          <button
            onClick={() => setShowForm(true)}
            className="px-4 py-2 bg-emerald-600 text-white rounded hover:bg-emerald-700 cursor-pointer transition-colors"
          >
            + New Task
          </button>
        </div>
      )}

      <div className="bg-gray-800 rounded-lg shadow-xl border border-gray-700 overflow-hidden">
        {tasks.length === 0 ? (
          <div className="p-8 text-center text-gray-400">No tasks yet</div>
        ) : (
          <ul className="divide-y divide-gray-700">
            {tasks.map((task) => (
              <li key={task.id} className="p-4 hover:bg-gray-750 transition-colors">
                <div className="flex justify-between items-start">
                  <div className="flex-1">
                    <h3 className="font-semibold text-white text-lg">{task.title}</h3>
                    {task.description && (
                      <p className="text-sm text-gray-400 mt-1">{task.description}</p>
                    )}
                    <div className="flex items-center gap-3 mt-2 text-sm text-gray-300">
                      <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-900/50 text-blue-200 border border-blue-700">
                        {task.status.replace('_', ' ')}
                      </span>
                      {task.due_date && (
                        <span className="text-gray-400">
                          Due: {new Date(task.due_date).toLocaleDateString()}
                        </span>
                      )}
                    </div>
                  </div>
                  
                  <div className="flex items-center gap-2 ml-4">
                    {/* Export Button - Only for admins */}
                    {user && user.role === 'admin' && (
                      <button
                        onClick={() => handleExport(task.id)}
                        disabled={exporting}
                        className="px-3 py-1.5 bg-purple-600 text-white text-sm rounded hover:bg-purple-700 disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer transition-colors"
                        title="Export this task"
                      >
                        Export
                      </button>
                    )}
                    
                    {/* Edit Button - For all members */}
                    <button
                      onClick={() => handleEdit(task)}
                      className="px-3 py-1.5 bg-blue-600 text-white text-sm rounded hover:bg-blue-700 cursor-pointer transition-colors"
                      title="Edit task"
                    >
                      Edit
                    </button>
                    
                    {/* Delete Button - Only for admins */}
                    {user && user.role === 'admin' && (
                      <button
                        onClick={() => handleDelete(task.id)}
                        className="px-3 py-1.5 bg-red-600 text-white text-sm rounded hover:bg-red-700 cursor-pointer transition-colors"
                        title="Delete task"
                      >
                        Delete
                      </button>
                    )}
                  </div>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {showForm && user && (
        <TaskForm
          orgId={user.org_id}
          task={editingTask}
          onSubmit={() => {
            setShowForm(false);
            setEditingTask(null);
            // WebSocket will handle adding/updating the task in the list
          }}
          onCancel={() => {
            setShowForm(false);
            setEditingTask(null);
          }}
        />
      )}
    </div>
  );
}
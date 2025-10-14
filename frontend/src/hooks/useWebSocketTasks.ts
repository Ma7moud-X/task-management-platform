'use client';

import { useEffect, useCallback } from 'react';
import { wsManager } from '@/lib/websocket';
import { Task } from '@/types';

export function useWebSocketTasks(
  orgId: string,
  onTaskCreated: (task: Task) => void,
  onTaskUpdated: (task: Task) => void,
  onTaskDeleted: (taskId: string) => void
) {
  const handleMessage = useCallback(
    (event: 'created' | 'updated' | 'deleted', task: Task) => {
      if (task.org_id !== orgId) return; // safety

      switch (event) {
        case 'created':
          onTaskCreated(task);
          break;
        case 'updated':
          onTaskUpdated(task);
          break;
        case 'deleted':
          onTaskDeleted(task.id);
          break;
      }
    },
    [orgId, onTaskCreated, onTaskUpdated, onTaskDeleted]
  );

  useEffect(() => {
    if (!orgId) {
      // Don't connect if no orgId provided
      return;
    }
    
    wsManager.connect(orgId);
    const unsubscribe = wsManager.subscribe(handleMessage);

    return () => {
      unsubscribe();
      // Don't disconnect globally — other components might need it
    };
  }, [orgId, handleMessage]);
}
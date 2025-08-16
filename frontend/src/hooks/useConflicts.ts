import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listConflicts, resolveConflict, resolveAllConflicts, Conflict } from '../api/conflicts';

export function useConflicts() {
  return useQuery<Conflict[], Error>({
    queryKey: ['conflicts'],
    queryFn: () => listConflicts(),
  });
}

export function useResolveConflict() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ conflictId, action, note }: { conflictId: string; action: 'ignore' | 'supersede'; note?: string }) => 
      resolveConflict(conflictId, action, note),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['conflicts'] });
      qc.invalidateQueries({ queryKey: ['documents'] });
    },
  });
}

export function useResolveAllConflicts() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ action, note }: { action?: 'ignore' | 'supersede'; note?: string } = {}) => 
      resolveAllConflicts(action, note),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['conflicts'] });
      qc.invalidateQueries({ queryKey: ['documents'] });
    },
  });
}

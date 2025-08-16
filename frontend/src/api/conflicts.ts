import { api } from './client';

export interface Conflict {
  id: string;
  new_chunk_id: string;
  existing_chunk_id: string;
  label: string;
  score: number;
  judged_by: string;
  neighbor_sim: number;
  resolution_action: string | null;
  new_chunk_text: string;
  existing_chunk_text: string;
}

export async function listConflicts(): Promise<Conflict[]> {
  const res = await api.get('/conflicts');
  return res.data;
}

export async function resolveConflict(conflictId: string, action: 'ignore' | 'supersede', note?: string): Promise<any> {
  const res = await api.post(`/conflicts/${conflictId}/resolve`, null, {
    params: { action, note }
  });
  return res.data;
}

export async function resolveAllConflicts(action: 'ignore' | 'supersede' = 'supersede', note?: string): Promise<any> {
  const res = await api.post('/conflicts/resolve-all', null, {
    params: { action, note }
  });
  return res.data;
}

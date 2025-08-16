import { api } from './client';

export interface Tenant {
  id: string;
  name: string;
  slug: string;
  created_at: string;
  updated_at: string;
}

export interface CreateTenantInput {
  name: string;
  slug?: string;
  description?: string;
}

export async function listTenants(): Promise<Tenant[]> {
  const res = await api.get('/tenants');
  return res.data;
}

export async function createTenant(input: CreateTenantInput): Promise<Tenant> {
  const res = await api.post('/tenants', input);
  return res.data;
}

export async function getTenant(id: string): Promise<Tenant> {
  const res = await api.get(`/tenants/${id}`);
  return res.data;
}

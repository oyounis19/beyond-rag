import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { listTenants, createTenant, CreateTenantInput, Tenant } from '../api/tenants';

export function useTenants() {
  return useQuery<Tenant[], Error>({
    queryKey: ['tenants'],
    queryFn: listTenants,
  });
}

export function useCreateTenant() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateTenantInput) => createTenant(input),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['tenants'] });
    },
  });
}

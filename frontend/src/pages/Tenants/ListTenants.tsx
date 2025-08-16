import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTenants, useCreateTenant } from '../../hooks/useTenants';

export const ListTenants: React.FC = () => {
  const { data, isLoading, error } = useTenants();
  const create = useCreateTenant();
  const [open, setOpen] = useState(false);
  const [name, setName] = useState('');
  const [slug, setSlug] = useState('');
  const [desc, setDesc] = useState('');
  const nav = useNavigate();

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    create.mutate({ name, slug: slug || undefined, description: desc || undefined }, {
      onSuccess: () => {
        setName(''); setSlug(''); setDesc(''); setOpen(false);
      }
    });
  };

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-2xl font-semibold">Tenants</h1>
        <button onClick={() => setOpen(true)} className="px-3 py-2 bg-blue-600 text-white rounded text-sm">New Tenant</button>
      </div>
      {isLoading && <p>Loading...</p>}
      {error && <p className="text-red-600">Error: {error.message}</p>}
      <table className="min-w-full text-sm bg-white shadow rounded overflow-hidden">
        <thead className="bg-gray-100 text-gray-700">
          <tr>
            <th className="text-left p-2">Name</th>
            <th className="text-left p-2">Slug</th>
            <th className="text-left p-2">Created</th>
            <th className="text-left p-2"></th>
          </tr>
        </thead>
        <tbody>
          {data?.map(t => (
            <tr key={t.id} className="border-t hover:bg-gray-50">
              <td className="p-2 font-medium">{t.name}</td>
              <td className="p-2 text-gray-500">{t.slug}</td>
              <td className="p-2 text-gray-500">{new Date(t.created_at).toLocaleString()}</td>
              <td className="p-2 text-right">
                <button onClick={() => nav(`/tenants/${t.id}`)} className="text-blue-600 hover:underline">Open</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {open && (
        <div className="fixed inset-0 bg-black/30 flex items-start justify-center pt-24">
          <form onSubmit={submit} className="bg-white rounded shadow p-6 w-full max-w-md space-y-4">
            <h2 className="text-lg font-semibold">Create Tenant</h2>
            <div>
              <label className="block text-sm font-medium mb-1">Name</label>
              <input value={name} onChange={e => setName(e.target.value)} required className="w-full border rounded px-2 py-1" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Slug (optional)</label>
              <input value={slug} onChange={e => setSlug(e.target.value)} className="w-full border rounded px-2 py-1" />
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">Description (optional)</label>
              <textarea value={desc} onChange={e => setDesc(e.target.value)} className="w-full border rounded px-2 py-1" rows={3} />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button type="button" onClick={() => setOpen(false)} className="px-3 py-1.5 rounded border">Cancel</button>
              <button type="submit" disabled={create.isPending} className="px-3 py-1.5 bg-blue-600 text-white rounded disabled:opacity-50">{create.isPending ? 'Creating...' : 'Create'}</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
};

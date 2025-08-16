import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { getTenant, Tenant } from '../../api/tenants';

export const TenantDetail: React.FC = () => {
  const { id } = useParams();
  const [tenant, setTenant] = useState<Tenant | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    getTenant(id)
      .then(t => setTenant(t))
      .catch(e => setError(e.message || 'Error'))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) return <p>Loading...</p>;
  if (error) return <p className="text-red-600">{error}</p>;
  if (!tenant) return <p>Not found</p>;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Tenant: {tenant.name}</h1>
        <Link to="/tenants" className="text-blue-600 hover:underline text-sm">Back</Link>
      </div>

      <div className="bg-white shadow rounded p-4 space-y-2 text-sm">
        <div><span className="font-medium">ID:</span> {tenant.id}</div>
        <div><span className="font-medium">Slug:</span> {tenant.slug}</div>
        <div><span className="font-medium">Created:</span> {new Date(tenant.created_at).toLocaleString()}</div>
        <div><span className="font-medium">Updated:</span> {new Date(tenant.updated_at).toLocaleString()}</div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="bg-white shadow rounded p-4">
          <h2 className="font-semibold mb-2">Documents</h2>
          <p className="text-xs text-gray-500 mb-3">Upload, version, and publish your knowledge base.</p>
          <Link 
            to={`/tenants/${tenant.id}/documents`}
            className="inline-block px-3 py-1.5 bg-blue-600 text-white rounded text-sm hover:bg-blue-700"
          >
            Manage Documents
          </Link>
        </div>
        <div className="bg-white shadow rounded p-4">
          <h2 className="font-semibold mb-2">Conflicts</h2>
          <p className="text-xs text-gray-500">Coming soon: detected contradictions & resolution workflow.</p>
        </div>
        <div className="bg-white shadow rounded p-4">
          <h2 className="font-semibold mb-2">Chat</h2>
            <p className="text-xs text-gray-500">Coming soon: chat sessions with retrieval & citations.</p>
        </div>
        <div className="bg-white shadow rounded p-4">
          <h2 className="font-semibold mb-2">Evaluations</h2>
          <p className="text-xs text-gray-500">Coming soon: test suites & metrics.</p>
        </div>
      </div>
    </div>
  );
};

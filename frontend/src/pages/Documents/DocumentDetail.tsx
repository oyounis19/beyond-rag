import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { useDocumentStatus } from '../../hooks/useDocuments';

export const DocumentDetail: React.FC = () => {
  const { tenantId, documentId } = useParams();
  const { data: status, isLoading, error } = useDocumentStatus(tenantId!, documentId!);

  if (!tenantId || !documentId) return <p className="text-red-600">Missing route params.</p>;
  if (isLoading) return <p>Loading document details...</p>;
  if (error) return <p className="text-red-600">Error: {(error as any).message}</p>;
  if (!status) return <p>Document not found</p>;

  const { document, total_chunks, total_conflicts, total_dedup_groups } = status as any;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Document: {document.name}</h1>
        <Link to={`/tenants/${tenantId}/documents`} className="text-blue-600 hover:underline text-sm">Back to Documents</Link>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <div className="bg-white shadow rounded p-4 space-y-3">
          <h2 className="font-semibold">Document Info</h2>
          <div className="text-sm space-y-2">
            <div><span className="font-medium">ID:</span> {document.id}</div>
            <div><span className="font-medium">Name:</span> {document.name}</div>
            <div>
              <span className="font-medium">Status:</span>{' '}
              <span className={`px-2 py-1 rounded text-xs ${
                document.status === 'published' ? 'bg-green-100 text-green-800' :
                document.status === 'draft' ? 'bg-yellow-100 text-yellow-800' :
                'bg-gray-100 text-gray-800'
              }`}>
                {document.status || 'n/a'}
              </span>
            </div>
            <div><span className="font-medium">Created:</span> {document.created_at ? new Date(document.created_at).toLocaleString() : 'n/a'}</div>
            {document.file_hash && (
              <div><span className="font-medium">Hash:</span> <code className="text-xs bg-gray-100 px-1 rounded">{document.file_hash.slice(0,16)}...</code></div>
            )}
            {document.effective_at && (
              <div><span className="font-medium">Published:</span> {new Date(document.effective_at).toLocaleString()}</div>
            )}
          </div>
        </div>

        <div className="bg-white shadow rounded p-4 space-y-3">
          <h2 className="font-semibold">Content Stats</h2>
          <div className="text-sm space-y-2">
            <div><span className="font-medium">Total Chunks:</span> {total_chunks}</div>
            <div><span className="font-medium">Conflicts Detected:</span> {total_conflicts}</div>
            <div><span className="font-medium">Dedup Groups:</span> {total_dedup_groups}</div>
          </div>
        </div>

        <div className="bg-white shadow rounded p-4 space-y-3">
          <h2 className="font-semibold">Actions</h2>
          <div className="space-y-2">
            <button className="block w-full text-left px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded text-sm" disabled>
              View Chunks (Coming Soon)
            </button>
            <button className="block w-full text-left px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded text-sm" disabled>
              View Conflicts (Coming Soon)
            </button>
            <button className="block w-full text-left px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded text-sm" disabled>
              Re-process Document (Coming Soon)
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};

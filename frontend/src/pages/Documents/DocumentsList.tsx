import React, { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useDocuments, useUploadDocument, usePublishDocument } from '../../hooks/useDocuments';
import { __API_BASE__ } from '../../api/client';

export const DocumentsList: React.FC = () => {
  const params = useParams();
  const tenantId = params.tenantId || params.id; // fallback if route param name mismatch
  const docsQuery = useDocuments(tenantId || '');
  const { data: documents, isLoading, error, status, refetch, fetchStatus } = docsQuery as any;
  const upload = useUploadDocument(tenantId || '');
  const publish = usePublishDocument(tenantId || '');
  const [dragOver, setDragOver] = useState(false);

  const handleFileSelect = (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const file = files[0];
    upload.mutate(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    handleFileSelect(e.dataTransfer.files);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(true);
  };

  const handleDragLeave = () => {
    setDragOver(false);
  };

  if (!tenantId) return <p className="text-red-600 text-sm">No tenant id in route.</p>;
  if (isLoading || fetchStatus === 'fetching') {
    return <div className="space-y-3 text-sm">
      <p>Loading documents... (react-query status: {status} fetchStatus: {fetchStatus})</p>
      <p>API Base: {__API_BASE__}</p>
      <button onClick={() => refetch()} className="px-2 py-1 border rounded">Retry</button>
    </div>;
  }
  if (error) return <p className="text-red-600">Error: {(error as any).message}</p>;
  if ((status === 'success') && fetchStatus === 'fetching' && !documents) {
    return <div className="space-y-3 text-sm">
      <p>Still fetching documents after success flag (likely retry loop / network). Tenant: {tenantId}</p>
      <p>Open dev tools Network tab, look for GET /tenants/{tenantId}/documents errors.</p>
      <button onClick={() => refetch()} className="px-2 py-1 border rounded">Force Refetch</button>
    </div>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold">Documents</h1>
        <Link to={`/tenants/${tenantId}`} className="text-blue-600 hover:underline text-sm">Back to Tenant</Link>
      </div>

      {/* Upload Zone */}
      <div
        className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors ${
          dragOver ? 'border-blue-500 bg-blue-50' : 'border-gray-300'
        }`}
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
      >
        <div className="space-y-3">
          <div className="text-gray-600">
            {upload.isPending ? 'Uploading...' : 'Drag & drop files here or click to select'}
          </div>
          <input
            type="file"
            onChange={(e) => handleFileSelect(e.target.files)}
            className="hidden"
            id="file-input"
            disabled={upload.isPending}
            accept=".txt,.md,.pdf"
          />
          <label
            htmlFor="file-input"
            className="inline-block px-4 py-2 bg-blue-600 text-white rounded cursor-pointer hover:bg-blue-700 disabled:opacity-50"
          >
            Select Files
          </label>
          <div className="text-xs text-gray-500">Supported: .txt, .md, .pdf</div>
        </div>
      </div>

      {/* Documents Table */}
      <div className="bg-white shadow rounded overflow-hidden">
        <table className="min-w-full text-sm">
          <thead className="bg-gray-100 text-gray-700">
            <tr>
              <th className="text-left p-3">Name</th>
              <th className="text-left p-3">Status</th>
              <th className="text-left p-3">Created</th>
              <th className="text-left p-3">Actions</th>
            </tr>
          </thead>
          <tbody>
            {documents?.map(doc => (
              <tr key={doc.id} className="border-t hover:bg-gray-50">
                <td className="p-3 font-medium">{doc.name}</td>
                <td className="p-3">
                  <span className={`px-2 py-1 rounded text-xs ${
                    doc.status === 'published' ? 'bg-green-100 text-green-800' :
                    doc.status === 'draft' ? 'bg-yellow-100 text-yellow-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {doc.status}
                  </span>
                </td>
                <td className="p-3 text-gray-500">{new Date(doc.created_at).toLocaleString()}</td>
                <td className="p-3 space-x-2">
                  {doc.status === 'draft' && (
                    <button
                      onClick={() => publish.mutate(doc.id)}
                      disabled={publish.isPending}
                      className="text-blue-600 hover:underline disabled:opacity-50"
                    >
                      Publish
                    </button>
                  )}
                  <Link
                    to={`/tenants/${tenantId}/documents/${doc.id}`}
                    className="text-blue-600 hover:underline"
                  >
                    Details
                  </Link>
                </td>
              </tr>
            ))}
            {(!documents || documents.length === 0) && (
              <tr>
                <td colSpan={4} className="p-8 text-center text-gray-500">
                  No documents yet. Upload your first document above.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};

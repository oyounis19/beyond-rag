import React, { useState, useRef } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useDocuments } from '../hooks/useDocuments';
import { publishDocument, deleteDocument, pollDocumentStatus, publishDocumentStream, PublishEvent } from '../api/documents';
import { Document } from '../api/documents';

export const DocumentList: React.FC = () => {
  const { data: documents = [], isLoading } = useDocuments();
  const [publishingIds, setPublishingIds] = useState<Set<string>>(new Set());
  const [deletingIds, setDeletingIds] = useState<Set<string>>(new Set());
  const [processingStatus, setProcessingStatus] = useState<Record<string, { message: string; progress?: number; detail?: string }>>({});
  const [useDocling, setUseDocling] = useState(false);
  const queryClient = useQueryClient();
  const publishCleanupRefs = useRef<Record<string, () => void>>({});

  const handlePublish = async (documentId: string) => {
    setPublishingIds(prev => new Set([...prev, documentId]));
    setProcessingStatus(prev => ({ 
      ...prev, 
      [documentId]: { message: 'Connecting...', progress: 0 } 
    }));
    
    // Clean up any existing stream for this document
    if (publishCleanupRefs.current[documentId]) {
      publishCleanupRefs.current[documentId]();
      delete publishCleanupRefs.current[documentId];
    }
    
    const cleanup = publishDocumentStream(
      documentId,
      useDocling,
      (event: PublishEvent) => {
        // Handle streaming events
        const status = { 
          message: event.message || getStageMessage(event.stage),
          progress: event.progress,
          detail: getEventDetail(event)
        };
        
        setProcessingStatus(prev => ({ ...prev, [documentId]: status }));
        
        // Handle completion events
        if (event.stage === 'complete' && event.published) {
          setTimeout(() => {
            setPublishingIds(prev => {
              const next = new Set(prev);
              next.delete(documentId);
              return next;
            });
            setProcessingStatus(prev => {
              const next = { ...prev };
              delete next[documentId];
              return next;
            });
            queryClient.invalidateQueries({ queryKey: ['documents'] });
          }, 1000);
        } else if (event.stage === 'conflicts_detected' && event.requires_review) {
          setTimeout(() => {
            setPublishingIds(prev => {
              const next = new Set(prev);
              next.delete(documentId);
              return next;
            });
            setProcessingStatus(prev => {
              const next = { ...prev };
              delete next[documentId];
              return next;
            });
            queryClient.invalidateQueries({ queryKey: ['documents'] });
            queryClient.invalidateQueries({ queryKey: ['conflicts'] });
            
            // Show conflict detection message
            // alert('✅ Document processed successfully!\n⚠️ Conflicts detected with existing content.\n\nPlease review and resolve the conflicts below before the document can be published.');
          }, 1500);
        }
      },
      (error: string) => {
        console.error('Publishing error:', error);
        setProcessingStatus(prev => ({ 
          ...prev, 
          [documentId]: { message: `Error: ${error}`, progress: 0 } 
        }));
        
        setTimeout(() => {
          setPublishingIds(prev => {
            const next = new Set(prev);
            next.delete(documentId);
            return next;
          });
          setProcessingStatus(prev => {
            const next = { ...prev };
            delete next[documentId];
            return next;
          });
        }, 3000);
      },
      () => {
        // Cleanup
        delete publishCleanupRefs.current[documentId];
      }
    );
    
    publishCleanupRefs.current[documentId] = cleanup;
  };

  const getStageMessage = (stage: string): string => {
    switch (stage) {
      case 'parsing': return 'Parsing document...';
      case 'parsed': return 'Document parsed';
      case 'chunking': return 'Splitting into chunks...';
      case 'chunked': return 'Chunks created';
      case 'embedding': return 'Generating embeddings...';
      case 'embedded': return 'Embeddings generated';
      case 'analyzing': return 'Analyzing conflicts...';
      case 'conflicts_detected': return 'Conflicts detected';
      case 'publishing': return 'Publishing...';
      case 'complete': return 'Complete!';
      case 'error': return 'Error occurred';
      default: return 'Processing...';
    }
  };

  const getEventDetail = (event: PublishEvent): string | undefined => {
    const details = [];
    
    if (event.chunks_created) details.push(`${event.chunks_created} chunks`);
    if (event.chunks_embedded) details.push(`${event.chunks_embedded} embedded`);
    if (event.chunks_processed && event.total_chunks) {
      details.push(`${event.chunks_processed}/${event.total_chunks} analyzed`);
    }
    if (event.estimated_time) details.push(event.estimated_time);
    if (event.duplicates_count || event.contradictions_count) {
      const conflicts = [];
      if (event.duplicates_count) conflicts.push(`${event.duplicates_count} duplicates`);
      if (event.contradictions_count) conflicts.push(`${event.contradictions_count} contradictions`);
      details.push(conflicts.join(', '));
    }
    
    return details.length > 0 ? details.join(' • ') : undefined;
  };

  const handleDelete = async (documentId: string, documentName: string) => {
    if (!confirm(`Are you sure you want to delete "${documentName}"? This action cannot be undone.`)) {
      return;
    }

    setDeletingIds(prev => new Set([...prev, documentId]));
    try {
      await deleteDocument(documentId);
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      queryClient.invalidateQueries({ queryKey: ['conflicts'] });
    } catch (error) {
      console.error('Delete error:', error);
      alert('Failed to delete document');
    } finally {
      setDeletingIds(prev => {
        const next = new Set(prev);
        next.delete(documentId);
        return next;
      });
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'published': return 'bg-green-100 text-green-800';
      case 'draft': return 'bg-gray-100 text-gray-800';
      case 'processing': return 'bg-blue-100 text-blue-800';
      case 'pending_review': return 'bg-yellow-100 text-yellow-800';
      case 'error': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'published': return '✅';
      case 'draft': return '📝';
      case 'processing': return '⏳';
      case 'pending_review': return '⚠️';
      case 'error': return '❌';
      default: return '📄';
    }
  };

  const getDisplayStatus = (doc: Document) => {
    if (publishingIds.has(doc.id)) {
      return 'processing';
    }
    return doc.status;
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex items-center justify-center py-8">
          <div className="w-6 h-6 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
          <span className="ml-2 text-gray-600">Loading documents...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-900">
          Documents ({documents.length})
        </h2>
        
        {documents.length > 0 && (
          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <label className="flex items-center space-x-2 text-sm text-gray-600">
                  <input
                    type="checkbox"
                    checked={useDocling}
                    onChange={(e) => setUseDocling(e.target.checked)}
                    className="rounded"
                  />
                  <span>Use Docling parser</span>
                </label>
              </div>
            </div>
          </div>
        )}
      </div>

      {documents.length === 0 ? (
        <div className="text-center py-8">
          <div className="text-4xl text-gray-400 mb-2">📁</div>
          <p className="text-gray-500">No documents uploaded yet</p>
          <p className="text-sm text-gray-400 mt-1">
            Upload your first document to get started
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {documents.map((doc: Document) => (
            <div
              key={doc.id}
              className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:bg-gray-50"
            >
              <div className="flex items-center space-x-3 flex-1">
                <div className="text-xl">
                  {getStatusIcon(getDisplayStatus(doc))}
                </div>
                
                <div className="flex-1 min-w-0">
                  <h3 className="text-sm font-medium text-gray-900 truncate">
                    {doc.name}
                  </h3>
                  <p className="text-xs text-gray-500">
                    Uploaded {new Date(doc.created_at).toLocaleDateString()}
                    {processingStatus[doc.id] && (
                      <span className="ml-2 text-blue-600 font-medium">
                        • {processingStatus[doc.id].message}
                        {processingStatus[doc.id].progress !== undefined && (
                          <span className="ml-1">({processingStatus[doc.id].progress?.toFixed(0)}%)</span>
                        )}
                        {processingStatus[doc.id].detail && (
                          <span className="block text-xs text-gray-500 mt-0.5">{processingStatus[doc.id].detail}</span>
                        )}
                      </span>
                    )}
                  </p>
                </div>

                <div className="flex items-center space-x-2">
                  <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${getStatusColor(getDisplayStatus(doc))}`}>
                    {getDisplayStatus(doc).replace('_', ' ')}
                  </span>
                </div>
              </div>

              <div className="flex items-center space-x-2 ml-4">
                {/* Publish button for draft documents */}
                {doc.status === 'draft' && (
                  <button
                    onClick={() => handlePublish(doc.id)}
                    disabled={publishingIds.has(doc.id) || deletingIds.has(doc.id)}
                    className="px-3 py-1 bg-blue-600 text-white text-xs rounded-md hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {publishingIds.has(doc.id) ? (
                      <div className="flex items-center space-x-2">
                        <div className="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin"></div>
                        <div className="flex flex-col">
                          <span className="text-xs">{processingStatus[doc.id]?.message || 'Publishing...'}</span>
                          {processingStatus[doc.id]?.progress !== undefined && (
                            <div className="w-16 bg-blue-200 rounded-full h-1 mt-1">
                              <div 
                                className="bg-white h-1 rounded-full transition-all duration-300" 
                                style={{ width: `${processingStatus[doc.id]?.progress || 0}%` }}
                              ></div>
                            </div>
                          )}
                        </div>
                      </div>
                    ) : (
                      '🚀 Publish'
                    )}
                  </button>
                )}

                {/* Status for pending review documents */}
                {doc.status === 'pending_review' && (
                  <div className="text-xs text-yellow-600 font-medium">
                    ⚠️ Conflicts found - resolve below
                  </div>
                )}
                
                {/* Status for published documents */}
                {doc.status === 'published' && (
                  <div className="text-xs text-green-600 font-medium">
                    ✓ Ready for chat
                  </div>
                )}

                {/* Delete button - always available */}
                <button
                  onClick={() => handleDelete(doc.id, doc.name)}
                  disabled={deletingIds.has(doc.id) || publishingIds.has(doc.id)}
                  className="px-2 py-1 bg-red-500 text-white text-xs rounded-md hover:bg-red-600 disabled:opacity-50 disabled:cursor-not-allowed"
                  title="Delete document"
                >
                  {deletingIds.has(doc.id) ? (
                    <div className="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin"></div>
                  ) : (
                    '🗑️'
                  )}
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

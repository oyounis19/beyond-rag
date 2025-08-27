import React, { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { useConflicts } from '../hooks/useConflicts';
import { resolveAllConflicts, resolveConflict } from '../api/conflicts';

export const ConflictResolution: React.FC = () => {
  const { data: conflicts = [], isLoading } = useConflicts();
  const [resolvingAll, setResolvingAll] = useState(false);
  const [resolvingIds, setResolvingIds] = useState<Set<string>>(new Set());
  const queryClient = useQueryClient();

  const handleResolveAll = async () => {
    setResolvingAll(true);
    try {
      await resolveAllConflicts('supersede');
      queryClient.invalidateQueries({ queryKey: ['conflicts'] });
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    } catch (error) {
      console.error('Bulk resolve error:', error);
      alert('Failed to resolve conflicts');
    } finally {
      setResolvingAll(false);
    }
  };

  const handleResolveSingle = async (conflictId: string, action: 'ignore' | 'supersede') => {
    setResolvingIds(prev => new Set([...prev, conflictId]));
    try {
      await resolveConflict(conflictId, action);
      queryClient.invalidateQueries({ queryKey: ['conflicts'] });
      queryClient.invalidateQueries({ queryKey: ['documents'] });
    } catch (error) {
      console.error('Resolve error:', error);
      alert('Failed to resolve conflict');
    } finally {
      setResolvingIds(prev => {
        const next = new Set(prev);
        next.delete(conflictId);
        return next;
      });
    }
  };

  if (isLoading) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="flex items-center justify-center py-4">
          <div className="w-5 h-5 border-2 border-yellow-600 border-t-transparent rounded-full animate-spin"></div>
          <span className="ml-2 text-gray-600">Checking for conflicts...</span>
        </div>
      </div>
    );
  }

  if (conflicts.length === 0) {
    return null;
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-3">
          <div className="text-xl">⚠️</div>
          <div>
            <h2 className="text-lg font-semibold text-gray-900">
              Content Conflicts ({conflicts.length})
            </h2>
            <p className="text-sm text-gray-600">
              New content contradicts existing documents
            </p>
          </div>
        </div>

                  <button
            onClick={handleResolveAll}
            disabled={resolvingAll || conflicts.length === 0}
            className="px-4 py-2 bg-green-600 text-white text-sm font-medium rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {resolvingAll ? (
              <div className="flex items-center space-x-2">
                <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                <span>Resolving All...</span>
              </div>
            ) : (
              <>🔄 Apply New Changes to All ({conflicts.length})</>
            )}
          </button>
      </div>

      <div className="space-y-4">
        {conflicts.map((conflict) => (
          <div
            key={conflict.id}
            className="border border-yellow-200 rounded-lg p-4 bg-yellow-50"
          >
            <div className="flex items-start justify-between mb-3">
              <div className="flex-1">
                <h3 className="text-sm font-medium text-gray-900 mb-1 uppercase">
                  {conflict.label}
                </h3>
                <div className="text-xs text-gray-600 space-y-1">
                  <p><strong>Conflict ID:</strong> {conflict.id}</p>
                  <p><strong>New Chunk:</strong> {conflict.new_chunk_id}</p>
                  <p><strong>Existing Chunk:</strong> {conflict.existing_chunk_id}</p>
                  <p><strong>Judged By:</strong> <span className="uppercase font-medium text-blue-600">{conflict.judged_by || 'unknown'}</span></p>
                  <p><strong>Similarity Score:</strong> {(conflict.score * 100).toFixed(1)}%</p>
                  {conflict.neighbor_sim && (
                    <p><strong>Neighbor Similarity:</strong> {(conflict.neighbor_sim * 100).toFixed(1)}%</p>
                  )}
                </div>
              </div>

              <div className="flex space-x-2">
                <button
                  onClick={() => handleResolveSingle(conflict.id, 'supersede')}
                  disabled={resolvingIds.has(conflict.id)}
                  className="px-3 py-1 bg-green-600 text-white text-xs font-medium rounded-md hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {resolvingIds.has(conflict.id) ? (
                    <div className="flex items-center space-x-1">
                      <div className="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin"></div>
                      <span>Resolving...</span>
                    </div>
                  ) : (
                    '✅ Apply New'
                  )}
                </button>
                
                <button
                  onClick={() => handleResolveSingle(conflict.id, 'ignore')}
                  disabled={resolvingIds.has(conflict.id)}
                  className="px-3 py-1 bg-red-600 text-white text-xs font-medium rounded-md hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {resolvingIds.has(conflict.id) ? (
                    <div className="flex items-center space-x-1">
                      <div className="w-3 h-3 border border-white border-t-transparent rounded-full animate-spin"></div>
                      <span>Resolving...</span>
                    </div>
                  ) : (
                    '❌ Discard New'
                  )}
                </button>
              </div>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="border border-red-200 rounded p-3 bg-red-50">
                <h4 className="text-xs font-medium text-red-800 mb-2">
                  📄 Existing Content
                </h4>
                <p className="text-xs text-red-700 leading-relaxed">
                  {conflict.existing_chunk_text || 'Content not available'}
                </p>
              </div>

              <div className="border border-green-200 rounded p-3 bg-green-50">
                <h4 className="text-xs font-medium text-green-800 mb-2">
                  ✨ New Content
                </h4>
                <p className="text-xs text-green-700 leading-relaxed">
                  {conflict.new_chunk_text || 'Content not available'}
                </p>
              </div>
            </div>

            <div className="mt-3 text-xs text-gray-500">
              <strong>Actions:</strong> 
              <span className="text-green-600 ml-1">Apply New</span> replaces existing content with new content.
              <span className="text-red-600 ml-2">Discard New</span> keeps existing content and removes new content.
            </div>
          </div>
        ))}
      </div>

      <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
        <div className="flex items-start space-x-2">
          <div className="text-blue-600 mt-0.5">💡</div>
          <div className="text-xs text-blue-800">
            <p><strong>About Conflict Detection:</strong></p>
            <p className="mt-1">
              Our AI analyzes semantic similarity and detects contradictions between new and existing content.
              Conflicts with similarity above 85% indicate potentially contradictory information that needs review.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

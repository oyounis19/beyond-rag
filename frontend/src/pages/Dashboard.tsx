import React, { useState } from 'react';
import { DocumentUpload } from '../components/DocumentUpload';
import { DocumentList } from '../components/DocumentList';
import { ConflictResolution } from '../components/ConflictResolution';
import { ChatInterface } from '../components/ChatInterface';
import { useDocuments } from '../hooks/useDocuments';
import { useConflicts } from '../hooks/useConflicts';

export const Dashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'documents' | 'chat'>('documents');
  const { data: documents = [] } = useDocuments();
  const { data: conflicts = [] } = useConflicts();
  
  const hasPublishedDocuments = documents.some(doc => doc.status === 'published');
  const hasUnresolvedConflicts = conflicts.length > 0;

  const tabs = [
    { 
      id: 'documents' as const, 
      name: 'Documents', 
      icon: '📄',
      badge: hasUnresolvedConflicts ? conflicts.length : undefined
    },
    { 
      id: 'chat' as const, 
      name: 'Chat', 
      icon: '💬', 
      disabled: !hasPublishedDocuments,
      tooltip: hasPublishedDocuments ? undefined : 'Upload and publish documents to start chatting'
    },
  ];

  return (
    <div className="max-w-7xl mx-auto px-6 py-6">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Document Intelligence Hub
        </h1>
        <p className="text-gray-600">
          Upload → Publish → Resolve conflicts → Chat with your knowledge base
        </p>
      </div>

      {/* Status Banner */}
      {hasUnresolvedConflicts && (
        <div className="mb-6 bg-yellow-50 border border-yellow-200 rounded-lg p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="text-yellow-600">⚠️</div>
              <div>
                <h3 className="text-sm font-medium text-yellow-800">
                  {conflicts.length} conflict{conflicts.length !== 1 ? 's' : ''} need{conflicts.length === 1 ? 's' : ''} resolution
                </h3>
                <p className="text-sm text-yellow-700">
                  Documents were processed and found contradictions with existing content. Review and resolve them to maintain consistency.
                </p>
              </div>
            </div>
            <button
              onClick={() => setActiveTab('documents')}
              className="px-3 py-1 bg-yellow-600 text-white text-sm rounded-md hover:bg-yellow-700"
            >
              View Conflicts
            </button>
          </div>
        </div>
      )}

      {/* Tab Navigation */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => !tab.disabled && setActiveTab(tab.id)}
              disabled={tab.disabled}
              title={tab.tooltip}
              className={`
                flex items-center space-x-2 py-2 px-1 border-b-2 font-medium text-sm transition-colors relative
                ${activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : tab.disabled
                  ? 'border-transparent text-gray-400 cursor-not-allowed'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }
              `}
            >
              <span>{tab.icon}</span>
              <span>{tab.name}</span>
              {tab.badge && (
                <span className="bg-red-500 text-white text-xs px-1.5 py-0.5 rounded-full min-w-[1.25rem] text-center">
                  {tab.badge}
                </span>
              )}
              {tab.disabled && (
                <span className="text-xs bg-gray-100 text-gray-600 px-2 py-0.5 rounded">
                  Disabled
                </span>
              )}
            </button>
          ))}
        </nav>
      </div>

      {/* Content */}
      <div className="space-y-6">
        {activeTab === 'documents' && (
          <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
            {/* Upload Section */}
            <div className="xl:col-span-1">
              <DocumentUpload />
            </div>
            
            {/* Documents and Conflicts */}
            <div className="xl:col-span-2 space-y-6">
              <DocumentList />
              {hasUnresolvedConflicts && <ConflictResolution />}
            </div>
          </div>
        )}
        
        {activeTab === 'chat' && (
          <ChatInterface />
        )}
      </div>
    </div>
  );
};

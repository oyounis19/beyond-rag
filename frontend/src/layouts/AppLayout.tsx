import { Link, Outlet } from 'react-router-dom';
import React from 'react';

export const AppLayout: React.FC = () => {
  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white shadow-sm border-b">
        <div className="mx-auto max-w-7xl px-6 py-4">
          <div className="flex items-center justify-between">
            <Link to="/" className="flex items-center space-x-3">
              <div className="h-8 w-8 bg-gradient-to-br from-blue-600 to-indigo-700 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-sm">BR</span>
              </div>
              <span className="text-xl font-semibold text-gray-900">Beyond RAG</span>
            </Link>
            <div className="flex items-center space-x-4 text-sm text-gray-600">
              <a 
                href="http://localhost:3000" 
                target="_blank" 
                rel="noopener noreferrer"
                className="flex items-center space-x-1 hover:text-blue-600 transition-colors"
              >
                <span>📊</span>
                <span>Langfuse</span>
              </a>
              <a 
                href="http://localhost:8000/docs" 
                target="_blank" 
                rel="noopener noreferrer"
                className="flex items-center space-x-1 hover:text-blue-600 transition-colors"
              >
                <span>📚</span>
                <span>API Docs</span>
              </a>
            </div>
          </div>
        </div>
      </header>
      
      <main className="flex-1">
        <Outlet />
      </main>
      
      <footer className="bg-white border-t">
        <div className="mx-auto max-w-7xl px-6 py-4">
          <div className="text-center text-sm text-gray-500">
            Beyond RAG - Intelligent Document Management with Conflict Detection
          </div>
        </div>
      </footer>
    </div>
  );
};

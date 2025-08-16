import React, { useState, useCallback } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { uploadDocument } from '../api/documents';

export const DocumentUpload: React.FC = () => {
  const [isUploading, setIsUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const queryClient = useQueryClient();

  const handleUpload = async (files: FileList) => {
    if (files.length === 0) return;
    
    setIsUploading(true);
    try {
      let uploadedCount = 0;
      
      // Upload files one by one (since the API expects single file uploads)
      for (let i = 0; i < files.length; i++) {
        const file = files[i];
        await uploadDocument(file);
        uploadedCount++;
      }
      
      // Refresh documents list
      queryClient.invalidateQueries({ queryKey: ['documents'] });
      
      // alert(`Successfully uploaded ${uploadedCount} file(s). Use the "Publish" button to process them.`);
    } catch (error) {
      console.error('Upload error:', error);
      alert('Upload failed. Please try again.');
    } finally {
      setIsUploading(false);
    }
  };

  const handleDrag = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleUpload(e.dataTransfer.files);
    }
  }, []);

  const handleFileInput = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      handleUpload(e.target.files);
    }
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">
        Upload Documents
      </h2>
      
      <div
        className={`
          relative border-2 border-dashed rounded-lg p-8 text-center transition-colors
          ${dragActive 
            ? 'border-blue-400 bg-blue-50' 
            : 'border-gray-300 hover:border-gray-400'
          }
          ${isUploading ? 'opacity-50 pointer-events-none' : ''}
        `}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input
          type="file"
          multiple
          onChange={handleFileInput}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          disabled={isUploading}
          accept=".pdf,.doc,.docx,.txt,.md"
        />
        
        <div className="space-y-3">
          <div className="text-4xl text-gray-400">
            {isUploading ? '⏳' : '📁'}
          </div>
          
          <div>
            <p className="text-sm font-medium text-gray-900">
              {isUploading ? 'Processing...' : 'Drop files here or click to browse'}
            </p>
            <p className="text-xs text-gray-500 mt-1">
              Supports PDF, Word, Text, and Markdown files
            </p>
          </div>
          
          {isUploading ? (
            <div className="flex items-center justify-center space-x-2">
              <div className="w-4 h-4 border-2 border-blue-600 border-t-transparent rounded-full animate-spin"></div>
              <span className="text-sm text-blue-600">Uploading and validating files...</span>
            </div>
          ) : (
            <p className="text-xs text-gray-500 mt-1">
              Files are uploaded and stored securely, then published for processing
            </p>
          )}
        </div>
      </div>
      
      <div className="mt-4 text-xs text-gray-500">
        <p><strong>Two-Step Process:</strong></p>
        <div className="mt-1 flex items-center space-x-2">
          <span>� Upload</span>
          <span>→</span>
          <span>🔍 Validate & Store</span>
          <span>→</span>
          <span>� Draft Status</span>
          <span>→</span>
          <span>🚀 Publish to Process</span>
        </div>
      </div>
    </div>
  );
};

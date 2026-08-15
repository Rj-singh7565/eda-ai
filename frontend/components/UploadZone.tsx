'use client';

import React, { useRef } from 'react';

interface UploadZoneProps {
  onUpload: (file: File) => void;
  isUploading: boolean;
}

export default function UploadZone({ onUpload, isUploading }: UploadZoneProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      onUpload(e.target.files[0]);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      onUpload(e.dataTransfer.files[0]);
    }
  };

  return (
    <div
      onDragOver={(e) => e.preventDefault()}
      onDrop={handleDrop}
      onClick={() => fileInputRef.current?.click()}
      style={{
        border: '2px dashed var(--border-color)',
        borderRadius: '12px',
        padding: '16px',
        textAlign: 'center',
        cursor: 'pointer',
        backgroundColor: 'var(--bg-app)',
        transition: 'border-color 0.2s ease'
      }}
    >
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        hidden
        accept=".pdf,.docx,.pptx,.xlsx,.csv,.txt,.md,.png,.jpg,.jpeg,.zip"
      />
      <div style={{ fontSize: '1.2rem', marginBottom: '4px' }}>📁</div>
      <p style={{ fontSize: '0.85rem', fontWeight: 500 }}>
        {isUploading ? 'Uploading & validating...' : 'Drag & drop files here, or browse'}
      </p>
      <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: '4px' }}>
        PDF, DOCX, PPTX, Excel, CSV, TXT, Images, ZIP (Max 25MB)
      </p>
    </div>
  );
}

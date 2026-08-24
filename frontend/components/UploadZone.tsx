'use client';

import React, { useRef, useState } from 'react';

interface UploadZoneProps {
  onUpload: (file: File) => void;
  isUploading: boolean;
}

export default function UploadZone({ onUpload, isUploading }: UploadZoneProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      onUpload(e.target.files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      onUpload(e.dataTransfer.files[0]);
    }
  };

  return (
    <div
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={() => fileInputRef.current?.click()}
      style={{
        border: isDragOver ? '2px dashed var(--accent-primary)' : '1px dashed var(--border-hover)',
        borderRadius: 'var(--radius-md)',
        padding: '20px 16px',
        textAlign: 'center',
        cursor: 'pointer',
        backgroundColor: isDragOver ? 'var(--accent-subtle)' : 'rgba(15, 23, 42, 0.4)',
        backdropFilter: 'blur(8px)',
        transition: 'all var(--transition-fast)',
        boxShadow: isDragOver ? 'var(--shadow-glow)' : 'none'
      }}
    >
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        hidden
        accept=".pdf,.docx,.pptx,.xlsx,.csv,.txt,.md,.png,.jpg,.jpeg,.zip"
      />
      <div style={{ fontSize: '1.6rem', marginBottom: '6px', animation: isUploading ? 'pulseDot 1.2s infinite' : 'none' }}>
        {isUploading ? '⚙️' : '📥'}
      </div>
      <p style={{ fontSize: '0.88rem', fontWeight: 600, color: 'var(--text-primary)' }}>
        {isUploading ? 'Parsing & Indexing File...' : 'Drop document or ZIP here'}
      </p>
      <p style={{ fontSize: '0.73rem', color: 'var(--text-muted)', marginTop: '4px', lineHeight: '1.4' }}>
        Supports PDF, DOCX, PPTX, Excel, CSV, OCR Images & ZIP archives
      </p>
    </div>
  );
}

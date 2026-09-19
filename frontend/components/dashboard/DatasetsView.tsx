'use client';

import React, { useState } from 'react';
import {
  Database,
  Search,
  Trash2,
  Eye,
  Sparkles,
  FileSpreadsheet,
  FileText,
  FileArchive,
  FileCode,
  UploadCloud,
  Plus
} from 'lucide-react';
import { Document } from '../../lib/types';

interface DatasetsViewProps {
  documents: Document[];
  activeDocId: string | null;
  onSelectDoc: (docId: string) => void;
  onPreviewDoc: (doc: Document) => void;
  onDeleteDoc: (docId: string) => void;
  onStartAnalysis: (docId: string) => void;
  onUpload: (file: File) => void;
  isUploading: boolean;
}

export default function DatasetsView({
  documents,
  activeDocId,
  onSelectDoc,
  onPreviewDoc,
  onDeleteDoc,
  onStartAnalysis,
  onUpload,
  isUploading
}: DatasetsViewProps) {
  const [searchTerm, setSearchTerm] = useState('');
  const [formatFilter, setFormatFilter] = useState('all');
  const fileInputRef = React.useRef<HTMLInputElement>(null);

  const getFormatIcon = (fileType: string) => {
    const ft = (fileType || '').toLowerCase();
    if (ft.includes('csv') || ft.includes('excel') || ft.includes('xls')) {
      return <FileSpreadsheet className="format-type-icon text-green" size={18} />;
    }
    if (ft.includes('zip')) {
      return <FileArchive className="format-type-icon text-purple" size={18} />;
    }
    if (ft.includes('json')) {
      return <FileCode className="format-type-icon text-amber" size={18} />;
    }
    return <FileText className="format-type-icon text-blue" size={18} />;
  };

  const filteredDocs = documents.filter((doc) => {
    const matchesSearch = doc.filename.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesFormat =
      formatFilter === 'all' ||
      (doc.file_type && doc.file_type.toLowerCase().includes(formatFilter));
    return matchesSearch && matchesFormat;
  });

  return (
    <div className="datasets-view-container">
      {/* Top Header & Action Controls */}
      <div className="view-action-toolbar">
        <div className="view-search-wrapper">
          <Search size={16} className="view-search-icon" />
          <input
            type="text"
            placeholder="Search datasets by filename or type..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="view-search-input"
          />
        </div>

        <div className="view-filter-group">
          {['all', 'csv', 'excel', 'pdf', 'zip'].map((fmt) => (
            <button
              key={fmt}
              className={`filter-chip-btn ${formatFilter === fmt ? 'active' : ''}`}
              onClick={() => setFormatFilter(fmt)}
            >
              {fmt.toUpperCase()}
            </button>
          ))}
        </div>

        <button
          className="view-primary-action-btn"
          onClick={() => fileInputRef.current?.click()}
          disabled={isUploading}
        >
          <Plus size={16} />
          <span>{isUploading ? 'Uploading...' : 'New Dataset'}</span>
        </button>
        <input
          type="file"
          ref={fileInputRef}
          style={{ display: 'none' }}
          onChange={(e) => {
            if (e.target.files && e.target.files.length > 0) {
              onUpload(e.target.files[0]);
            }
          }}
          accept=".csv,.xlsx,.xls,.json,.zip,.txt,.md,.pdf,.docx,.pptx"
        />
      </div>

      {/* Datasets Table Panel */}
      <div className="dashboard-panel" style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
        <div className="panel-header">
          <h2 className="panel-title">All Datasets ({filteredDocs.length})</h2>
          <span className="panel-subtitle">Manage uploaded datasets, view data schemas, or launch AI analysis</span>
        </div>

        <div className="table-responsive-wrapper" style={{ flex: 1 }}>
          <table className="dashboard-data-table">
            <thead>
              <tr>
                <th>Dataset Name</th>
                <th>File Size</th>
                <th>Format</th>
                <th>Rows / Pages</th>
                <th>Chunks</th>
                <th>Status</th>
                <th>Uploaded</th>
                <th style={{ textAlign: 'right' }}>Actions</th>
              </tr>
            </thead>
            <tbody>
              {filteredDocs.length === 0 ? (
                <tr>
                  <td colSpan={8} className="table-empty-row">
                    No matching datasets found. Upload a new dataset to get started!
                  </td>
                </tr>
              ) : (
                filteredDocs.map((doc) => {
                  const isSelected = activeDocId === doc.doc_id;
                  const sizeMb = (doc.file_size / (1024 * 1024)).toFixed(2);
                  const uploadDate = doc.created_at
                    ? new Date(doc.created_at).toLocaleDateString('en-US', {
                        month: 'short',
                        day: 'numeric',
                        year: 'numeric'
                      })
                    : 'Recently';

                  return (
                    <tr
                      key={doc.doc_id}
                      className={isSelected ? 'selected-row' : ''}
                      onClick={() => onSelectDoc(doc.doc_id)}
                    >
                      <td>
                        <div className="table-dataset-name-cell">
                          {getFormatIcon(doc.file_type || doc.filename)}
                          <span className="dataset-filename-text" title={doc.filename}>
                            {doc.filename}
                          </span>
                        </div>
                      </td>
                      <td>{sizeMb} MB</td>
                      <td>
                        <span className="table-format-tag">{doc.file_type.toUpperCase()}</span>
                      </td>
                      <td>{doc.page_count ? doc.page_count : '—'}</td>
                      <td>{doc.chunk_count ? doc.chunk_count : '—'}</td>
                      <td>
                        <span
                          className={`table-status-badge ${
                            doc.status === 'ready'
                              ? 'ready'
                              : doc.status === 'failed'
                              ? 'failed'
                              : 'processing'
                          }`}
                        >
                          {doc.status === 'ready' ? 'Ready' : doc.status === 'failed' ? 'Failed' : doc.status}
                        </span>
                      </td>
                      <td>{uploadDate}</td>
                      <td style={{ textAlign: 'right' }}>
                        <div className="table-actions-cluster">
                          <button
                            className="table-action-icon-btn analyze"
                            onClick={(e) => {
                              e.stopPropagation();
                              onSelectDoc(doc.doc_id);
                              onStartAnalysis(doc.doc_id);
                            }}
                            title="Start AI Analysis"
                            disabled={doc.status !== 'ready'}
                          >
                            <Sparkles size={15} />
                          </button>
                          <button
                            className="table-action-icon-btn preview"
                            onClick={(e) => {
                              e.stopPropagation();
                              onPreviewDoc(doc);
                            }}
                            title="Preview Markdown"
                          >
                            <Eye size={15} />
                          </button>
                          <button
                            className="table-action-icon-btn delete"
                            onClick={(e) => {
                              e.stopPropagation();
                              if (confirm(`Are you sure you want to delete '${doc.filename}'?`)) {
                                onDeleteDoc(doc.doc_id);
                              }
                            }}
                            title="Delete Dataset"
                          >
                            <Trash2 size={15} />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

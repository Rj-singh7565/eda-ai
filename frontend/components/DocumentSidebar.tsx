'use client';

import { Document } from '../lib/types';
import UploadZone from './UploadZone';
import ProcessingStatus from './ProcessingStatus';

interface DocumentSidebarProps {
  documents: Document[];
  activeDocId: string | null;
  onSelectDoc: (docId: string) => void;
  onDeleteDoc: (docId: string) => void;
  onUpload: (file: File) => void;
  isUploading: boolean;
  searchFilter: string;
  onSearchFilterChange: (q: string) => void;
}

export default function DocumentSidebar(props: DocumentSidebarProps) {
  const getFormatBadge = (filename: string) => {
    const ext = filename.split('.').pop()?.toUpperCase() || 'DOC';
    switch (ext) {
      case 'PDF':
        return <span className="format-icon format-pdf">PDF</span>;
      case 'DOCX':
      case 'DOC':
        return <span className="format-icon format-docx">DOC</span>;
      case 'XLSX':
      case 'CSV':
      case 'XLS':
        return <span className="format-icon format-xlsx">XLS</span>;
      case 'PPTX':
      case 'PPT':
        return <span className="format-icon format-pptx">PPT</span>;
      case 'ZIP':
        return <span className="format-icon format-zip">ZIP</span>;
      default:
        return <span className="format-icon format-docx">TXT</span>;
    }
  };

  const filteredDocs = props.documents.filter((doc) =>
    doc.filename.toLowerCase().includes(props.searchFilter.toLowerCase())
  );

  return (
    <aside className="col-library">
      {/* Header */}
      <div className="lib-header">
        <div>
          <div style={{ fontSize: '0.72rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--muted)', letterSpacing: '0.06em' }}>
            Documents
          </div>
          <div>Library</div>
        </div>
        <button className="lib-add-btn" title="Add Document">+</button>
      </div>

      {/* Upload Zone Card */}
      <UploadZone onUpload={props.onUpload} isUploading={props.isUploading} />

      {/* Filter / Search Input */}
      <div style={{ margin: '4px 0' }}>
        <input
          type="text"
          placeholder="🔍 Filter documents..."
          value={props.searchFilter}
          onChange={(e) => props.onSearchFilterChange(e.target.value)}
          style={{
            width: '100%',
            padding: '6px 10px',
            fontSize: '0.78rem',
            borderRadius: 'var(--radius-xs)',
            border: '1px solid var(--border)',
            background: 'var(--paper)',
            color: 'var(--ink)'
          }}
        />
      </div>

      {/* Recently Added List */}
      <div className="recent-header">
        <span>Recently added ({filteredDocs.length})</span>
        {props.searchFilter && (
          <span
            onClick={() => props.onSearchFilterChange('')}
            style={{ cursor: 'pointer', fontSize: '0.72rem', color: 'var(--slate)', fontWeight: 600 }}
          >
            Clear filter
          </span>
        )}
      </div>

      {/* Document Items List */}
      <div className="doc-list-group">
        {filteredDocs.length === 0 ? (
          <div style={{ textAlign: 'center', padding: '20px 0', fontSize: '0.8rem', color: 'var(--muted)' }}>
            No matching documents
          </div>
        ) : (
          filteredDocs.map((doc) => {
            const isActive = doc.doc_id === props.activeDocId;
            const sizeMb = doc.file_size
              ? (doc.file_size / (1024 * 1024)).toFixed(1)
              : '1.2';

            return (
              <div
                key={doc.doc_id}
                onClick={() => props.onSelectDoc(doc.doc_id)}
                className={`doc-item-row ${isActive ? 'active' : ''}`}
              >
                {getFormatBadge(doc.filename)}
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--ink)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {doc.filename}
                  </div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--muted)', marginTop: '4px', display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                    <span>Today • {sizeMb} MB</span>
                    <ProcessingStatus status={doc.status} errorMessage={doc.error_message} chunkCount={doc.chunk_count} compact />
                  </div>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    props.onDeleteDoc(doc.doc_id);
                  }}
                  style={{ background: 'transparent', border: 'none', color: 'var(--muted)', cursor: 'pointer', fontSize: '0.9rem' }}
                >
                  &times;
                </button>
              </div>
            );
          })
        )}
      </div>

      {/* Footer Actions & Storage Usage */}
      <div style={{ borderTop: '1px solid var(--border)', paddingTop: '12px', marginTop: 'auto' }}>
        <button
          style={{
            width: '100%',
            background: 'transparent',
            border: '1px solid var(--border)',
            padding: '8px',
            borderRadius: 'var(--radius-xs)',
            fontSize: '0.78rem',
            fontWeight: 600,
            color: 'var(--ink)',
            cursor: 'pointer',
            marginBottom: '12px'
          }}
        >
          View all documents &rarr;
        </button>

        {/* Dynamic Storage Usage calculation */}
        {(() => {
          const totalBytes = props.documents.reduce((sum, d) => sum + (d.file_size || 0), 0);
          const maxBytes = 10 * 1024 * 1024 * 1024; // 10 GB limit
          const pct = Math.min(100, Math.max(0, (totalBytes / maxBytes) * 100));
          const displayUsed = totalBytes >= 1024 * 1024 * 1024
            ? `${(totalBytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
            : `${(totalBytes / (1024 * 1024)).toFixed(1)} MB`;

          return (
            <>
              <div style={{ fontSize: '0.72rem', color: 'var(--muted)', display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                <span>Storage Usage</span>
                <span>{displayUsed} / 10 GB</span>
              </div>
              <div style={{ height: '4px', background: 'rgba(0, 0, 0, 0.08)', borderRadius: '2px', overflow: 'hidden' }}>
                <div style={{ width: `${pct}%`, height: '100%', background: '#6366f1', transition: 'width 0.3s ease' }} />
              </div>
            </>
          );
        })()}
      </div>
    </aside>
  );
}

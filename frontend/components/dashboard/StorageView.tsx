'use client';

import React from 'react';
import { HardDrive, Database, Server, FileText, CheckCircle2, ShieldCheck } from 'lucide-react';
import { Document, DashboardStats, SystemHealth } from '../../lib/types';

interface StorageViewProps {
  documents: Document[];
  stats: DashboardStats | null;
  health: SystemHealth | null;
}

export default function StorageView({ documents, stats, health }: StorageViewProps) {
  const totalBytes = documents.reduce((acc, d) => acc + (d.file_size || 0), 0);
  const totalMb = (totalBytes / (1024 * 1024)).toFixed(2);
  const totalGb = (totalBytes / (1024 * 1024 * 1024)).toFixed(3);
  const storageDisplay = `${totalMb} MB (${totalGb} GB)`;
  const maxQuotaGb = 5.0;
  const usagePercent = Math.min(100, Math.max(2, (totalBytes / (maxQuotaGb * 1024 * 1024 * 1024)) * 100)).toFixed(1);

  return (
    <div className="storage-view-container">
      <div className="kpi-metrics-row">
        <div className="kpi-card">
          <div className="kpi-card-header">
            <div className="kpi-icon-box purple">
              <HardDrive size={20} />
            </div>
            <div className="kpi-sub-label">Quota: 5 GB</div>
          </div>
          <div className="kpi-card-content">
            <div className="kpi-title">Local Storage Used</div>
            <div className="kpi-value">{storageDisplay}</div>
            <div className="kpi-progress-track">
              <div className="kpi-progress-bar" style={{ width: `${usagePercent}%` }}></div>
            </div>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-card-header">
            <div className="kpi-icon-box blue">
              <Database size={20} />
            </div>
            <div className="kpi-trend-pill positive">Namespace Isolated</div>
          </div>
          <div className="kpi-card-content">
            <div className="kpi-title">Vector Database Index</div>
            <div className="kpi-value">{health?.pinecone_index || 'eda-assistant'}</div>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-card-header">
            <div className="kpi-icon-box teal">
              <Server size={20} />
            </div>
            <div className="kpi-trend-pill positive">Active</div>
          </div>
          <div className="kpi-card-content">
            <div className="kpi-title">Relational Database</div>
            <div className="kpi-value">{health?.database ? health.database.toUpperCase() : 'SQLITE'}</div>
          </div>
        </div>
      </div>

      <div className="dashboard-panel" style={{ marginTop: '20px' }}>
        <div className="panel-header">
          <h2 className="panel-title">Storage Allocation by Dataset</h2>
          <span className="panel-subtitle">Disk artifacts and normalized Markdown files</span>
        </div>

        <div className="table-responsive-wrapper">
          <table className="dashboard-data-table">
            <thead>
              <tr>
                <th>Dataset Name</th>
                <th>File Size</th>
                <th>Format</th>
                <th>Chunks Indexed</th>
                <th>Markdown Path</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {documents.length === 0 ? (
                <tr>
                  <td colSpan={6} className="table-empty-row">
                    No files stored yet.
                  </td>
                </tr>
              ) : (
                documents.map((doc) => (
                  <tr key={doc.doc_id}>
                    <td>
                      <div className="table-dataset-name-cell">
                        <FileText size={16} className="text-blue" />
                        <span className="dataset-filename-text">{doc.filename}</span>
                      </div>
                    </td>
                    <td>{(doc.file_size / (1024 * 1024)).toFixed(2)} MB</td>
                    <td><span className="table-format-tag">{doc.file_type.toUpperCase()}</span></td>
                    <td>{doc.chunk_count || '—'}</td>
                    <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.78rem', color: 'var(--muted)' }}>
                      {doc.markdown_path ? `processed/${doc.doc_id}.md` : '—'}
                    </td>
                    <td>
                      <span className={`table-status-badge ${doc.status}`}>
                        {doc.status}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

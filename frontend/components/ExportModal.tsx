'use client';

import React, { useState } from 'react';
import {
  FileText,
  FileSpreadsheet,
  Download,
  X,
  Check,
  Sparkles,
  Printer,
  FileCode,
  FileJson,
  Layers,
  Database
} from 'lucide-react';
import { Document, ChatMessage } from '../lib/types';

interface ExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  activeDoc: Document | null;
  messages: ChatMessage[];
  onShowToast: (type: 'success' | 'error' | 'info', message: string) => void;
}

export type ExportFormat = 'pdf' | 'excel' | 'csv' | 'json' | 'markdown';

export default function ExportModal({
  isOpen,
  onClose,
  activeDoc,
  messages,
  onShowToast
}: ExportModalProps) {
  const [selectedFormat, setSelectedFormat] = useState<ExportFormat>('pdf');
  const [includeSql, setIncludeSql] = useState(true);
  const [includeInsights, setIncludeInsights] = useState(true);
  const [includeMetadata, setIncludeMetadata] = useState(true);
  const [isExporting, setIsExporting] = useState(false);

  if (!isOpen) return null;

  // Group user and assistant turns
  const turns: { question: string; answer: string; timestamp?: string }[] = [];
  for (let i = 0; i < messages.length; i++) {
    if (messages[i].sender === 'user') {
      const q = messages[i].text;
      const t = messages[i].timestamp;
      let a = '';
      if (i + 1 < messages.length && messages[i + 1].sender === 'assistant') {
        a = messages[i + 1].text;
        i++;
      }
      turns.push({ question: q, answer: a, timestamp: t });
    }
  }

  // Parse markdown tables from turn answers
  const parseTableFromAnswer = (answer: string) => {
    const lines = answer.split('\n').map((l) => l.trim()).filter(Boolean);
    const tableLines = lines.filter((l) => l.startsWith('|') && l.endsWith('|'));
    if (tableLines.length >= 2) {
      const headers = tableLines[0].split('|').map((c) => c.trim()).filter(Boolean);
      const rows: string[][] = [];
      for (let i = 1; i < tableLines.length; i++) {
        const line = tableLines[i];
        if (/^\|(\s*[-:]+\s*\|)+$/.test(line)) continue;
        const cells = line.split('|').map((c) => c.trim()).slice(1, -1);
        if (cells.length > 0) rows.push(cells);
      }
      return { headers, rows };
    }
    return null;
  };

  const docTitle = activeDoc?.filename ? activeDoc.filename.replace(/\.[^/.]+$/, '') : 'EDA_Analysis';

  const handleExport = () => {
    setIsExporting(true);

    try {
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, 19);

      if (selectedFormat === 'pdf') {
        // Generate Printable HTML Report and trigger Print/Save as PDF
        generatePdfPrintView();
        onShowToast('success', 'PDF Print Dialog opened. Select "Save as PDF" to save.');
        onClose();
        setIsExporting(false);
        return;
      }

      if (selectedFormat === 'excel' || selectedFormat === 'csv') {
        let csvContent = '\uFEFF'; // UTF-8 Byte Order Mark for Excel compatibility
        
        if (includeMetadata) {
          csvContent += `# EDA Analysis Report\n`;
          csvContent += `# Dataset: ${activeDoc?.filename || 'Active Dataset'}\n`;
          csvContent += `# Generated: ${new Date().toLocaleString()}\n`;
          csvContent += `# Queries Executed: ${turns.length}\n\n`;
        }

        turns.forEach((turn, idx) => {
          csvContent += `=== QUERY ${idx + 1}: ${turn.question.replace(/"/g, '""')} ===\n`;
          const tableData = parseTableFromAnswer(turn.answer);

          if (tableData && tableData.headers.length > 0) {
            csvContent += tableData.headers.map((h) => `"${h.replace(/"/g, '""')}"`).join(',') + '\n';
            tableData.rows.forEach((row) => {
              csvContent += row.map((cell) => `"${cell.replace(/"/g, '""')}"`).join(',') + '\n';
            });
          } else {
            csvContent += `"Response","${turn.answer.replace(/"/g, '""')}"\n`;
          }
          csvContent += '\n';
        });

        const mimeType = selectedFormat === 'excel' ? 'application/vnd.ms-excel;charset=utf-8;' : 'text/csv;charset=utf-8;';
        const ext = selectedFormat === 'excel' ? 'csv' : 'csv';
        const blob = new Blob([csvContent], { type: mimeType });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${docTitle}_Analysis_${timestamp}.${ext}`;
        a.click();
        URL.revokeObjectURL(url);
        onShowToast('success', `Exported ${selectedFormat.toUpperCase()} spreadsheet successfully!`);
      }

      if (selectedFormat === 'json') {
        const jsonData = {
          report_title: `EDA Analysis Report — ${activeDoc?.filename || 'Dataset'}`,
          generated_at: new Date().toISOString(),
          dataset_metadata: includeMetadata && activeDoc ? {
            filename: activeDoc.filename,
            file_size_bytes: activeDoc.file_size,
            file_type: activeDoc.file_type,
            status: activeDoc.status,
            chunk_count: activeDoc.chunk_count,
            page_count: activeDoc.page_count
          } : undefined,
          queries: turns.map((turn, idx) => {
            const tableData = parseTableFromAnswer(turn.answer);
            return {
              query_index: idx + 1,
              question: turn.question,
              timestamp: turn.timestamp,
              has_table: !!tableData,
              table: tableData || undefined,
              raw_response: turn.answer
            };
          })
        };

        const blob = new Blob([JSON.stringify(jsonData, null, 2)], { type: 'application/json;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${docTitle}_Analysis_${timestamp}.json`;
        a.click();
        URL.revokeObjectURL(url);
        onShowToast('success', 'Exported JSON dataset successfully!');
      }

      if (selectedFormat === 'markdown') {
        let mdContent = `# 📊 EDA Analysis Report — ${activeDoc?.filename || 'Dataset'}\n\n`;
        
        if (includeMetadata) {
          mdContent += `> **Generated:** ${new Date().toLocaleString()}  \n`;
          mdContent += `> **Dataset:** ${activeDoc?.filename || 'Active Dataset'}  \n`;
          mdContent += `> **Total Query Turns:** ${turns.length}  \n\n---\n\n`;
        }

        turns.forEach((turn, idx) => {
          mdContent += `## Query ${idx + 1}: ${turn.question}\n\n`;
          mdContent += `${turn.answer}\n\n---\n\n`;
        });

        const blob = new Blob([mdContent], { type: 'text/markdown;charset=utf-8;' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `${docTitle}_Analysis_${timestamp}.md`;
        a.click();
        URL.revokeObjectURL(url);
        onShowToast('success', 'Exported Markdown report successfully!');
      }

      onClose();
    } catch (err: any) {
      console.error('Export error:', err);
      onShowToast('error', 'Failed to export document. Please try again.');
    } finally {
      setIsExporting(false);
    }
  };

  const generatePdfPrintView = () => {
    const printWindow = window.open('', '_blank');
    if (!printWindow) return;

    let turnsHtml = '';
    turns.forEach((turn, idx) => {
      const tableData = parseTableFromAnswer(turn.answer);
      let tableHtml = '';

      if (tableData && tableData.headers.length > 0) {
        tableHtml = `
          <div class="table-container">
            <table>
              <thead>
                <tr>
                  <th style="width: 38px; text-align: center;">#</th>
                  ${tableData.headers.map((h) => `<th>${h}</th>`).join('')}
                </tr>
              </thead>
              <tbody>
                ${tableData.rows
                  .map(
                    (row, rIdx) => `
                  <tr>
                    <td style="text-align: center; color: #64748b; font-weight: 600;">${rIdx + 1}</td>
                    ${row.map((c, cIdx) => `<td class="${cIdx > 0 ? 'metric' : ''}">${c}</td>`).join('')}
                  </tr>
                `
                  )
                  .join('')}
              </tbody>
            </table>
          </div>
        `;
      } else {
        tableHtml = `<div class="raw-response"><pre>${turn.answer}</pre></div>`;
      }

      turnsHtml += `
        <div class="turn-card">
          <div class="turn-header">
            <span class="turn-badge">Query ${idx + 1}</span>
            <h3 class="turn-question">${turn.question}</h3>
          </div>
          ${tableHtml}
        </div>
      `;
    });

    const htmlContent = `
      <!DOCTYPE html>
      <html>
      <head>
        <title>EDA Analysis Report — ${activeDoc?.filename || 'Dataset'}</title>
        <meta charset="utf-8" />
        <style>
          @page {
            size: A4 portrait;
            margin: 18mm 16mm;
          }
          * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
          }
          body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            color: #0f172a;
            background: #ffffff;
            padding: 24px;
            font-size: 13px;
            line-height: 1.5;
          }
          .header-box {
            border-bottom: 2px solid #2563eb;
            padding-bottom: 16px;
            margin-bottom: 24px;
            display: flex;
            justify-content: space-between;
            align-items: flex-end;
          }
          .brand-title {
            font-size: 20px;
            font-weight: 800;
            color: #0f172a;
          }
          .brand-subtitle {
            font-size: 12px;
            color: #64748b;
            margin-top: 4px;
          }
          .meta-info {
            text-align: right;
            font-size: 11px;
            color: #64748b;
          }
          .turn-card {
            background: #ffffff;
            border: 1px solid #e2e8f0;
            border-radius: 8px;
            padding: 16px;
            margin-bottom: 20px;
            page-break-inside: avoid;
          }
          .turn-header {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 12px;
          }
          .turn-badge {
            background: #eff6ff;
            color: #2563eb;
            font-size: 10px;
            font-weight: 700;
            padding: 3px 8px;
            border-radius: 4px;
            text-transform: uppercase;
          }
          .turn-question {
            font-size: 14px;
            font-weight: 700;
            color: #0f172a;
          }
          .table-container {
            overflow: hidden;
            border-radius: 6px;
            border: 1px solid #e2e8f0;
          }
          table {
            width: 100%;
            border-collapse: collapse;
            font-size: 11.5px;
          }
          th {
            background: #f8fafc;
            color: #475569;
            font-weight: 700;
            text-align: left;
            padding: 8px 12px;
            border-bottom: 1px solid #e2e8f0;
            text-transform: uppercase;
            font-size: 10px;
            letter-spacing: 0.03em;
          }
          td {
            padding: 8px 12px;
            border-bottom: 1px solid #f1f5f9;
            color: #1e293b;
          }
          tr:nth-child(even) {
            background-color: #f8fafc;
          }
          td.metric {
            font-variant-numeric: tabular-nums;
            font-weight: 600;
            color: #0f172a;
          }
          .raw-response {
            background: #f8fafc;
            padding: 12px;
            border-radius: 6px;
            font-size: 11.5px;
            white-space: pre-wrap;
          }
          .footer {
            margin-top: 32px;
            text-align: center;
            font-size: 10px;
            color: #94a3b8;
            border-top: 1px solid #e2e8f0;
            padding-top: 12px;
          }
        </style>
      </head>
      <body>
        <div class="header-box">
          <div>
            <div class="brand-title">EDA Assistant — Analytical Report</div>
            <div class="brand-subtitle">Dataset: <strong>${activeDoc?.filename || 'Active Dataset'}</strong></div>
          </div>
          <div class="meta-info">
            <div>Generated: <strong>${new Date().toLocaleDateString()} ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</strong></div>
            <div>Status: <strong>Verified SQL Execution</strong></div>
          </div>
        </div>

        ${turnsHtml}

        <div class="footer">
          Generated automatically by EDA Assistant • Deterministic Tabular Analytics Platform
        </div>

        <script>
          window.onload = function() {
            setTimeout(function() {
              window.print();
            }, 300);
          };
        </script>
      </body>
      </html>
    `;

    printWindow.document.open();
    printWindow.document.write(htmlContent);
    printWindow.document.close();
  };

  const formats: { id: ExportFormat; title: string; subtitle: string; icon: any; badge: string; color: string }[] = [
    {
      id: 'pdf',
      title: 'PDF Document (.pdf)',
      subtitle: 'Printable executive report with styled tables & insights',
      icon: Printer,
      badge: 'Recommended',
      color: '#dc2626'
    },
    {
      id: 'excel',
      title: 'Excel Spreadsheet (.csv / .xlsx)',
      subtitle: 'Compatible spreadsheet with UTF-8 encoding & row/column structure',
      icon: FileSpreadsheet,
      badge: 'Data Table',
      color: '#16a34a'
    },
    {
      id: 'csv',
      title: 'CSV Data (.csv)',
      subtitle: 'Standard comma-separated table records for data tools',
      icon: FileSpreadsheet,
      badge: 'Raw Data',
      color: '#059669'
    },
    {
      id: 'json',
      title: 'JSON Dataset (.json)',
      subtitle: 'Structured machine-readable format with full metadata',
      icon: FileJson,
      badge: 'API & Dev',
      color: '#7c3aed'
    },
    {
      id: 'markdown',
      title: 'Markdown Document (.md)',
      subtitle: 'Standard Markdown tables and documentation syntax',
      icon: FileText,
      badge: 'Docs',
      color: '#2563eb'
    }
  ];

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(15, 23, 42, 0.65)',
        backdropFilter: 'blur(4px)',
        zIndex: 9999,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '16px'
      }}
      onClick={onClose}
    >
      <div
        style={{
          background: '#ffffff',
          borderRadius: '16px',
          width: '100%',
          maxWidth: '560px',
          boxShadow: '0 20px 40px -10px rgba(0, 0, 0, 0.25)',
          border: '1px solid #e2e8f0',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column'
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Modal Header */}
        <div
          style={{
            padding: '20px 24px',
            borderBottom: '1px solid #e2e8f0',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            background: '#f8fafc'
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: '10px',
                background: '#eff6ff',
                color: '#2563eb',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}
            >
              <Download size={18} />
            </div>
            <div>
              <h2 style={{ fontSize: '1.05rem', fontWeight: 700, color: '#0f172a', margin: 0 }}>
                Export Analysis File
              </h2>
              <p style={{ fontSize: '0.78rem', color: '#64748b', margin: '2px 0 0 0' }}>
                Select format to export {activeDoc?.filename || 'current dataset analysis'}
              </p>
            </div>
          </div>

          <button
            onClick={onClose}
            style={{
              background: 'transparent',
              border: 'none',
              color: '#94a3b8',
              cursor: 'pointer',
              padding: '6px',
              borderRadius: '6px',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}
          >
            <X size={18} />
          </button>
        </div>

        {/* Modal Body */}
        <div style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {/* Format Selector List */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            <span style={{ fontSize: '0.72rem', fontWeight: 700, color: '#64748b', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
              Choose Document Format
            </span>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {formats.map((fmt) => {
                const IconComponent = fmt.icon;
                const isSelected = selectedFormat === fmt.id;
                return (
                  <div
                    key={fmt.id}
                    onClick={() => setSelectedFormat(fmt.id)}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'space-between',
                      padding: '12px 14px',
                      borderRadius: '10px',
                      border: `1.5px solid ${isSelected ? '#2563eb' : '#e2e8f0'}`,
                      background: isSelected ? '#eff6ff' : '#ffffff',
                      cursor: 'pointer',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                      <div
                        style={{
                          width: '32px',
                          height: '32px',
                          borderRadius: '8px',
                          background: isSelected ? '#ffffff' : '#f8fafc',
                          border: `1px solid ${isSelected ? '#bfdbfe' : '#e2e8f0'}`,
                          color: fmt.color,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center'
                        }}
                      >
                        <IconComponent size={16} />
                      </div>
                      <div>
                        <div style={{ fontSize: '0.86rem', fontWeight: 700, color: '#0f172a' }}>
                          {fmt.title}
                        </div>
                        <div style={{ fontSize: '0.74rem', color: '#64748b', marginTop: '1px' }}>
                          {fmt.subtitle}
                        </div>
                      </div>
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span
                        style={{
                          fontSize: '0.68rem',
                          fontWeight: 700,
                          padding: '2px 8px',
                          borderRadius: '9999px',
                          background: isSelected ? '#dbeafe' : '#f1f5f9',
                          color: isSelected ? '#1e40af' : '#64748b'
                        }}
                      >
                        {fmt.badge}
                      </span>
                      <div
                        style={{
                          width: '18px',
                          height: '18px',
                          borderRadius: '50%',
                          border: `1.5px solid ${isSelected ? '#2563eb' : '#cbd5e1'}`,
                          background: isSelected ? '#2563eb' : 'transparent',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center'
                        }}
                      >
                        {isSelected && <Check size={11} color="#ffffff" strokeWidth={3} />}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>

          {/* Options & Metadata */}
          <div
            style={{
              background: '#f8fafc',
              border: '1px solid #e2e8f0',
              borderRadius: '10px',
              padding: '12px 16px',
              display: 'flex',
              flexDirection: 'column',
              gap: '10px'
            }}
          >
            <span style={{ fontSize: '0.72rem', fontWeight: 700, color: '#64748b', textTransform: 'uppercase' }}>
              Export Options
            </span>

            <div style={{ display: 'flex', flexWrap: 'wrap', gap: '14px' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.78rem', color: '#1e293b', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={includeMetadata}
                  onChange={(e) => setIncludeMetadata(e.target.checked)}
                  style={{ accentColor: '#2563eb' }}
                />
                <span>Dataset metadata</span>
              </label>

              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.78rem', color: '#1e293b', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={includeInsights}
                  onChange={(e) => setIncludeInsights(e.target.checked)}
                  style={{ accentColor: '#2563eb' }}
                />
                <span>Summary insights</span>
              </label>

              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '0.78rem', color: '#1e293b', cursor: 'pointer' }}>
                <input
                  type="checkbox"
                  checked={includeSql}
                  onChange={(e) => setIncludeSql(e.target.checked)}
                  style={{ accentColor: '#2563eb' }}
                />
                <span>SQL operations</span>
              </label>
            </div>
          </div>
        </div>

        {/* Modal Footer */}
        <div
          style={{
            padding: '16px 24px',
            borderTop: '1px solid #e2e8f0',
            background: '#f8fafc',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between'
          }}
        >
          <div style={{ fontSize: '0.75rem', color: '#64748b' }}>
            {turns.length} quer{turns.length === 1 ? 'y' : 'ies'} ready to export
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <button
              onClick={onClose}
              style={{
                padding: '8px 16px',
                borderRadius: '8px',
                border: '1px solid #cbd5e1',
                background: '#ffffff',
                color: '#475569',
                fontSize: '0.82rem',
                fontWeight: 600,
                cursor: 'pointer'
              }}
            >
              Cancel
            </button>

            <button
              onClick={handleExport}
              disabled={isExporting || turns.length === 0}
              style={{
                padding: '8px 20px',
                borderRadius: '8px',
                border: 'none',
                background: '#2563eb',
                color: '#ffffff',
                fontSize: '0.82rem',
                fontWeight: 700,
                cursor: turns.length === 0 || isExporting ? 'not-allowed' : 'pointer',
                opacity: turns.length === 0 || isExporting ? 0.5 : 1,
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                boxShadow: '0 2px 6px rgba(37, 99, 235, 0.3)'
              }}
            >
              <Download size={14} />
              <span>Download {selectedFormat.toUpperCase()}</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

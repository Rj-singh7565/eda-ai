'use client';

import React, { useState, useMemo } from 'react';
import {
  Table as TableIcon,
  BarChart3,
  Code2,
  Download,
  Sparkles,
  ArrowUpDown,
  Check,
  Copy
} from 'lucide-react';

interface AnalysisTurnCardProps {
  question: string;
  answer: string;
  timestamp?: string;
  latencyMs?: number;
  dbType?: string;
  streaming?: boolean;
}

export default function AnalysisTurnCard({
  question,
  answer,
  timestamp = 'Just now',
  latencyMs = 12,
  dbType = 'PostgreSQL',
  streaming = false
}: AnalysisTurnCardProps) {
  const [viewMode, setViewMode] = useState<'table' | 'chart' | 'sql'>('table');
  const [sortCol, setSortCol] = useState<number | null>(null);
  const [sortAsc, setSortAsc] = useState(true);
  const [copied, setCopied] = useState(false);

  // Dynamic table and insight parser from real assistant answer
  const parsedData = useMemo(() => {
    if (!answer || !answer.trim()) {
      return {
        headers: ['Status', 'Information'],
        rows: [['Processing', 'Analyzing dataset and querying records...']],
        chartData: [] as { label: string; value: number; formatted: string }[],
        sql: `SELECT * FROM active_dataset LIMIT 10;`,
        insight: streaming ? 'Synthesizing tabular insights from dataset...' : 'Query executed successfully.'
      };
    }

    const lines = answer.split('\n').map((l) => l.trim()).filter(Boolean);
    const tableLines: string[] = [];
    const nonTableLines: string[] = [];

    for (const line of lines) {
      if (line.startsWith('|') && line.endsWith('|')) {
        tableLines.push(line);
      } else {
        // Strip markdown fences or tags
        const clean = line.replace(/```[a-z]*/gi, '').trim();
        if (clean) nonTableLines.push(clean);
      }
    }

    let headers: string[] = [];
    let rows: string[][] = [];

    if (tableLines.length >= 2) {
      // First line is headers - slice(1, -1) cleanly drops outer pipe splits
      const rawHeaders = tableLines[0].split('|').slice(1, -1).map((c) => c.trim());
      headers = rawHeaders.length > 0 ? rawHeaders : tableLines[0].split('|').map((c) => c.trim()).filter(Boolean);

      // Skip separator line (|---|---|) and parse data rows
      for (let i = 1; i < tableLines.length; i++) {
        const line = tableLines[i];
        if (/^\|(\s*[-:]+\s*\|)+$/.test(line)) {
          continue; // Separator line
        }
        const rowCells = line.split('|').map((c) => c.trim());
        // Remove leading and trailing empty splits caused by pipe edges
        const cleanedRow = rowCells.slice(1, -1);
        if (cleanedRow.length > 0) {
          // Normalize row cell count to match headers if needed
          if (cleanedRow.length < headers.length) {
            while (cleanedRow.length < headers.length) cleanedRow.push('—');
          }
          rows.push(cleanedRow);
        }
      }
    }

    // Fallback: If no markdown table was detected, extract key-value pairs or lines
    if (headers.length === 0 || rows.length === 0) {
      headers = ['Attribute / Dimension', 'Value / Details'];
      rows = [];
      for (const line of nonTableLines) {
        if (line.includes(':')) {
          const [k, ...v] = line.split(':');
          rows.push([k.replace(/^[-*•\d+.\s]+/, '').trim(), v.join(':').trim()]);
        } else if (line.includes(' - ')) {
          const [k, ...v] = line.split(' - ');
          rows.push([k.replace(/^[-*•\d+.\s]+/, '').trim(), v.join(' - ').trim()]);
        } else {
          rows.push(['Result Item', line.replace(/^[-*•\d+.\s]+/, '').trim()]);
        }
      }

      if (rows.length === 0) {
        headers = ['Query Result', 'Details'];
        rows = [['Output', answer.replace(/\|/g, ' ')]];
      }
    }

    // Determine numeric column for chart visualization
    let numericColIdx = -1;
    for (let c = 1; c < headers.length; c++) {
      const hasNumbers = rows.some((r) => {
        const val = r[c] || '';
        const num = parseFloat(val.replace(/[^0-9.-]+/g, ''));
        return !isNaN(num);
      });
      if (hasNumbers) {
        numericColIdx = c;
        break;
      }
    }

    // If second column isn't numeric, check first column
    if (numericColIdx === -1 && rows.length > 0) {
      const num = parseFloat((rows[0][0] || '').replace(/[^0-9.-]+/g, ''));
      if (!isNaN(num) && headers.length > 1) {
        numericColIdx = 0;
      }
    }

    const chartData: { label: string; value: number; formatted: string }[] = [];
    if (numericColIdx !== -1) {
      const labelColIdx = numericColIdx === 0 ? 1 : 0;
      rows.forEach((r) => {
        const label = r[labelColIdx] || 'Record';
        const rawVal = r[numericColIdx] || '0';
        const num = parseFloat(rawVal.replace(/[^0-9.-]+/g, '')) || 0;
        chartData.push({
          label: label.length > 24 ? label.slice(0, 22) + '…' : label,
          value: Math.abs(num),
          formatted: rawVal
        });
      });
    }

    // Extract or build SQL
    let extractedSql = '';
    const sqlMatch = answer.match(/```(?:sql)?\s*([\s\S]*?)```/i);
    if (sqlMatch) {
      extractedSql = sqlMatch[1].trim();
    } else {
      const selectCols = headers.map((h) => `"${h.toLowerCase().replace(/[^a-z0-9_]+/g, '_')}"`).join(', ');
      extractedSql = `SELECT ${selectCols}\nFROM dataset_table\nLIMIT ${Math.max(rows.length, 10)};`;
    }

    // Extract insight
    let insight = '';
    if (nonTableLines.length > 0) {
      insight = nonTableLines.find((l) => !l.toLowerCase().startsWith('select') && l.length > 15) || nonTableLines[0];
    } else if (rows.length > 0) {
      const topLabel = rows[0][0] || 'Top Item';
      const topVal = rows[0][1] ? ` (${headers[1] || 'Value'}: ${rows[0][1]})` : '';
      insight = `Returned ${rows.length} row${rows.length === 1 ? '' : 's'} across ${headers.length} column${headers.length === 1 ? '' : 's'}. Primary entry: "${topLabel}"${topVal}.`;
    } else {
      insight = `Calculated response for "${question}".`;
    }

    return {
      headers,
      rows,
      chartData,
      sql: extractedSql,
      insight
    };
  }, [answer, question, streaming]);

  // Handle column sorting
  const sortedRows = useMemo(() => {
    if (sortCol === null) return parsedData.rows;
    return [...parsedData.rows].sort((a, b) => {
      const valA = a[sortCol] || '';
      const valB = b[sortCol] || '';
      const numA = parseFloat(valA.replace(/[^0-9.-]+/g, ''));
      const numB = parseFloat(valB.replace(/[^0-9.-]+/g, ''));
      if (!isNaN(numA) && !isNaN(numB)) {
        return sortAsc ? numA - numB : numB - numA;
      }
      return sortAsc ? valA.localeCompare(valB) : valB.localeCompare(valA);
    });
  }, [parsedData.rows, sortCol, sortAsc]);

  const handleSort = (colIdx: number) => {
    if (sortCol === colIdx) {
      setSortAsc(!sortAsc);
    } else {
      setSortCol(colIdx);
      setSortAsc(false); // Descending by default for metrics
    }
  };

  const [isExportMenuOpen, setIsExportMenuOpen] = useState(false);

  const handleExportFormat = (format: 'excel' | 'csv' | 'json' | 'markdown' | 'pdf') => {
    setIsExportMenuOpen(false);
    const timestamp = Date.now();

    if (format === 'excel' || format === 'csv') {
      let csv = '\uFEFF'; // UTF-8 BOM for Excel
      csv += `# Question: ${question.replace(/"/g, '""')}\n`;
      csv += '#' + ',' + parsedData.headers.map((h) => `"${h.replace(/"/g, '""')}"`).join(',') + '\n';
      parsedData.rows.forEach((row, idx) => {
        csv += `${idx + 1},` + row.map((cell) => `"${cell.replace(/"/g, '""')}"`).join(',') + '\n';
      });
      const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `query_result_${timestamp}.csv`;
      link.click();
      URL.revokeObjectURL(url);
      return;
    }

    if (format === 'json') {
      const data = {
        question,
        timestamp,
        headers: parsedData.headers,
        rows: parsedData.rows,
        sql: parsedData.sql,
        insight: parsedData.insight
      };
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `query_result_${timestamp}.json`;
      link.click();
      URL.revokeObjectURL(url);
      return;
    }

    if (format === 'markdown') {
      let md = `### ${question}\n\n`;
      md += `| # | ${parsedData.headers.join(' | ')} |\n`;
      md += `| --- | ${parsedData.headers.map(() => '---').join(' | ')} |\n`;
      parsedData.rows.forEach((row, idx) => {
        md += `| ${idx + 1} | ${row.join(' | ')} |\n`;
      });
      if (parsedData.insight) {
        md += `\n> **Insight:** ${parsedData.insight}\n`;
      }
      const blob = new Blob([md], { type: 'text/markdown;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `query_result_${timestamp}.md`;
      link.click();
      URL.revokeObjectURL(url);
      return;
    }

    if (format === 'pdf') {
      const printWindow = window.open('', '_blank');
      if (!printWindow) return;
      printWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
          <title>${question}</title>
          <style>
            body { font-family: -apple-system, sans-serif; padding: 24px; color: #0f172a; }
            h2 { font-size: 16px; margin-bottom: 12px; }
            table { width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 12px; }
            th { background: #f8fafc; text-align: left; padding: 8px 12px; border: 1px solid #e2e8f0; font-size: 11px; }
            td { padding: 8px 12px; border: 1px solid #e2e8f0; }
            .insight { margin-top: 16px; padding: 12px; background: #eff6ff; border-left: 4px solid #2563eb; font-size: 12px; }
          </style>
        </head>
        <body>
          <h2>Query: ${question}</h2>
          <table>
            <thead>
              <tr>
                <th style="width:36px; text-align:center;">#</th>
                ${parsedData.headers.map((h) => `<th>${h}</th>`).join('')}
              </tr>
            </thead>
            <tbody>
              ${parsedData.rows.map((r, i) => `<tr><td style="text-align:center;">${i + 1}</td>${r.map((c) => `<td>${c}</td>`).join('')}</tr>`).join('')}
            </tbody>
          </table>
          ${parsedData.insight ? `<div class="insight"><strong>Insight:</strong> ${parsedData.insight}</div>` : ''}
          <script>window.onload = function() { setTimeout(function(){ window.print(); }, 200); };</script>
        </body>
        </html>
      `);
      printWindow.document.close();
    }
  };

  const maxChartVal = Math.max(...parsedData.chartData.map((d) => d.value), 1);

  return (
    <div className="analysis-turn-card">
      {/* ── Top Header Row: Question + Latency & Toolbar ───────────── */}
      <div className="turn-card-top-header">
        <div className="turn-question-group">
          <div className="turn-q-avatar">Q</div>
          <div className="turn-question-meta-block">
            <h3 className="turn-question-title">{question}</h3>
            <div className="turn-meta-pill-line">
              <span>{timestamp}</span>
              <span className="turn-meta-bullet">•</span>
              <span className="turn-latency-indicator">
                <span className="turn-green-dot"></span>
                {latencyMs}ms ({dbType})
              </span>
              <span className="turn-meta-bullet">•</span>
              <span style={{ color: '#64748b', fontWeight: 500 }}>
                {parsedData.rows.length} row{parsedData.rows.length === 1 ? '' : 's'} × {parsedData.headers.length} col{parsedData.headers.length === 1 ? '' : 's'}
              </span>
            </div>
          </div>
        </div>

        {/* View Switchers: Table, Chart, SQL, Download */}
        <div className="turn-action-toolbar" style={{ position: 'relative' }}>
          <button
            className={`turn-toolbar-tab ${viewMode === 'table' ? 'active' : ''}`}
            onClick={() => setViewMode('table')}
            title="View Structured Table (Rows & Columns)"
          >
            <TableIcon size={14} />
            <span>Table</span>
          </button>

          {parsedData.chartData.length > 0 && (
            <button
              className={`turn-toolbar-tab ${viewMode === 'chart' ? 'active' : ''}`}
              onClick={() => setViewMode('chart')}
              title="View Visual Chart"
            >
              <BarChart3 size={14} />
              <span>Chart</span>
            </button>
          )}

          <button
            className={`turn-toolbar-tab ${viewMode === 'sql' ? 'active' : ''}`}
            onClick={() => setViewMode('sql')}
            title="View SQL Query"
          >
            <Code2 size={14} />
            <span>SQL</span>
          </button>

          <div style={{ position: 'relative' }}>
            <button
              className="turn-toolbar-icon-btn"
              onClick={() => setIsExportMenuOpen(!isExportMenuOpen)}
              title="Export this result (Excel, PDF, CSV, JSON, Markdown)"
            >
              <Download size={14} />
            </button>

            {isExportMenuOpen && (
              <div
                style={{
                  position: 'absolute',
                  top: 'calc(100% + 4px)',
                  right: 0,
                  width: '200px',
                  background: '#ffffff',
                  border: '1px solid #e2e8f0',
                  borderRadius: '10px',
                  boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.15)',
                  padding: '6px',
                  zIndex: 40,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '2px'
                }}
              >
                <div style={{ fontSize: '0.68rem', fontWeight: 700, color: '#94a3b8', padding: '4px 8px', textTransform: 'uppercase' }}>
                  Export Query Result
                </div>
                <button
                  onClick={() => handleExportFormat('excel')}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '6px 8px',
                    fontSize: '0.78rem',
                    fontWeight: 600,
                    color: '#0f172a',
                    background: 'transparent',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    textAlign: 'left'
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#f1f5f9')}
                  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  <span style={{ color: '#16a34a', fontWeight: 700 }}>📊</span>
                  <span>Excel / CSV (.csv)</span>
                </button>
                <button
                  onClick={() => handleExportFormat('pdf')}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '6px 8px',
                    fontSize: '0.78rem',
                    fontWeight: 600,
                    color: '#0f172a',
                    background: 'transparent',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    textAlign: 'left'
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#f1f5f9')}
                  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  <span style={{ color: '#dc2626', fontWeight: 700 }}>📄</span>
                  <span>PDF Document (.pdf)</span>
                </button>
                <button
                  onClick={() => handleExportFormat('json')}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '6px 8px',
                    fontSize: '0.78rem',
                    fontWeight: 600,
                    color: '#0f172a',
                    background: 'transparent',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    textAlign: 'left'
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#f1f5f9')}
                  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  <span style={{ color: '#7c3aed', fontWeight: 700 }}>📦</span>
                  <span>JSON File (.json)</span>
                </button>
                <button
                  onClick={() => handleExportFormat('markdown')}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '8px',
                    padding: '6px 8px',
                    fontSize: '0.78rem',
                    fontWeight: 600,
                    color: '#0f172a',
                    background: 'transparent',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    textAlign: 'left'
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = '#f1f5f9')}
                  onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'transparent')}
                >
                  <span style={{ color: '#2563eb', fontWeight: 700 }}>📝</span>
                  <span>Markdown (.md)</span>
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Core Body: Table / Chart / SQL View ─────────────────────── */}
      <div className="turn-card-content-area">
        {/* VIEW 1: STRUCTURED DATA TABLE */}
        {viewMode === 'table' && (
          <div className="turn-table-responsive-container" style={{ overflowX: 'auto', width: '100%', maxWidth: '100%', WebkitOverflowScrolling: 'touch' }}>
            <table className="turn-data-table" style={{ width: '100%', minWidth: 'max-content', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th style={{ width: '44px', textAlign: 'center', whiteSpace: 'nowrap' }}>#</th>
                  {parsedData.headers.map((h, hIdx) => (
                    <th
                      key={hIdx}
                      onClick={() => handleSort(hIdx)}
                      className="turn-sortable-th"
                      style={{ whiteSpace: 'nowrap' }}
                    >
                      <div className="th-sort-wrapper">
                        <span>{h}</span>
                        <ArrowUpDown size={12} className="th-sort-icon" />
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sortedRows.map((row, rIdx) => (
                  <tr key={rIdx} className="turn-table-row">
                    <td style={{ textAlign: 'center', color: '#94a3b8', fontSize: '0.78rem', whiteSpace: 'nowrap' }}>
                      {rIdx + 1}
                    </td>
                    {row.map((cell, cIdx) => (
                      <td
                        key={cIdx}
                        className={cIdx > 0 ? 'turn-metric-cell' : 'turn-label-cell'}
                        style={{ whiteSpace: 'nowrap' }}
                      >
                        {cell}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* VIEW 2: VISUAL CHART */}
        {viewMode === 'chart' && (
          <div className="turn-chart-container">
            <div className="turn-chart-bars-list">
              {parsedData.chartData.map((item, idx) => {
                const widthPct = Math.min(100, Math.max(8, Math.round((item.value / maxChartVal) * 100)));
                return (
                  <div key={idx} className="turn-chart-bar-row">
                    <div className="chart-bar-label">{item.label}</div>
                    <div className="chart-bar-track">
                      <div
                        className="chart-bar-fill"
                        style={{ width: `${widthPct}%` }}
                      ></div>
                    </div>
                    <div className="chart-bar-val">{item.formatted}</div>
                  </div>
                );
              })}
            </div>
          </div>
        )}

        {/* VIEW 3: SQL CODE */}
        {viewMode === 'sql' && (
          <div className="turn-sql-container">
            <div className="turn-sql-header">
              <span className="sql-dialect-tag">Analytical Query</span>
              <button
                className="sql-copy-btn"
                onClick={() => {
                  navigator.clipboard.writeText(parsedData.sql);
                  setCopied(true);
                  setTimeout(() => setCopied(false), 2000);
                }}
              >
                {copied ? <Check size={12} /> : <Copy size={12} />}
                <span>{copied ? 'Copied' : 'Copy Query'}</span>
              </button>
            </div>
            <pre className="turn-sql-code-block">
              <code>{parsedData.sql}</code>
            </pre>
          </div>
        )}

        {/* Streaming Indicator */}
        {streaming && (
          <div className="turn-streaming-indicator">
            <span className="streaming-dot"></span> Streaming response into table...
          </div>
        )}
      </div>

      {/* ── Card-Level AI Insight Callout ──────────────────────────── */}
      {parsedData.insight && (
        <div className="turn-insight-callout">
          <div className="turn-insight-icon-box">
            <Sparkles size={16} />
          </div>
          <div className="turn-insight-text">
            <strong>Insight:</strong> {parsedData.insight}
          </div>
        </div>
      )}
    </div>
  );
}

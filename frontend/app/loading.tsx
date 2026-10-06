import React from 'react';

/**
 * Server-Rendered Loading Skeleton for EDA Assistant.
 * Matches exact dimensions of the 5-column workspace to prevent Cumulative Layout Shift (CLS).
 */
export default function DashboardLoading() {
  return (
    <div className="app-viewport" style={{ backgroundColor: 'var(--canvas, #f1f0ec)' }}>
      {/* Sidebar Skeleton */}
      <aside
        style={{
          width: '260px',
          minWidth: '260px',
          height: '100%',
          backgroundColor: '#ffffff',
          borderRight: '1px solid #e2e8f0',
          display: 'flex',
          flexDirection: 'column',
          padding: '24px 16px',
          gap: '24px',
          boxSizing: 'border-box',
        }}
      >
        {/* Brand Skeleton */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px', paddingBottom: '16px', borderBottom: '1px solid #f1f5f9' }}>
          <div style={{ width: '38px', height: '38px', borderRadius: '10px', backgroundColor: '#e2e8f0', animation: 'pulse 1.5s infinite' }} />
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <div style={{ width: '100px', height: '14px', borderRadius: '4px', backgroundColor: '#e2e8f0', animation: 'pulse 1.5s infinite' }} />
            <div style={{ width: '60px', height: '10px', borderRadius: '4px', backgroundColor: '#f1f5f9', animation: 'pulse 1.5s infinite' }} />
          </div>
        </div>

        {/* Navigation Items Skeleton */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', flex: 1 }}>
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <div
              key={i}
              style={{
                width: '100%',
                height: '40px',
                borderRadius: '8px',
                backgroundColor: i === 1 ? '#eff6ff' : '#f8fafc',
                border: '1px solid #f1f5f9',
                display: 'flex',
                alignItems: 'center',
                padding: '0 12px',
                gap: '12px',
              }}
            >
              <div style={{ width: '18px', height: '18px', borderRadius: '4px', backgroundColor: '#cbd5e1' }} />
              <div style={{ width: `${60 + (i % 3) * 20}px`, height: '12px', borderRadius: '4px', backgroundColor: '#cbd5e1' }} />
            </div>
          ))}
        </div>
      </aside>

      {/* Main Workspace Skeleton */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
        {/* Global Header Skeleton */}
        <header
          style={{
            height: '60px',
            minHeight: '60px',
            backgroundColor: '#ffffff',
            borderBottom: '1px solid #e2e8f0',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 28px',
            boxSizing: 'border-box',
          }}
        >
          <div style={{ width: '140px', height: '20px', borderRadius: '4px', backgroundColor: '#e2e8f0', animation: 'pulse 1.5s infinite' }} />
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <div style={{ width: '180px', height: '34px', borderRadius: '8px', backgroundColor: '#f1f5f9' }} />
            <div style={{ width: '100px', height: '34px', borderRadius: '8px', backgroundColor: '#e2e8f0' }} />
          </div>
        </header>

        {/* Dashboard Content Skeleton */}
        <div style={{ flex: 1, padding: '24px 28px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {/* KPI Cards Row Skeleton */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px' }}>
            {[1, 2, 3, 4, 5].map((i) => (
              <div
                key={i}
                style={{
                  backgroundColor: '#ffffff',
                  borderRadius: '12px',
                  padding: '18px 20px',
                  border: '1px solid #e2e8f0',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '12px',
                  boxShadow: '0 1px 3px rgba(0, 0, 0, 0.02)',
                }}
              >
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ width: '32px', height: '32px', borderRadius: '8px', backgroundColor: '#f1f5f9' }} />
                  <div style={{ width: '50px', height: '16px', borderRadius: '12px', backgroundColor: '#f8fafc' }} />
                </div>
                <div style={{ width: '80px', height: '12px', borderRadius: '4px', backgroundColor: '#f1f5f9' }} />
                <div style={{ width: '60px', height: '24px', borderRadius: '4px', backgroundColor: '#e2e8f0' }} />
              </div>
            ))}
          </div>

          {/* Panels Row Skeleton */}
          <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '20px', flex: 1 }}>
            <div
              style={{
                backgroundColor: '#ffffff',
                borderRadius: '12px',
                padding: '24px',
                border: '1px solid #e2e8f0',
                display: 'flex',
                flexDirection: 'column',
                gap: '16px',
                minHeight: '260px',
              }}
            >
              <div style={{ width: '160px', height: '18px', borderRadius: '4px', backgroundColor: '#e2e8f0' }} />
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                {[1, 2, 3].map((r) => (
                  <div key={r} style={{ height: '42px', borderRadius: '6px', backgroundColor: '#f8fafc', border: '1px solid #f1f5f9' }} />
                ))}
              </div>
            </div>

            <div
              style={{
                backgroundColor: '#ffffff',
                borderRadius: '12px',
                padding: '24px',
                border: '1px solid #e2e8f0',
                display: 'flex',
                flexDirection: 'column',
                gap: '16px',
                minHeight: '260px',
              }}
            >
              <div style={{ width: '130px', height: '18px', borderRadius: '4px', backgroundColor: '#e2e8f0' }} />
              <div style={{ flex: 1, borderRadius: '8px', border: '2px dashed #e2e8f0', backgroundColor: '#f8fafc' }} />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

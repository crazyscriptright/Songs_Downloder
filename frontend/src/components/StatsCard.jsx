import React from 'react';

export default function StatsCard({ value, label }) {
  return (
    <div
      className="rounded-lg p-4 text-center min-w-0 border"
      style={{
        background: 'var(--bg-secondary)',
        borderColor: 'var(--border-color)',
      }}
    >
      <div className="text-3xl font-bold mb-1" style={{ color: 'var(--accent-color)' }}>
        {value}
      </div>
      <div className="text-sm break-words" style={{ color: 'var(--text-secondary)' }}>
        {label}
      </div>
    </div>
  );
}
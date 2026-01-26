import React from 'react';
import { Link } from 'react-router-dom';

export default function Header({ title, subtitle, showHomeLink = false, onThemeToggle }) {
  return (
    <div className="text-center py-8 mb-8 relative">
      {showHomeLink && (
        <div className="absolute top-8 left-5 flex gap-4">
          <Link
            to="/"
            className="px-5 py-2 rounded-lg border-2 font-medium transition-all"
            style={{
              background: 'var(--bg-card)',
              color: 'var(--text-secondary)',
              borderColor: 'var(--border-color)',
            }}
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'var(--accent-color)';
              e.currentTarget.style.color = 'var(--bg-primary)';
              e.currentTarget.style.borderColor = 'var(--accent-color)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'var(--bg-card)';
              e.currentTarget.style.color = 'var(--text-secondary)';
              e.currentTarget.style.borderColor = 'var(--border-color)';
            }}
          >
            ← Home
          </Link>
        </div>
      )}
      
      <button
        onClick={onThemeToggle}
        className="absolute top-8 right-5 px-4 py-2 rounded-3xl border-2 cursor-pointer transition-all font-medium"
        style={{
          background: 'var(--bg-card)',
          borderColor: 'var(--border-color)',
          color: 'var(--text-secondary)',
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.background = 'var(--accent-color)';
          e.currentTarget.style.color = 'var(--bg-primary)';
          e.currentTarget.style.borderColor = 'var(--accent-color)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.background = 'var(--bg-card)';
          e.currentTarget.style.color = 'var(--text-secondary)';
          e.currentTarget.style.borderColor = 'var(--border-color)';
        }}
      >
        Theme
      </button>

      <h1 className="text-4xl font-bold mb-3" style={{ color: 'var(--accent-color)' }}>
        {title}
      </h1>
      <p className="text-lg" style={{ color: 'var(--text-secondary)' }}>
        {subtitle}
      </p>
    </div>
  );
}
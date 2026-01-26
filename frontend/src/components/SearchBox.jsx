import React, { useState, useEffect } from 'react';

export default function SearchBox({ searchType, setSearchType, searchQuery, setSearchQuery, onSearch, isSearching }) {
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);

  // Fetch suggestions
  useEffect(() => {
    if (searchQuery.length < 2) {
      setSuggestions([]);
      setShowSuggestions(false);
      return;
    }

    const timer = setTimeout(async () => {
      try {
        const response = await fetch(
          `https://suggestqueries-clients6.youtube.com/complete/search?client=youtube&q=${encodeURIComponent(
            searchQuery
          )}&xhr=t`
        );
        const data = await response.json();

        if (data && data[1] && Array.isArray(data[1])) {
          const suggestionList = data[1]
            .slice(0, 6)
            .map((item) => (Array.isArray(item) ? item[0] : item))
            .filter((s) => s && typeof s === 'string');
          setSuggestions(suggestionList);
          setShowSuggestions(suggestionList.length > 0);
        }
      } catch (error) {
        console.error('Suggestions error:', error);
      }
    }, 300);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  const handleSearch = (e) => {
    e.preventDefault();
    setShowSuggestions(false);
    onSearch(searchQuery, searchType);
  };

  const selectSuggestion = (suggestion) => {
    setSearchQuery(suggestion);
    setShowSuggestions(false);
    onSearch(suggestion, searchType);
  };

  return (
    <div
      className="rounded-2xl p-10 mb-10 border max-w-[800px] mx-auto"
      style={{
        background: 'var(--bg-card)',
        borderColor: 'var(--border-color)',
        boxShadow: '0 10px 30px rgba(0, 0, 0, 0.1)',
      }}
    >
      {/* Search Type Selector */}
      <div className="flex gap-3 mb-5 justify-center">
        {[
          { type: 'music', icon: 'M9 18V5l12-2v13 M6 18a3 3 0 100-6 3 3 0 000 6z M18 16a3 3 0 100-6 3 3 0 000 6z', label: 'Music' },
          { type: 'video', icon: 'M23 7l-7 5 7 5V7z M1 5h15v14H1z', label: 'Videos' },
          { type: 'all', icon: 'M12 2a10 10 0 100 20 10 10 0 000-20z M2 12h20 M12 2a15.3 15.3 0 014 10 15.3 15.3 0 01-4 10 15.3 15.3 0 01-4-10 15.3 15.3 0 014-10z', label: 'All Sources' },
        ].map(({ type, icon, label }) => (
          <button
            key={type}
            onClick={() => setSearchType(type)}
            className={`px-6 py-3 text-base font-bold rounded-lg cursor-pointer transition-all border-2 flex items-center gap-2 ${
              searchType === type ? 'gradient-secondary text-white' : ''
            }`}
            style={
              searchType === type
                ? { borderColor: 'var(--accent-color)' }
                : {
                    background: 'var(--bg-card)',
                    color: 'var(--text-secondary)',
                    borderColor: 'var(--border-color)',
                  }
            }
            onMouseEnter={(e) => {
              if (searchType !== type) {
                e.currentTarget.style.background = 'var(--accent-color)';
                e.currentTarget.style.color = 'var(--bg-primary)';
              }
            }}
            onMouseLeave={(e) => {
              if (searchType !== type) {
                e.currentTarget.style.background = 'var(--bg-card)';
                e.currentTarget.style.color = 'var(--text-secondary)';
              }
            }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d={icon} />
            </svg>
            {label}
          </button>
        ))}
      </div>

      {/* Search Input */}
      <form onSubmit={handleSearch} className="relative">
        <div className="flex gap-4 mb-4">
          <div className="flex-1 relative">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Enter song name, artist, or paste URL..."
              className="w-full px-6 py-4 text-lg rounded-2xl border-2 transition-all"
              style={{
                background: 'var(--bg-primary)',
                borderColor: 'var(--border-color)',
                color: 'var(--text-primary)',
              }}
              onFocus={(e) => {
                e.currentTarget.style.borderColor = 'var(--accent-color)';
                e.currentTarget.style.boxShadow = '0 0 0 4px var(--shadow-color)';
              }}
              onBlur={(e) => {
                setTimeout(() => setShowSuggestions(false), 200);
                e.currentTarget.style.borderColor = 'var(--border-color)';
                e.currentTarget.style.boxShadow = 'none';
              }}
            />

            {/* Suggestions Dropdown */}
            {showSuggestions && suggestions.length > 0 && (
              <div
                className="absolute top-full left-0 right-0 mt-1 rounded-b-2xl border-2 border-t-0 max-h-[300px] overflow-y-auto z-50"
                style={{
                  background: 'var(--bg-card)',
                  borderColor: 'var(--border-color)',
                  boxShadow: '0 8px 25px rgba(0, 0, 0, 0.15)',
                }}
              >
                {suggestions.map((suggestion, index) => (
                  <div
                    key={index}
                    onClick={() => selectSuggestion(suggestion)}
                    className="px-5 py-3 cursor-pointer border-b transition-all flex items-center gap-3"
                    style={{ borderColor: 'var(--border-color)' }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.background = 'var(--accent-color)';
                      e.currentTarget.style.color = 'var(--bg-primary)';
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.background = 'transparent';
                      e.currentTarget.style.color = 'var(--text-primary)';
                    }}
                  >
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <circle cx="11" cy="11" r="8"></circle>
                      <path d="M21 21l-4.35-4.35"></path>
                    </svg>
                    {suggestion}
                  </div>
                ))}
              </div>
            )}
          </div>

          <button
            type="submit"
            disabled={isSearching || !searchQuery.trim()}
            className="px-11 py-4 text-lg font-semibold text-white border-0 rounded-2xl cursor-pointer transition-all min-w-[140px] gradient-secondary disabled:opacity-60 disabled:cursor-not-allowed"
            onMouseEnter={(e) => {
              if (!isSearching && searchQuery.trim()) {
                e.currentTarget.style.transform = 'translateY(-3px)';
                e.currentTarget.style.boxShadow = '0 8px 25px var(--shadow-color)';
              }
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = 'none';
            }}
          >
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              className="inline mr-2"
            >
              <circle cx="11" cy="11" r="8"></circle>
              <path d="m21 21-4.35-4.35"></path>
            </svg>
            Search
          </button>
        </div>

        <p className="text-center text-sm" style={{ color: 'var(--text-tertiary)' }}>
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className="inline mr-1"
          >
            <circle cx="12" cy="12" r="10"></circle>
            <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path>
            <line x1="12" y1="17" x2="12.01" y2="17"></line>
          </svg>
          Search by name or paste a music URL (YouTube, SoundCloud, JioSaavn etc.)
        </p>
      </form>
    </div>
  );
}
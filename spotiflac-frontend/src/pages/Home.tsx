import { App } from "@/app";
import { useEffect, useRef } from "react";

export default function Home() {
  const appRef = useRef<App | null>(null);

  useEffect(() => {
    // Init the App controller after React has rendered the DOM elements
    if (!appRef.current) {
      appRef.current = new App();
      appRef.current.init();
    }
  }, []);

  return (
    <>
      {/* Search Box */}
      <div className="search-box">
        <div className="search-type-selector">
          <button className="type-btn active" data-type="music">
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <path d="M9 18V5l12-2v13" />
              <circle cx="6" cy="18" r="3" />
              <circle cx="18" cy="16" r="3" />
            </svg>
            Music
          </button>
          <button className="type-btn" data-type="video">
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <polygon points="23 7 16 12 23 17 23 7" />
              <rect x="1" y="5" width="15" height="14" rx="2" ry="2" />
            </svg>
            Videos
          </button>
          <button className="type-btn" data-type="all">
            <svg
              width="18"
              height="18"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <circle cx="12" cy="12" r="10" />
              <line x1="2" y1="12" x2="22" y2="12" />
              <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
            </svg>
            All Sources
          </button>
        </div>

        <div className="search-input-group" style={{ position: "relative" }}>
          <input
            type="text"
            id="searchInput"
            placeholder="Enter song name, artist, or paste URL..."
            autoComplete="off"
          />
          <div id="searchSuggestions" className="search-suggestions" />
          <button id="searchBtn">
            <svg
              width="20"
              height="20"
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
            >
              <circle cx="11" cy="11" r="8" />
              <path d="m21 21-4.35-4.35" />
            </svg>
            Search
          </button>
        </div>

        <div id="queryHint" className="query-hint">
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            style={{ display: "inline-block", marginRight: 5 }}
          >
            <circle cx="12" cy="12" r="10" />
            <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
            <line x1="12" y1="17" x2="12.01" y2="17" />
          </svg>
          Search by name or paste a music URL (YouTube, SoundCloud, JioSaavn
          etc.)
        </div>
      </div>

      {/* Status bar */}
      <div id="status" className="status" />

      {/* Source Navigation tabs */}
      <div id="sourceNavigation" className="source-navigation" />

      {/* Results */}
      <div id="results" className="results-container" />
    </>
  );
}

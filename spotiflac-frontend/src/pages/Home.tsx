import { App } from "@/app";
import { useEffect, useRef } from "react";
import {
  IoGlobeOutline,
  IoHelpCircleOutline,
  IoMusicalNotes,
  IoSearch,
  IoVideocam,
} from "react-icons/io5";
import { Link } from "react-router-dom";

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
      <div className="header">
        <p>
          Download high-quality music from YouTube, SoundCloud, JioSaavn &amp;
          more
          <br />
          <Link
            to="/bulk"
            style={{
              color: "var(--accent-color)",
              textDecoration: "none",
              fontWeight: 600,
              marginTop: 10,
              display: "inline-block",
            }}
          >
            Bulk &amp; Playlist Downloader →
          </Link>
        </p>
      </div>
      {/* Search Box */}
      <div className="search-box">
        <div className="search-type-selector">
          <button className="type-btn active" data-type="music">
            <IoMusicalNotes size={18} />
            Music
          </button>
          <button className="type-btn" data-type="video">
            <IoVideocam size={18} />
            Videos
          </button>
          <button className="type-btn" data-type="all">
            <IoGlobeOutline size={18} />
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
            <IoSearch size={20} />
            Search
          </button>
        </div>

        <div id="queryHint" className="query-hint">
          <IoHelpCircleOutline size={16} />
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

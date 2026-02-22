import { useState, useEffect, useCallback } from "react";
import { Link, Outlet } from "react-router-dom";

/* ---- Sun / Moon SVG icons ---- */
const SunIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <circle cx="12" cy="12" r="5" />
    <line x1="12" y1="1" x2="12" y2="3" />
    <line x1="12" y1="21" x2="12" y2="23" />
    <line x1="4.22" y1="4.22" x2="5.64" y2="5.64" />
    <line x1="18.36" y1="18.36" x2="19.78" y2="19.78" />
    <line x1="1" y1="12" x2="3" y2="12" />
    <line x1="21" y1="12" x2="23" y2="12" />
    <line x1="4.22" y1="19.78" x2="5.64" y2="18.36" />
    <line x1="18.36" y1="5.64" x2="19.78" y2="4.22" />
  </svg>
);

const MoonIcon = () => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z" />
  </svg>
);

export default function RootLayout() {
  /* ---- Theme state ---- */
  const [isLight, setIsLight] = useState(() => {
    const saved = localStorage.getItem("theme");
    return saved === "light";
  });

  // Apply theme class on mount and whenever isLight changes
  useEffect(() => {
    const root = document.documentElement;
    const body = document.body;
    if (isLight) {
      root.classList.add("light-theme");
      body.classList.add("light-theme");
    } else {
      root.classList.remove("light-theme");
      body.classList.remove("light-theme");
    }
    localStorage.setItem("theme", isLight ? "light" : "dark");
  }, [isLight]);

  const toggleTheme = useCallback(() => setIsLight((prev) => !prev), []);

  return (
    <>
      {/* Toast container — always present */}
      <div id="toastContainer" className="toast-container" />

      <div className="container">
        {/* Header */}
        <div className="header">
          <button className="theme-toggle" id="themeToggle" onClick={toggleTheme} title={isLight ? "Switch to Dark" : "Switch to Light"}>
            {isLight ? <SunIcon /> : <MoonIcon />}
          </button>
          <h1>
            <Link to="/" style={{ textDecoration: "none", color: "inherit" }}>
              <svg
                width="32"
                height="32"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                style={{ display: "inline-block", marginRight: 10 }}
              >
                <circle cx="12" cy="12" r="3" />
                <path d="M12 1v6m0 6v6m11-7h-6m-6 0H1" />
              </svg>
              Universal Music Downloader
            </Link>
          </h1>
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

        {/* Page content */}
        <Outlet />

        {/* Download Manager Panel */}
        <div id="downloadManager" className="download-manager">
          <div className="download-manager-header">
            <h3>
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                <polyline points="7,10 12,15 17,10" />
                <line x1="12" y1="15" x2="12" y2="3" />
              </svg>
              Downloads
            </h3>
            <div className="download-manager-controls">
              <select id="downloadFilter">
                <option value="all">All</option>
                <option value="downloading">Downloading</option>
                <option value="queued">Queued</option>
                <option value="complete">Complete</option>
                <option value="error">Failed</option>
              </select>
              <button id="clearFinished" title="Clear Finished">
                <svg
                  width="14"
                  height="14"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                >
                  <polyline points="3,6 5,6 21,6" />
                  <path d="M19,6v14a2,2,0,0,1-2,2H7a2,2,0,0,1-2-2V6M8,6V4a2,2,0,0,1,2-2h4a2,2,0,0,1,2,2v2" />
                </svg>
              </button>
              <button id="closeDownloadManager" title="Close">
                &times;
              </button>
            </div>
          </div>
          <div id="downloadList" className="download-list">
            <div
              style={{
                padding: 20,
                textAlign: "center",
                color: "var(--text-secondary)",
              }}
            >
              No downloads yet
            </div>
          </div>
        </div>

        {/* Download Toggle Button */}
        <button id="downloadToggle" className="download-manager-toggle">
          <svg
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
          >
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7,10 12,15 17,10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
          <span
            id="downloadBadge"
            className="badge"
            style={{ display: "none" }}
          >
            0
          </span>
        </button>
      </div>
    </>
  );
}

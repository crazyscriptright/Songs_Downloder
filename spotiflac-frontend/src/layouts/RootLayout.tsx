import { useCallback, useEffect, useState } from "react";
import {
  IoClose,
  IoDownloadOutline,
  IoMoon,
  IoSparkles,
  IoSunny,
  IoTrashOutline,
} from "react-icons/io5";
import { Link, Outlet } from "react-router-dom";

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
          <button
            className="theme-toggle"
            id="themeToggle"
            onClick={toggleTheme}
            title={isLight ? "Switch to Dark" : "Switch to Light"}
          >
            {isLight ? <IoSunny size={20} /> : <IoMoon size={20} />}
          </button>
          <h1>
            <Link
              to="/"
              className="header-title-link"
              style={{
                textDecoration: "none",
                color: "inherit",
              }}
            >
              <IoSparkles size={32} className="header-title-icon" />
              Universal Music Downloader
            </Link>
          </h1>
        </div>

        {/* Page content */}
        <Outlet />

        {/* Download Manager Panel */}
        <div id="downloadManager" className="download-manager">
          <div className="download-manager-header">
            <h3>
              <IoDownloadOutline size={18} />
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
                <IoTrashOutline size={14} />
              </button>
              <button id="closeDownloadManager" title="Close">
                <IoClose size={20} />
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
          <IoDownloadOutline size={24} />
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

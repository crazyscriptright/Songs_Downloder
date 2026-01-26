import React, { useState, useEffect } from "react";
import Header from "../components/Header";
import BulkUrlsTab from "../components/BulkUrlsTab";
import PlaylistTab from "../components/PlaylistTab";
import DownloadManager from "../components/DownloadManager";
import { useDownloadManager } from "../hooks/useDownloadManager";

export default function Bulk() {
  const [activeTab, setActiveTab] = useState("bulk");
  const [isManagerVisible, setIsManagerVisible] = useState(false);
  const { downloads, updateDownloads, downloadViaProxy, autoDownloadedIds } =
    useDownloadManager();

  // Theme toggle
  const toggleTheme = () => {
    document.body.classList.toggle("light-theme");
    const theme = document.body.classList.contains("light-theme")
      ? "light"
      : "dark";
    localStorage.setItem("theme", theme);
  };

  // Load saved theme
  useEffect(() => {
    const savedTheme = localStorage.getItem("theme");
    if (savedTheme === "light") {
      document.body.classList.add("light-theme");
    }
  }, []);

  return (
    <div className="max-w-[1400px] mx-auto p-5">
      <Header
        title="Bulk & Playlist Downloader"
        subtitle="Download multiple songs or entire playlists at once"
        showHomeLink={true}
        onThemeToggle={toggleTheme}
      />

      {/* Tabs */}
      <div className="flex gap-3 mb-8 justify-center">
        <button
          onClick={() => setActiveTab("bulk")}
          className={`px-8 py-3 text-base font-semibold rounded-lg cursor-pointer transition-all border-2 ${
            activeTab === "bulk" ? "gradient-secondary text-white" : ""
          }`}
          style={
            activeTab === "bulk"
              ? { borderColor: "var(--accent-color)" }
              : {
                  background: "var(--bg-card)",
                  color: "var(--text-secondary)",
                  borderColor: "var(--border-color)",
                }
          }
          onMouseEnter={(e) => {
            if (activeTab !== "bulk") {
              e.currentTarget.style.background = "var(--accent-color)";
              e.currentTarget.style.color = "var(--bg-primary)";
            }
          }}
          onMouseLeave={(e) => {
            if (activeTab !== "bulk") {
              e.currentTarget.style.background = "var(--bg-card)";
              e.currentTarget.style.color = "var(--text-secondary)";
            }
          }}
        >
          Bulk URLs
        </button>
        <button
          onClick={() => setActiveTab("playlist")}
          className={`px-8 py-3 text-base font-semibold rounded-lg cursor-pointer transition-all border-2 ${
            activeTab === "playlist" ? "gradient-secondary text-white" : ""
          }`}
          style={
            activeTab === "playlist"
              ? { borderColor: "var(--accent-color)" }
              : {
                  background: "var(--bg-card)",
                  color: "var(--text-secondary)",
                  borderColor: "var(--border-color)",
                }
          }
          onMouseEnter={(e) => {
            if (activeTab !== "playlist") {
              e.currentTarget.style.background = "var(--accent-color)";
              e.currentTarget.style.color = "var(--bg-primary)";
            }
          }}
          onMouseLeave={(e) => {
            if (activeTab !== "playlist") {
              e.currentTarget.style.background = "var(--bg-card)";
              e.currentTarget.style.color = "var(--text-secondary)";
            }
          }}
        >
          Playlist
        </button>
      </div>

      {/* Tab Content */}
      {activeTab === "bulk" && (
        <BulkUrlsTab
          downloads={downloads}
          updateDownloads={updateDownloads}
          autoDownloadedIds={autoDownloadedIds}
        />
      )}
      {activeTab === "playlist" && (
        <PlaylistTab
          downloads={downloads}
          updateDownloads={updateDownloads}
          downloadViaProxy={downloadViaProxy}
        />
      )}

      {/* Download Manager */}
      <DownloadManager
        downloads={downloads}
        isVisible={isManagerVisible}
        onToggle={() => setIsManagerVisible(!isManagerVisible)}
      />
    </div>
  );
}

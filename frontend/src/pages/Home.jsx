import React, { useState, useEffect, useRef } from "react";
import { Link } from "react-router-dom";
import SearchBox from "../components/SearchBox";
import SearchResults from "../components/SearchResults";
import DownloadManager from "../components/DownloadManager";
import { useDownloadManager } from "../hooks/useDownloadManager";
import { getApiBaseUrl } from "../config";

export default function Home() {
  const [searchType, setSearchType] = useState("music");
  const [searchQuery, setSearchQuery] = useState("");
  const [searchResults, setSearchResults] = useState(null);
  const [isSearching, setIsSearching] = useState(false);
  const [statusMessage, setStatusMessage] = useState(null);
  const [isManagerVisible, setIsManagerVisible] = useState(false);
  const { downloads, updateDownloads, downloadViaProxy, autoDownloadedIds } =
    useDownloadManager();

  // Helper function to detect if query is a URL
  const isUrl = (query) => {
    const musicUrlPatterns = [
      /youtube\.com\/watch/i,
      /youtu\.be\//i,
      /music\.youtube\.com/i,
      /jiosaavn\.com\//i,
      /saavn\.com\//i,
      /soundcloud\.com\//i,
      /spotify\.com\//i,
      /gaana\.com\//i,
      /wynk\.in\//i,
    ];
    return musicUrlPatterns.some(pattern => pattern.test(query));
  };

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

  // Perform search
  const performSearch = async (query, type) => {
    if (!query.trim()) return;

    setIsSearching(true);
    setSearchResults(null);

    try {
      // Check if query is a URL
      if (isUrl(query)) {
        setStatusMessage({
          type: "searching",
          text: "Validating URL...",
        });

        // Use the unified /search endpoint for URL handling
        const response = await fetch(`${getApiBaseUrl()}/search`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ query, type }),
        });

        const data = await response.json();
        
        if (data.status === "started" && data.search_id) {
          // Poll for results
          const pollResults = async (searchId) => {
            const maxAttempts = 20;
            let attempts = 0;

            while (attempts < maxAttempts) {
              await new Promise(resolve => setTimeout(resolve, 500));
              
              const statusResponse = await fetch(`${getApiBaseUrl()}/search_status/${searchId}`);
              const statusData = await statusResponse.json();

              if (statusData.status === "complete") {
                setSearchResults({ ...statusData, searchType: type });
                if (statusData.query_type === "url" && statusData.direct_url) {
                  const urlData = statusData.direct_url[0];
                  setStatusMessage({
                    type: "complete",
                    text: `URL validated: ${urlData.title || 'Ready to download'}`,
                  });
                } else {
                  setStatusMessage({
                    type: "complete",
                    text: "URL processed successfully",
                  });
                }
                return;
              } else if (statusData.status === "error") {
                setStatusMessage({
                  type: "error",
                  text: statusData.error || "URL validation failed",
                });
                return;
              }

              attempts++;
            }

            setStatusMessage({
              type: "error",
              text: "URL validation timeout",
            });
          };

          await pollResults(data.search_id);
        }
      } else {
        // For video searches, only use ytvideo endpoint
        if (type === "video") {
          setStatusMessage({
            type: "searching",
            text: "Searching YouTube videos...",
          });

          const results = {
            jiosaavn: [],
            ytmusic: [],
            soundcloud: [],
            ytvideo: [],
          };

          try {
            const response = await fetch(`${getApiBaseUrl()}/search/ytvideo`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({ query, type }),
            });

            const data = await response.json();
            results.ytvideo = data.results || [];

            setSearchResults({ ...results, searchType: type });
            setStatusMessage({
              type: "complete",
              text: `Found ${results.ytvideo.length} video results`,
            });
          } catch (error) {
            console.error("Error searching ytvideo:", error);
            setStatusMessage({
              type: "error",
              text: "Search failed. Please try again.",
            });
          }
        } else {
          // For music searches, search all music platforms
          setStatusMessage({
            type: "searching",
            text: "Searching across all platforms...",
          });

          const endpoints = ["jiosaavn", "ytmusic", "soundcloud"];
          const results = {
            jiosaavn: [],
            ytmusic: [],
            soundcloud: [],
            ytvideo: [],
          };

          let completedSources = 0;

          const searchPromises = endpoints.map(async (source) => {
            try {
              const response = await fetch(
                `${getApiBaseUrl()}/search/${source}`,
                {
                  method: "POST",
                  headers: { "Content-Type": "application/json" },
                  body: JSON.stringify({ query, type }),
                },
              );

              const data = await response.json();
              results[source] = data.results || [];
              completedSources++;

              // Update results as they come in
              setSearchResults({ ...results, searchType: type });
              setStatusMessage({
                type: "searching",
                text: `Found results from ${completedSources}/${endpoints.length} sources`,
              });
            } catch (error) {
              console.error(`Error searching ${source}:`, error);
              completedSources++;
            }
          });

          await Promise.allSettled(searchPromises);

          const totalResults = Object.values(results).reduce(
            (sum, arr) => sum + arr.length,
            0,
          );
          setStatusMessage({
            type: "complete",
            text: `Found ${totalResults} results across all platforms`,
          });
        }
      }
    } catch (error) {
      console.error("Search error:", error);
      setStatusMessage({
        type: "error",
        text: "Search failed. Please try again.",
      });
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="max-w-[1400px] mx-auto relative">
      {/* Header */}
      <div className="text-center py-8 mb-8 relative">
        <button
          onClick={toggleTheme}
          className="absolute top-8 right-5 px-4 py-2 rounded-3xl border-2 cursor-pointer transition-all font-medium flex items-center gap-2"
          style={{
            background: "var(--bg-card)",
            borderColor: "var(--border-color)",
            color: "var(--text-secondary)",
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = "var(--accent-color)";
            e.currentTarget.style.color = "var(--bg-primary)";
            e.currentTarget.style.borderColor = "var(--accent-color)";
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = "var(--bg-card)";
            e.currentTarget.style.color = "var(--text-secondary)";
            e.currentTarget.style.borderColor = "var(--border-color)";
          }}
        >
          🌓 Theme
        </button>

        <h1
          className="text-5xl font-bold mb-4 flex items-center justify-center"
          style={{ color: "var(--accent-color)" }}
        >
          <svg
            width="32"
            height="32"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            className="mr-3"
          >
            <circle cx="12" cy="12" r="3"></circle>
            <path d="M12 1v6m0 6v6m11-7h-6m-6 0H1"></path>
          </svg>
          Universal Music Downloader
        </h1>
        <p className="text-lg mb-2" style={{ color: "var(--text-secondary)" }}>
          Download high-quality music from YouTube, SoundCloud, JioSaavn & more
        </p>
        <Link
          to="/bulk"
          className="inline-block mt-3 font-semibold"
          style={{ color: "var(--accent-color)", textDecoration: "none" }}
        >
          Bulk & Playlist Downloader →
        </Link>
      </div>

      {/* Search Box */}
      <SearchBox
        searchType={searchType}
        setSearchType={setSearchType}
        searchQuery={searchQuery}
        setSearchQuery={setSearchQuery}
        onSearch={performSearch}
        isSearching={isSearching}
      />

      {/* Status Message */}
      {statusMessage && (
        <div
          className={`text-center py-5 px-6 rounded-2xl my-5 mx-auto max-w-[600px] border-2 font-medium text-lg transition-all ${
            statusMessage.type === "searching" ? "opacity-100" : "opacity-100"
          }`}
          style={{
            background:
              statusMessage.type === "searching"
                ? "var(--status-loading-bg)"
                : statusMessage.type === "complete"
                  ? "var(--status-success-bg)"
                  : "var(--status-error-bg)",
            borderColor:
              statusMessage.type === "searching"
                ? "var(--status-loading-border)"
                : statusMessage.type === "complete"
                  ? "var(--status-success-border)"
                  : "var(--status-error-border)",
            color:
              statusMessage.type === "searching"
                ? "var(--download-color)"
                : statusMessage.type === "complete"
                  ? "var(--success-color)"
                  : "var(--error-color)",
          }}
        >
          {statusMessage.type === "searching" && (
            <div className="inline-block w-5 h-5 border-2 border-current border-t-transparent rounded-full animate-spin mr-2" />
          )}
          {statusMessage.text}
        </div>
      )}

      {/* Search Results */}
      {searchResults && (
        <SearchResults
          results={searchResults}
          downloads={downloads}
          updateDownloads={updateDownloads}
          downloadViaProxy={downloadViaProxy}
          autoDownloadedIds={autoDownloadedIds}
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

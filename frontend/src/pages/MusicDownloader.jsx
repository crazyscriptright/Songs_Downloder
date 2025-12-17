import { useState } from 'react';
import { Header } from '../components/layout/Header';
import { DownloadManager } from '../components/layout/DownloadManager';
import { AnimatedBackground } from '../components/layout/AnimatedBackground';
import { useTheme, useDownloadManager } from '../hooks/useDownload';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:5001';

export default function MusicDownloader() {
  const { theme, toggleTheme } = useTheme();
  const downloadManager = useDownloadManager();
  
  const [searchType, setSearchType] = useState('music');
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState(null);
  const [isSearching, setIsSearching] = useState(false);
  const [activeResultTab, setActiveResultTab] = useState('ytmusic');

  const handleSearch = async () => {
    if (!searchQuery.trim()) return;
    setIsSearching(true);
    
    try {
      const response = await fetch(`${API_URL}/search`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: searchQuery, search_type: searchType })
      });
      const data = await response.json();
      if (data.search_id) pollSearchResults(data.search_id);
    } catch (error) {
      setIsSearching(false);
    }
  };

  const pollSearchResults = async (searchId) => {
    let attempts = 0;
    const interval = setInterval(async () => {
      if (attempts++ >= 30) {
        clearInterval(interval);
        setIsSearching(false);
        return;
      }
      try {
        const response = await fetch(`${API_URL}/search_status/${searchId}`);
        const data = await response.json();
        if (data.status === 'complete') {
          clearInterval(interval);
          setSearchResults(data);
          setIsSearching(false);
        }
      } catch (error) {
        clearInterval(interval);
        setIsSearching(false);
      }
    }, 1000);
  };

  const styles = {
    container: {
      minHeight: '100vh',
      backgroundColor: 'var(--bg-primary)',
      color: 'var(--text-primary)',
      padding: '20px',
      position: 'relative',
      paddingBottom: '40px'
    },
    inner: {
      maxWidth: '1400px',
      margin: '0 auto',
      position: 'relative',
      zIndex: 1
    },
    searchBox: {
      padding: '50px',
      marginBottom: '40px',
      maxWidth: '800px',
      margin: '0 auto 40px auto',
      background: theme === 'light'
        ? 'rgba(255, 255, 255, 0.4)'
        : 'rgba(31, 31, 31, 0.4)',
      backdropFilter: 'blur(10px)',
      WebkitBackdropFilter: 'blur(10px)',
      borderRadius: '20px',
      border: '1px solid var(--border-color)',
      boxShadow: theme === 'light'
        ? '0 8px 32px rgba(0, 0, 0, 0.1)'
        : '0 8px 32px rgba(0, 0, 0, 0.4)'
    },
    typeSelector: {
      display: 'flex',
      gap: '15px',
      marginBottom: '25px',
      justifyContent: 'center',
      flexWrap: 'wrap'
    },
    typeBtn: (isActive) => ({
      padding: '10px 25px',
      fontSize: '1em',
      fontWeight: 'bold',
      background: isActive 
        ? 'linear-gradient(135deg, var(--accent-color) 0%, var(--accent-secondary) 100%)'
        : 'var(--bg-card)',
      color: isActive ? 'var(--bg-primary)' : 'var(--text-secondary)',
      border: `2px solid ${isActive ? 'var(--accent-color)' : 'var(--border-color)'}`,
      borderRadius: '8px',
      cursor: 'pointer',
      transition: 'all 0.3s ease',
      display: 'flex',
      alignItems: 'center',
      gap: '8px',
      boxShadow: isActive 
        ? '0 4px 15px var(--shadow-color)'
        : '0 2px 8px rgba(0, 0, 0, 0.1)'
    }),
    searchInputGroup: {
      display: 'flex',
      gap: '15px',
      marginBottom: '15px',
      alignItems: 'stretch',
      justifyContent: 'center',
      maxWidth: '900px',
      margin: '0 auto 15px auto'
    },
    input: {
      flex: 1,
      maxWidth: '800px',
      padding: '12px 18px',
      fontSize: '1.2em',
      border: '2px solid var(--border-color)',
      borderRadius: '15px',
      background: 'var(--bg-card)',
      color: 'var(--text-primary)',
      outline: 'none',
      transition: 'all 0.3s ease',
      boxShadow: '0 2px 10px rgba(0, 0, 0, 0.05)'
    },
    searchBtn: {
      padding: '18px 45px',
      fontSize: '1.2em',
      fontWeight: '600',
      background: 'linear-gradient(135deg, var(--accent-color) 0%, var(--accent-secondary) 100%)',
      color: 'white',
      border: 'none',
      borderRadius: '15px',
      cursor: 'pointer',
      transition: 'all 0.3s ease',
      minWidth: '140px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '8px',
      boxShadow: '0 4px 15px var(--shadow-color)',
      whiteSpace: 'nowrap'
    },
    searchBtnDisabled: {
      opacity: 0.6,
      cursor: 'not-allowed',
      transform: 'none'
    },
    queryHint: {
      textAlign: 'center',
      fontSize: '0.9em',
      color: 'var(--text-tertiary)',
      marginTop: '10px',
      padding: '0 10px'
    },
    resultsGrid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
      gap: '20px'
    },
    sourceNavigation: {
      padding: '15px',
      marginBottom: '30px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '15px',
      flexWrap: 'wrap',
      WebkitBackdropFilter: 'blur(10px)',
    },
    sourceNavBtn: (isActive) => ({
      padding: '12px 25px',
      fontSize: '1em',
      fontWeight: 'bold',
      background: isActive 
        ? 'linear-gradient(135deg, var(--accent-color) 0%, var(--accent-secondary) 100%)'
        : 'var(--bg-card)',
      color: isActive ? 'var(--bg-primary)' : 'var(--text-secondary)',
      border: `2px solid ${isActive ? 'var(--accent-color)' : 'var(--border-color)'}`,
      borderRadius: '8px',
      cursor: 'pointer',
      transition: 'all 0.3s ease',
      display: 'flex',
      alignItems: 'center',
      gap: '10px',
      boxShadow: isActive 
        ? '0 4px 15px var(--shadow-color)'
        : '0 2px 8px rgba(0, 0, 0, 0.1)'
    }),
    sourceSection: {
      background: theme === 'light'
        ? 'rgba(255, 255, 255, 0.5)'
        : 'rgba(31, 31, 31, 0.5)',
      borderRadius: '15px',
      padding: '20px',
      backdropFilter: 'blur(10px)',
      WebkitBackdropFilter: 'blur(10px)',
      border: `1px solid var(--border-color)`
    },
    sectionTitle: {
      color: 'var(--accent-color)',
      marginBottom: '16px',
      fontSize: '1.3em',
      fontWeight: '700',
      textShadow: theme === 'light'
        ? '0 2px 4px rgba(0, 0, 0, 0.05)'
        : '0 2px 4px rgba(0, 0, 0, 0.3)'
    },
    resultCard: {
      background: 'var(--bg-card)',
      borderRadius: '16px',
      padding: '16px',
      marginBottom: '16px',
      border: '1px solid var(--border-color)',
      transition: 'all 0.3s ease',
      boxShadow: theme === 'light'
        ? '0 4px 15px rgba(0, 0, 0, 0.08)'
        : '0 4px 15px rgba(0, 0, 0, 0.4)',
      backdropFilter: 'blur(5px)',
      WebkitBackdropFilter: 'blur(5px)'
    },
    thumbnail: (isVideo) => ({
      width: '100%',
      aspectRatio: isVideo ? '16/9' : '1/1',
      objectFit: 'cover',
      borderRadius: '12px',
      marginBottom: '12px',
      boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)'
    }),
    downloadBtn: {
      width: '100%',
      padding: '12px 15px',
      borderRadius: '10px',
      border: 'none',
      background: 'var(--accent-color)',
      color: 'white',
      fontSize: '0.95em',
      fontWeight: '700',
      cursor: 'pointer',
      transition: 'all 0.3s ease',
      boxShadow: '0 4px 12px var(--shadow-color)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '8px'
    }
  };

  return (
    <div style={styles.container} className="music-downloader">
      <AnimatedBackground theme={theme} />
      <div style={styles.inner}>
        <Header toggleTheme={toggleTheme} theme={theme} />
        
        <div style={styles.searchBox} className="search-box">
          {/* Search Type Selector */}
          <div style={styles.typeSelector} className="type-selector">
            <button
              onClick={() => setSearchType('music')}
              style={styles.typeBtn(searchType === 'music')}
              className="type-btn"
              data-label="Music"
              onMouseEnter={(e) => {
                if (searchType !== 'music') {
                  e.currentTarget.style.background = 'var(--accent-color)';
                  e.currentTarget.style.color = 'var(--bg-primary)';
                }
              }}
              onMouseLeave={(e) => {
                if (searchType !== 'music') {
                  e.currentTarget.style.background = 'var(--bg-card)';
                  e.currentTarget.style.color = 'var(--text-secondary)';
                }
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ display: 'inline-block' }}>
                <path d="M9 18V5l12-2v13"></path>
                <circle cx="6" cy="18" r="3"></circle>
                <circle cx="18" cy="16" r="3"></circle>
              </svg>
              <span className="btn-label">Music</span>
            </button>
            <button
              onClick={() => setSearchType('video')}
              style={styles.typeBtn(searchType === 'video')}
              className="type-btn"
              data-label="Videos"
              onMouseEnter={(e) => {
                if (searchType !== 'video') {
                  e.currentTarget.style.background = 'var(--accent-color)';
                  e.currentTarget.style.color = 'var(--bg-primary)';
                }
              }}
              onMouseLeave={(e) => {
                if (searchType !== 'video') {
                  e.currentTarget.style.background = 'var(--bg-card)';
                  e.currentTarget.style.color = 'var(--text-secondary)';
                }
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ display: 'inline-block' }}>
                <polygon points="23 7 16 12 23 17 23 7"></polygon>
                <rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect>
              </svg>
              <span className="btn-label">Videos</span>
            </button>
            <button
              onClick={() => setSearchType('all')}
              style={styles.typeBtn(searchType === 'all')}
              className="type-btn"
              data-label="All Sources"
              onMouseEnter={(e) => {
                if (searchType !== 'all') {
                  e.currentTarget.style.background = 'var(--accent-color)';
                  e.currentTarget.style.color = 'var(--bg-primary)';
                }
              }}
              onMouseLeave={(e) => {
                if (searchType !== 'all') {
                  e.currentTarget.style.background = 'var(--bg-card)';
                  e.currentTarget.style.color = 'var(--text-secondary)';
                }
              }}
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ display: 'inline-block' }}>
                <circle cx="12" cy="12" r="10"></circle>
                <line x1="2" y1="12" x2="22" y2="12"></line>
                <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"></path>
              </svg>
              <span className="btn-label">All Sources</span>
            </button>
          </div>

          {/* Search Input */}
          <div style={styles.searchInputGroup} className="search-input-group">
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              placeholder="Enter song name, artist, or paste URL..."
              style={styles.input}
              onFocus={(e) => {
                e.target.style.borderColor = 'var(--accent-color)';
                e.target.style.boxShadow = '0 0 0 4px var(--shadow-color)';
                e.target.style.transform = 'translateY(-2px)';
              }}
              onBlur={(e) => {
                e.target.style.borderColor = 'var(--border-color)';
                e.target.style.boxShadow = 'none';
                e.target.style.transform = 'translateY(0)';
              }}
            />
            <button
              onClick={handleSearch}
              disabled={isSearching || !searchQuery.trim()}
              style={{
                ...styles.searchBtn,
                ...(isSearching || !searchQuery.trim() ? styles.searchBtnDisabled : {})
              }}
              onMouseEnter={(e) => {
                if (!isSearching && searchQuery.trim()) {
                  e.currentTarget.style.transform = 'translateY(-3px)';
                  e.currentTarget.style.boxShadow = '0 8px 25px var(--shadow-color)';
                }
              }}
              onMouseLeave={(e) => {
                if (!isSearching && searchQuery.trim()) {
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = 'none';
                }
              }}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="8"></circle>
                <path d="m21 21-4.35-4.35"></path>
              </svg>
              {isSearching ? 'Searching...' : 'Search'}
            </button>
          </div>

          <div style={styles.queryHint}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ display: 'inline-block', marginRight: '5px' }}>
              <circle cx="12" cy="12" r="10"></circle>
              <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path>
              <line x1="12" y1="17" x2="12.01" y2="17"></line>
            </svg>
            Search by name or paste a music URL (YouTube, SoundCloud, JioSaavn etc.)
          </div>
        </div>

        {/* Results with Tabs */}
        {searchResults && (
          <div>
            {/* Tab Navigation */}
            {(['ytmusic', 'ytvideo', 'jiosaavn', 'soundcloud'].filter(source => 
              searchResults[source]?.length > 0
            ).length > 0) && (
              <div style={styles.sourceNavigation}>
                {['ytmusic', 'ytvideo', 'jiosaavn', 'soundcloud'].map(source => {
                  const results = searchResults[source];
                  if (!results || results.length === 0) return null;
                  
                  const sourceNames = {
                    'ytmusic': 'YouTube Music',
                    'ytvideo': 'YouTube Videos',
                    'jiosaavn': 'JioSaavn',
                    'soundcloud': 'SoundCloud'
                  };
                  
                  return (
                    <button
                      key={source}
                      onClick={() => setActiveResultTab(source)}
                      style={styles.sourceNavBtn(activeResultTab === source)}
                      onMouseEnter={(e) => {
                        if (activeResultTab !== source) {
                          e.currentTarget.style.transform = 'translateY(-2px)';
                        }
                      }}
                      onMouseLeave={(e) => {
                        if (activeResultTab !== source) {
                          e.currentTarget.style.transform = 'translateY(0)';
                        }
                      }}
                    >
                      {sourceNames[source]}
                      <span style={{
                        background: activeResultTab === source 
                          ? 'rgba(0, 0, 0, 0.2)' 
                          : 'rgba(0, 0, 0, 0.1)',
                        padding: '2px 8px',
                        borderRadius: '10px',
                        fontSize: '0.85em'
                      }}>
                        {results.length}
                      </span>
                    </button>
                  );
                })}
              </div>
            )}

            {/* Tab Content */}
            {['ytmusic', 'ytvideo', 'jiosaavn', 'soundcloud'].map(source => {
              const results = searchResults[source];
              if (!results || results.length === 0 || activeResultTab !== source) return null;
              
              const sourceNames = {
                'ytmusic': 'YouTube Music',
                'ytvideo': 'YouTube Videos',
                'jiosaavn': 'JioSaavn',
                'soundcloud': 'SoundCloud'
              };
              
              return (
                <div key={source} style={styles.sourceSection}>
                  <h3 style={styles.sectionTitle}>
                    {sourceNames[source]}
                  </h3>
                  <div style={styles.resultsGrid}>
                    {results.map((item, idx) => (
                      <div
                        key={idx}
                        style={styles.resultCard}
                        onMouseEnter={(e) => {
                          e.currentTarget.style.transform = 'translateY(-4px)';
                          e.currentTarget.style.boxShadow = theme === 'light'
                            ? '0 8px 25px rgba(16, 185, 129, 0.2), 0 4px 12px rgba(0, 0, 0, 0.1)'
                            : '0 8px 25px rgba(52, 211, 153, 0.3), 0 4px 12px rgba(0, 0, 0, 0.5)';
                          e.currentTarget.style.borderColor = 'var(--accent-color)';
                        }}
                        onMouseLeave={(e) => {
                          e.currentTarget.style.transform = 'translateY(0)';
                          e.currentTarget.style.boxShadow = theme === 'light'
                            ? '0 4px 15px rgba(0, 0, 0, 0.08)'
                            : '0 4px 15px rgba(0, 0, 0, 0.4)';
                          e.currentTarget.style.borderColor = 'var(--border-color)';
                        }}
                      >
                        {item.thumbnail && (
                          <img src={item.thumbnail} alt={item.title} style={styles.thumbnail(source === 'ytvideo')} />
                        )}
                        <h4 style={{ color: 'var(--text-primary)', marginBottom: '8px', fontWeight: '600' }}>
                          {item.title}
                        </h4>
                        {item.artist && (
                          <p style={{ color: 'var(--text-secondary)', fontSize: '0.85em', marginBottom: '12px' }}>
                            {item.artist}
                          </p>
                        )}
                        <button
                          onClick={() => {
                            const id = Date.now().toString();
                            downloadManager.addDownload(id, {
                              title: item.title,
                              url: item.url,
                              status: 'downloading',
                              progress: 0
                            });
                          }}
                          style={styles.downloadBtn}
                          onMouseEnter={(e) => {
                            e.currentTarget.style.transform = 'translateY(-2px)';
                            e.currentTarget.style.boxShadow = '0 6px 20px var(--shadow-color)';
                          }}
                          onMouseLeave={(e) => {
                            e.currentTarget.style.transform = 'translateY(0)';
                            e.currentTarget.style.boxShadow = '0 4px 12px var(--shadow-color)';
                          }}
                        >
                          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5">
                            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                            <polyline points="7 10 12 15 17 10"></polyline>
                            <line x1="12" y1="15" x2="12" y2="3"></line>
                          </svg>
                          Download
                        </button>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
      
      <DownloadManager {...downloadManager} />
    </div>
  );
}

import { Link, useLocation } from 'react-router-dom';

export const Header = ({ toggleTheme, theme }) => {
  const location = useLocation();
  
  const styles = {
    header: {
      marginBottom: '60px', 
      padding: '40px 20px',
      position: 'relative'
    },
    topBar: {
      display: 'flex',
      justifyContent: 'space-between',
      alignItems: 'center',
      marginBottom: '30px',
      position: 'relative',
      zIndex: 10
    },
    logoContainer: {
      background: 'var(--bg-card)',
      color: 'var(--text-secondary)',
      textDecoration: 'none',
      padding: '10px 16px',
      borderRadius: '12px',
      border: '2px solid var(--border-color)',
      transition: 'all 0.3s ease',
      fontWeight: '600',
      display: 'flex',
      alignItems: 'center',
      gap: '10px',
      fontSize: '1em',
      boxShadow: theme === 'light'
        ? '0 2px 8px rgba(0, 0, 0, 0.08)'
        : '0 2px 8px rgba(0, 0, 0, 0.3)'
    },
    logoIcon: {
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      width: '24px',
      height: '24px'
    },
    logoImage: {
      width: '24px',
      height: '24px',
      objectFit: 'contain'
    },
    logoText: {
      fontWeight: '700',
      fontSize: '1.1em'
    },
    themeToggle: {
      background: theme === 'light'
        ? 'rgba(255, 255, 255, 0.8)'
        : 'rgba(31, 31, 31, 0.8)',
      border: '2px solid var(--border-color)',
      borderRadius: '12px',
      padding: '12px',
      cursor: 'pointer',
      transition: 'all 0.3s ease',
      color: 'var(--text-primary)',
      boxShadow: '0 4px 15px rgba(0,0,0,0.15)',
      fontSize: '1.2em',
      backdropFilter: 'blur(10px)',
      WebkitBackdropFilter: 'blur(10px)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      width: '48px',
      height: '48px'
    }
  };
  
  return (
    <header style={styles.header} className="header">
      <div style={styles.topBar} className="header-top-bar">
        <div style={styles.logoContainer} className="logo-link">
          <div style={styles.logoIcon}>
            <img src="/static/fevicon2.png" alt="Logo" style={styles.logoImage} />
          </div>
          <span className="logo-text" style={styles.logoText}>UMD</span>
        </div>
        
        <button
          onClick={toggleTheme}
          style={styles.themeToggle}
          className="theme-toggle-btn"
          title="Toggle theme"
          onMouseEnter={(e) => {
            e.currentTarget.style.transform = 'scale(1.1) rotate(15deg)';
            e.currentTarget.style.boxShadow = '0 6px 20px rgba(0,0,0,0.2)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.transform = 'scale(1) rotate(0deg)';
            e.currentTarget.style.boxShadow = '0 4px 15px rgba(0,0,0,0.15)';
          }}
        >
          {theme === 'dark' ? '☀️' : '🌙'}
        </button>
      </div>

      {/* Title Section */}
      <div style={{
        textAlign: 'center',
        marginBottom: '15px'
      }}>
        <h1 style={{
          fontFamily: 'var(--font-display)',
          fontSize: 'clamp(1.2em, 8vw, 3.2em)',
          fontWeight: '800',
          color: 'var(--text-primary)',
          letterSpacing: '-0.02em',
          margin: 0,
          minWidth: '0',
          wordBreak: 'break-word',
          textShadow: theme === 'light'
            ? '0 2px 8px rgba(0, 0, 0, 0.05)'
            : '0 2px 8px rgba(0, 0, 0, 0.3)'
        }}>
          Universal Music Downloader
        </h1>
      </div>

      {/* Subtitle */}
      <p style={{ 
        color: 'var(--text-secondary)', 
        fontSize: 'clamp(0.9em, 2.5vw, 1.1em)',
        marginBottom: '0',
        fontWeight: '400',
        opacity: '0.8',
        textAlign: 'center'
      }}>
        Download music from YouTube, SoundCloud, JioSaavn & more
        <br />
        <Link 
          to="/bulk" 
          style={{
            color: 'var(--accent-color)',
            textDecoration: 'none',
            fontWeight: 700,
            marginTop: '10px',
            display: 'inline-block'
          }}
        >
          Bulk & Playlist Downloader →
        </Link>
      </p>
    </header>
  );
};


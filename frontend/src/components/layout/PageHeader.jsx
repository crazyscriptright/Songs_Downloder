import { Link } from 'react-router-dom';

export const PageHeader = ({ title, subtitle, showHomeLink = false, theme, toggleTheme }) => {
  const styles = {
    header: {
      textAlign: 'center',
      padding: '40px 20px',
      marginBottom: '60px',
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
    headerTitle: {
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
    },
    headerSubtitle: {
      color: 'var(--text-secondary)',
      fontSize: 'clamp(0.9em, 2.5vw, 1.1em)',
      marginBottom: '0',
      fontWeight: '400',
      opacity: '0.8',
      padding: '0 20px'
    },
    logoLink: {
      background: 'var(--bg-card)',
      color: 'var(--text-secondary)',
      textDecoration: 'none',
      padding: '10px 16px',
      borderRadius: '12px',
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
    <div style={styles.header} className="page-header">
      <div style={styles.topBar} className="header-top-bar">
        {showHomeLink ? (
          <Link
            to="/"
            style={styles.logoLink}
            className="logo-link"
            onMouseEnter={(e) => {
              e.currentTarget.style.background = 'var(--accent-color)';
              e.currentTarget.style.color = 'var(--bg-primary)';
              e.currentTarget.style.borderColor = 'var(--accent-color)';
              e.currentTarget.style.transform = 'translateY(-2px)';
              e.currentTarget.style.boxShadow = '0 4px 15px var(--shadow-color)';
            }}
            onMouseLeave={(e) => {
              e.currentTarget.style.background = 'var(--bg-card)';
              e.currentTarget.style.color = 'var(--text-secondary)';
              e.currentTarget.style.borderColor = 'var(--border-color)';
              e.currentTarget.style.transform = 'translateY(0)';
              e.currentTarget.style.boxShadow = theme === 'light'
                ? '0 2px 8px rgba(0, 0, 0, 0.08)'
                : '0 2px 8px rgba(0, 0, 0, 0.3)';
            }}
          >
            <div style={styles.logoIcon}>
              <img src="/static/fevicon2.png" alt="Logo" style={styles.logoImage} />
            </div>
            <span className="logo-text" style={styles.logoText}>SDL</span>
          </Link>
        ) : (
          <div style={styles.logoLink} className="logo-link">
            <div style={styles.logoIcon}>
              <img src="/static/fevicon2.png" alt="Logo" style={styles.logoImage} />
            </div>
            <span className="logo-text" style={styles.logoText}>UMD</span>
          </div>
        )}
        
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
      
      <h1 style={styles.headerTitle}>{title}</h1>
      <p style={styles.headerSubtitle}>{subtitle}</p>
    </div>
  );
};

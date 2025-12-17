export const ThemeToggle = ({ theme, toggleTheme }) => {
  const styles = {
    themeToggle: {
      position: 'fixed',
      top: '20px',
      right: '20px',
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
      zIndex: 1000,
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      width: '48px',
      height: '48px'
    }
  };

  return (
    <button
      onClick={toggleTheme}
      style={styles.themeToggle}
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
  );
};

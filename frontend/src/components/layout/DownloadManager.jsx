import { Button } from '../ui/FormComponents';

export const DownloadManager = ({ 
  downloads, 
  isVisible, 
  onToggle, 
  onClearFinished, 
  onCancel 
}) => {
  const downloadList = Object.entries(downloads);
  const activeCount = downloadList.filter(([, d]) => 
    d.status === 'downloading' || d.status === 'queued'
  ).length;

  return (
    <>
      {/* Toggle Button - Floating Action Button */}
      <button
        onClick={onToggle}
        style={{
          position: 'fixed',
          bottom: '24px',
          right: '24px',
          zIndex: 50,
          background: 'var(--accent-color)',
          color: 'white',
          padding: '16px',
          borderRadius: '50%',
          border: 'none',
          boxShadow: '0 4px 16px var(--shadow-color)',
          cursor: 'pointer',
          transition: 'all 0.3s ease',
          width: '60px',
          height: '60px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontSize: '1.5em'
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.transform = 'scale(1.1)';
          e.currentTarget.style.boxShadow = '0 6px 20px var(--shadow-color)';
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.transform = 'scale(1)';
          e.currentTarget.style.boxShadow = '0 4px 16px var(--shadow-color)';
        }}
      >
        ⬇️
        {activeCount > 0 && (
          <span style={{
            position: 'absolute',
            top: '-6px',
            right: '-6px',
            backgroundColor: '#ef4444',
            color: 'white',
            fontSize: '0.65em',
            fontWeight: '700',
            borderRadius: '50%',
            width: '22px',
            height: '22px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 2px 6px rgba(239, 68, 68, 0.4)'
          }}>
            {activeCount}
          </span>
        )}
      </button>

      {/* Download Manager Panel */}
      <div
        style={{
          position: 'fixed',
          top: 0,
          right: 0,
          height: '100%',
          width: '380px',
          backgroundColor: 'var(--bg-card)',
          borderLeft: '1px solid var(--border-color)',
          boxShadow: '-2px 0 20px rgba(0,0,0,0.15)',
          transform: isVisible ? 'translateX(0)' : 'translateX(100%)',
          transition: 'transform 0.3s ease',
          zIndex: 50,
          display: 'flex',
          flexDirection: 'column'
        }}
      >
        {/* Header */}
        <div style={{
          padding: '16px 20px',
          borderBottom: '1px solid var(--border-color)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          background: 'var(--accent-color)',
          color: 'white'
        }}>
          <h3 style={{ margin: 0, fontSize: '1.15em', fontWeight: '700', display: 'flex', alignItems: 'center', gap: '8px' }}>
            ⬇️ Downloads
          </h3>
          <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
            <button
              onClick={onClearFinished}
              style={{
                padding: '6px 12px',
                fontSize: '0.85em',
                backgroundColor: 'rgba(255,255,255,0.2)',
                color: 'white',
                border: 'none',
                borderRadius: '6px',
                cursor: 'pointer',
                fontWeight: '600',
                transition: 'all 0.2s ease'
              }}
              onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.3)'}
              onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.2)'}
            >
              Clear
            </button>
            <button
              onClick={onToggle}
              style={{
                padding: '6px',
                background: 'none',
                border: 'none',
                color: 'white',
                cursor: 'pointer',
                fontSize: '1.5em',
                lineHeight: '1',
                transition: 'transform 0.2s ease'
              }}
              onMouseEnter={(e) => e.currentTarget.style.transform = 'rotate(90deg)'}
              onMouseLeave={(e) => e.currentTarget.style.transform = 'rotate(0deg)'}
            >
              ×
            </button>
          </div>
        </div>

        {/* Download List */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '16px' }}>
          {downloadList.length === 0 ? (
            <div style={{
              textAlign: 'center',
              color: 'var(--text-tertiary)',
              padding: '40px 20px',
              fontSize: '0.95em'
            }}>
              No downloads yet
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {downloadList.map(([id, download]) => (
                <DownloadItem
                  key={id}
                  id={id}
                  download={download}
                  onCancel={onCancel}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </>
  );
};

const DownloadItem = ({ id, download, onCancel }) => {
  const getStatusColor = (status) => {
    switch(status) {
      case 'downloading': return 'var(--info-color)';
      case 'complete': return 'var(--success-color)';
      case 'error': return 'var(--error-color)';
      case 'queued': return 'var(--warning-color)';
      default: return 'var(--border-color)';
    }
  };

  return (
    <div 
      style={{
        backgroundColor: 'var(--bg-secondary)',
        borderRadius: '10px',
        padding: '14px',
        borderLeft: `4px solid ${getStatusColor(download.status)}`,
        transition: 'all 0.2s ease'
      }}
    >
      <div style={{ display: 'flex', alignItems: 'start', justifyContent: 'space-between', marginBottom: '10px' }}>
        <h4 style={{ 
          fontSize: '0.9em', 
          fontWeight: '600', 
          margin: 0,
          color: 'var(--text-primary)',
          flex: 1,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          paddingRight: '8px'
        }}>
          {download.title}
        </h4>
        {(download.status === 'downloading' || download.status === 'queued') && (
          <button
            onClick={() => onCancel(id)}
            style={{
              background: 'none',
              border: 'none',
              color: 'var(--error-color)',
              cursor: 'pointer',
              padding: '2px',
              fontSize: '1.1em',
              lineHeight: '1',
              transition: 'opacity 0.2s ease'
            }}
            onMouseEnter={(e) => e.currentTarget.style.opacity = '0.7'}
            onMouseLeave={(e) => e.currentTarget.style.opacity = '1'}
          >
            ×
          </button>
        )}
      </div>

      {download.progress !== undefined && (
        <div style={{ marginBottom: '8px' }}>
          <div style={{ 
            width: '100%', 
            borderRadius: '10px', 
            height: '6px',
            backgroundColor: 'var(--border-color)',
            overflow: 'hidden'
          }}>
            <div
              style={{
                height: '100%',
                borderRadius: '10px',
                width: `${download.progress}%`,
                backgroundColor: download.status === 'complete' ? 'var(--success-color)' :
                                download.status === 'error' ? 'var(--error-color)' :
                                'var(--accent-color)',
                transition: 'width 0.3s ease'
              }}
            />
          </div>
        </div>
      )}

      <div style={{ 
        display: 'flex', 
        alignItems: 'center', 
        justifyContent: 'space-between',
        fontSize: '0.8em',
        color: 'var(--text-tertiary)'
      }}>
        <span style={{ textTransform: 'capitalize' }}>{download.status}</span>
        {download.speed && <span>{download.speed}</span>}
      </div>
    </div>
  );
};

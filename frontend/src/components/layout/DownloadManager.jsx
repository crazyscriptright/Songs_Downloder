import { Button } from '../ui/FormComponents';

export const DownloadManager = ({ 
  downloads, 
  isVisible, 
  onToggle, 
  onClearFinished,
  onStopAll,
  onRemoveAll,
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
        className="fixed bottom-5 right-5 md:bottom-[30px] md:right-[30px] z-[999] bg-[var(--accent-color)] text-white rounded-full border-none shadow-[0_4px_20px_var(--shadow-color)] cursor-pointer transition-all duration-300 w-[60px] h-[60px] flex items-center justify-center hover:scale-110 hover:shadow-[0_6px_30px_var(--shadow-color)]"
      >
        <svg
          width="24"
          height="24"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        >
          <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
          <polyline points="7 10 12 15 17 10"></polyline>
          <line x1="12" y1="15" x2="12" y2="3"></line>
        </svg>
        {activeCount > 0 && (
          <span className="absolute -top-[5px] -right-[5px] bg-[var(--error-color)] text-white text-[0.6em] font-bold rounded-full w-6 h-6 flex items-center justify-center">
            {activeCount}
          </span>
        )}
      </button>

      {/* Download Manager Panel */}
      <div
        className={`fixed top-0 right-0 h-full w-full md:w-[420px] bg-[var(--bg-card)] border-l border-[var(--border-color)] shadow-[-2px_0_20px_rgba(0,0,0,0.15)] transition-transform duration-300 z-[998] flex flex-col ${
          isVisible ? 'translate-x-0' : 'translate-x-full'
        }`}
      >
        {/* Header */}
        <div className="p-4 border-b border-[var(--border-color)] bg-[var(--accent-color)] text-white">
          <div className="flex items-center justify-between mb-3">
            <h3 className="m-0 text-lg font-bold flex items-center gap-2">
              <svg
                width="18"
                height="18"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                <polyline points="7 10 12 15 17 10"></polyline>
                <line x1="12" y1="15" x2="12" y2="3"></line>
              </svg>
              Downloads
            </h3>
            <button
              onClick={onToggle}
              className="p-1.5 bg-transparent border-none text-white cursor-pointer text-2xl leading-none transition-transform duration-200 hover:rotate-90"
            >
              ×
            </button>
          </div>
          
          {/* Action Buttons */}
          <div className="flex gap-2">
            <button
              onClick={onStopAll}
              disabled={activeCount === 0}
              title="Stop All Downloads"
              className={`px-2.5 py-1.5 text-sm font-semibold rounded-md border-none transition-all duration-200 ${
                activeCount === 0
                  ? 'bg-gray-400 text-gray-200 cursor-not-allowed opacity-50'
                  : 'bg-orange-500 text-white hover:bg-orange-600'
              }`}
            >
              ⏸
            </button>
            <button
              onClick={() => {
                if (activeCount > 0) {
                  if (window.confirm(`Stop and remove all ${downloadList.length} downloads including ${activeCount} active download(s)?`)) {
                    onRemoveAll();
                  }
                } else {
                  onRemoveAll();
                }
              }}
              disabled={downloadList.length === 0}
              title="Clear All Downloads"
              className={`px-2.5 py-1.5 text-sm font-semibold rounded-md border-none transition-all duration-200 ${
                downloadList.length === 0
                  ? 'bg-gray-400 text-gray-200 cursor-not-allowed opacity-50'
                  : 'bg-red-600 text-white hover:bg-red-700'
              }`}
            >
              🗑️
            </button>
            <button
              onClick={onClearFinished}
              title="Clear Finished Downloads"
              className="px-2.5 py-1.5 text-sm font-semibold bg-white/20 text-white rounded-md border-none cursor-pointer transition-all duration-200 hover:bg-white/30"
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <polyline points="3 6 5 6 21 6"></polyline>
                <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
              </svg>
            </button>
          </div>
        </div>

        {/* Download List */}
        <div className="flex-1 overflow-y-auto p-4">
          {downloadList.length === 0 ? (
            <div className="text-center text-[var(--text-tertiary)] py-10 px-5 text-sm">
              No downloads yet
            </div>
          ) : (
            <div className="flex flex-col gap-3">
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
      className="bg-[var(--bg-secondary)] rounded-xl p-3.5 transition-all duration-200"
      style={{ borderLeft: `4px solid ${getStatusColor(download.status)}` }}
    >
      <div className="flex items-start justify-between mb-2.5">
        <h4 className="text-sm font-semibold m-0 text-[var(--text-primary)] flex-1 overflow-hidden text-ellipsis whitespace-nowrap pr-2">
          {download.title}
        </h4>
        {(download.status === 'downloading' || download.status === 'queued') && (
          <button
            onClick={() => onCancel(id)}
            className="bg-transparent border-none text-[var(--error-color)] cursor-pointer p-0.5 text-lg leading-none transition-opacity duration-200 hover:opacity-70"
          >
            ×
          </button>
        )}
      </div>

      {download.progress !== undefined && (
        <div className="mb-2">
          <div className="w-full rounded-xl h-1.5 bg-[var(--border-color)] overflow-hidden">
            <div
              className="h-full rounded-xl transition-all duration-300"
              style={{
                width: `${download.progress}%`,
                backgroundColor: download.status === 'complete' ? 'var(--success-color)' :
                                download.status === 'error' ? 'var(--error-color)' :
                                'var(--accent-color)'
              }}
            />
          </div>
        </div>
      )}

      <div className="flex items-center justify-between text-xs text-[var(--text-tertiary)]">
        <span className="capitalize">{download.status}</span>
        {download.speed && <span>{download.speed}</span>}
      </div>
    </div>
  );
};

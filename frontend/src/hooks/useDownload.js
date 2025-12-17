import { useState, useEffect } from 'react';
import { storage } from '../utils/helpers';

export const useTheme = () => {
  const [theme, setTheme] = useState('dark');

  useEffect(() => {
    const savedTheme = storage.getTheme();
    setTheme(savedTheme);
    document.body.classList.toggle('light-theme', savedTheme === 'light');
  }, []);

  const toggleTheme = () => {
    const newTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(newTheme);
    storage.saveTheme(newTheme);
    document.body.classList.toggle('light-theme', newTheme === 'light');
  };

  return { theme, toggleTheme };
};

export const useDownloadManager = () => {
  const [downloads, setDownloads] = useState({});
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const savedDownloads = storage.getDownloads();
    setDownloads(savedDownloads);
  }, []);

  const addDownload = (id, downloadData) => {
    const updated = { ...downloads, [id]: downloadData };
    setDownloads(updated);
    storage.saveDownloads(updated);
  };

  const updateDownload = (id, updates) => {
    if (!downloads[id]) return;
    const updated = {
      ...downloads,
      [id]: { ...downloads[id], ...updates }
    };
    setDownloads(updated);
    storage.saveDownloads(updated);
  };

  const removeDownload = (id) => {
    const updated = { ...downloads };
    delete updated[id];
    setDownloads(updated);
    storage.saveDownloads(updated);
  };

  const clearFinished = () => {
    const updated = Object.fromEntries(
      Object.entries(downloads).filter(([, d]) => 
        d.status !== 'complete' && d.status !== 'error'
      )
    );
    setDownloads(updated);
    storage.saveDownloads(updated);
  };

  const stopAll = () => {
    const updated = Object.fromEntries(
      Object.entries(downloads).map(([id, download]) => {
        if (download.status === 'downloading' || download.status === 'queued') {
          return [id, { ...download, status: 'cancelled' }];
        }
        return [id, download];
      })
    );
    setDownloads(updated);
    storage.saveDownloads(updated);
  };

  const removeAll = () => {
    setDownloads({});
    storage.saveDownloads({});
  };

  const cancelDownload = (id) => {
    if (downloads[id]) {
      const updated = {
        ...downloads,
        [id]: { ...downloads[id], status: 'cancelled' }
      };
      setDownloads(updated);
      storage.saveDownloads(updated);
    }
  };

  const toggleVisibility = () => setIsVisible(!isVisible);

  return {
    downloads,
    isVisible,
    onToggle: toggleVisibility,
    onClearFinished: clearFinished,
    onStopAll: stopAll,
    onRemoveAll: removeAll,
    onCancel: cancelDownload,
    addDownload,
    updateDownload,
    removeDownload,
    clearFinished,
    toggleVisibility
  };
};

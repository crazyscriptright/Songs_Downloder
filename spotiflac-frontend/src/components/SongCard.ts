import type { SearchType, Song, SourceId } from "@/types";
import { createLazyImageHTML } from "@/utils/imageUtils";
import { initLazyLoadingForNewImages } from "@/utils/lazyLoader";

export type DownloadCallback = (
  url: string,
  title: string,
  button: HTMLButtonElement,
  useAdvanced?: boolean,
) => void;
export type AdvancedCallback = (
  url: string,
  title: string,
  button: HTMLButtonElement,
) => void;

const ICON = {
  clock:
    '<svg style="width:14px;height:14px;vertical-align:middle;margin-right:3px;" viewBox="0 0 24 24" fill="currentColor"><path d="M15 1H9v2h6V1zm-4 13h2V8h-2v6zm8.03-6.61l1.42-1.42c-.43-.51-.9-.99-1.41-1.41l-1.42 1.42C16.07 4.74 14.12 4 12 4c-4.97 0-9 4.03-9 9s4.02 9 9 9 9-4.03 9-9c0-2.12-.74-4.07-1.97-5.61zM12 20c-3.87 0-7-3.13-7-7s3.13-7 7-7 7 3.13 7 7-3.13 7-7 7z"/></svg>',
  play: '<svg style="width:14px;height:14px;vertical-align:middle;margin-right:3px;" viewBox="0 0 24 24" fill="currentColor"><path d="M8 5v14l11-7z"/></svg>',
  heart:
    '<svg style="width:14px;height:14px;vertical-align:middle;margin-right:3px;" viewBox="0 0 24 24" fill="currentColor"><path d="M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z"/></svg>',
  music:
    '<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:inline;margin-right:3px;"><path d="M9 18V5l12-2v13"></path><circle cx="6" cy="18" r="3"></circle><circle cx="18" cy="16" r="3"></circle></svg>',
  calendar:
    '<svg style="width:14px;height:14px;vertical-align:middle;margin-right:3px;" viewBox="0 0 24 24" fill="currentColor"><path d="M9 11H7v2h2v-2zm4 0h-2v2h2v-2zm4 0h-2v2h2v-2zm2-7h-1V2h-2v2H8V2H6v2H5c-1.11 0-1.99.9-1.99 2L3 20c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 16H5V9h14v11z"/></svg>',
  globe:
    '<svg style="width:14px;height:14px;vertical-align:middle;margin-right:3px;" viewBox="0 0 24 24" fill="currentColor"><path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zm6.93 6h-2.95c-.32-1.25-.78-2.45-1.38-3.56 1.84.63 3.37 1.91 4.33 3.56zM12 4.04c.83 1.2 1.48 2.53 1.91 3.96h-3.82c.43-1.43 1.08-2.76 1.91-3.96zM4.26 14C4.1 13.36 4 12.69 4 12s.1-1.36.26-2h3.38c-.08.66-.14 1.32-.14 2 0 .68.06 1.34.14 2H4.26zm.82 2h2.95c.32 1.25.78 2.45 1.38 3.56-1.84-.63-3.37-1.9-4.33-3.56zm2.95-8H5.08c.96-1.66 2.49-2.93 4.33-3.56C8.81 5.55 8.35 6.75 8.03 8zM12 19.96c-.83-1.2-1.48-2.53-1.91-3.96h3.82c-.43 1.43-1.08 2.76-1.91 3.96zM14.34 14H9.66c-.09-.66-.16-1.32-.16-2 0-.68.07-1.35.16-2h4.68c.09.65.16 1.32.16 2 0 .68-.07 1.34-.16 2zm.25 5.56c.6-1.11 1.06-2.31 1.38-3.56h2.95c-.96 1.65-2.49 2.93-4.33 3.56zM16.36 14c.08-.66.14-1.32.14-2 0-.68-.06-1.34-.14-2h3.38c.16.64.26 1.31.26 2s-.1 1.36-.26 2h-3.38z"/></svg>',
  disc: '<svg style="width:14px;height:14px;vertical-align:middle;margin-right:3px;" viewBox="0 0 24 24" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 14.5c-2.49 0-4.5-2.01-4.5-4.5S9.51 7.5 12 7.5s4.5 2.01 4.5 4.5-2.01 4.5-4.5 4.5zm0-5.5c-.55 0-1 .45-1 1s.45 1 1 1 1-.45 1-1-.45-1-1-1z"/></svg>',
  gear: '<svg style="width:16px;height:16px;" viewBox="0 0 24 24" fill="currentColor"><path d="M19.14,12.94c0.04-0.3,0.06-0.61,0.06-0.94c0-0.32-0.02-0.64-0.07-0.94l2.03-1.58c0.18-0.14,0.23-0.41,0.12-0.61 l-1.92-3.32c-0.12-0.22-0.37-0.29-0.59-0.22l-2.39,0.96c-0.5-0.38-1.03-0.7-1.62-0.94L14.4,2.81c-0.04-0.24-0.24-0.41-0.48-0.41 h-3.84c-0.24,0-0.43,0.17-0.47,0.41L9.25,5.35C8.66,5.59,8.12,5.92,7.63,6.29L5.24,5.33c-0.22-0.08-0.47,0-0.59,0.22L2.74,8.87 C2.62,9.08,2.66,9.34,2.86,9.48l2.03,1.58C4.84,11.36,4.8,11.69,4.8,12s0.02,0.64,0.07,0.94l-2.03,1.58 c-0.18,0.14-0.23,0.41-0.12,0.61l1.92,3.32c0.12,0.22,0.37,0.29,0.59,0.22l2.39-0.96c0.5,0.38,1.03,0.7,1.62,0.94l0.36,2.54 c0.05,0.24,0.24,0.41,0.48,0.41h3.84c0.24,0,0.44-0.17,0.47-0.41l0.36-2.54c0.59-0.24,1.13-0.56,1.62-0.94l2.39,0.96 c0.22,0.08,0.47,0,0.59-0.22l1.92-3.32c0.12-0.22,0.07-0.47-0.12-0.61L19.14,12.94z M12,15.6c-1.98,0-3.6-1.62-3.6-3.6 s1.62-3.6,3.6-3.6s3.6,1.62,3.6,3.6S13.98,15.6,12,15.6z"/></svg>',
};

const PLACEHOLDER_IMG =
  'data:image/svg+xml,<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect fill="%23333"/><text x="50%" y="50%" text-anchor="middle" dy=".3em" fill="%23666">No Image</text></svg>';

function buildSoundCloudMeta(song: Song): string {
  const parts: string[] = [];
  if (song.duration) parts.push(`<span>${ICON.clock}${song.duration}</span>`);
  if (song.plays)
    parts.push(`<span>${ICON.play}${song.plays.toLocaleString()}</span>`);
  if (song.likes)
    parts.push(`<span>${ICON.heart}${song.likes.toLocaleString()}</span>`);
  if (song.genre) parts.push(`<span>${ICON.music}${song.genre}</span>`);
  return parts.length
    ? `<div class="song-metadata">${parts.join("")}</div>`
    : "";
}

function buildJioSaavnMeta(song: Song): string {
  const parts: string[] = [];
  if (song.year) parts.push(`<span>${ICON.calendar}${song.year}</span>`);
  if (song.language) parts.push(`<span>${ICON.globe}${song.language}</span>`);
  if (song.subtitle) parts.push(`<span>${ICON.disc}${song.subtitle}</span>`);
  return parts.length
    ? `<div class="song-metadata">${parts.join("")}</div>`
    : "";
}

/**
 * Create a source section (header + grid of song cards).
 */
export function createSourceSection(
  title: string,
  songs: Song[],
  sourceId: SourceId,
  searchType: SearchType,
  onDownload: DownloadCallback,
  onAdvanced: AdvancedCallback,
): HTMLElement {
  const section = document.createElement("div");
  section.className = "source-section";
  section.id = sourceId;

  const header = document.createElement("div");
  header.className = "source-header";
  header.innerHTML = `<h2>${title}</h2><span class="count">${songs.length} results</span>`;

  const grid = document.createElement("div");
  grid.className = "songs-grid";

  songs.forEach((song, index) => {
    grid.appendChild(
      createSongCard(song, sourceId, index, searchType, onDownload, onAdvanced),
    );
  });

  section.appendChild(header);
  section.appendChild(grid);

  setTimeout(() => initLazyLoadingForNewImages(), 0);

  return section;
}

/**
 * Create a single song card element.
 */
export function createSongCard(
  song: Song,
  sourceId: SourceId,
  index: number,
  searchType: SearchType,
  onDownload: DownloadCallback,
  onAdvanced: AdvancedCallback,
): HTMLElement {
  const card = document.createElement("div");
  card.className = "song-card";
  card.dataset.songId = `${sourceId}-${index}`;

  const thumbnailUrl = song.thumbnail || PLACEHOLDER_IMG;

  let metadataHTML = "";
  if (sourceId === "soundcloud") {
    metadataHTML = buildSoundCloudMeta(song);
  } else if (sourceId === "jiosaavn") {
    metadataHTML = buildJioSaavnMeta(song);
  }

  let artistDisplay = song.artist || "Unknown Artist";
  if (sourceId === "jiosaavn" && song.subtitle && !song.artist) {
    artistDisplay = song.subtitle.split(" - ")[0] || "Unknown Artist";
  }

  const buttonId = `download-btn-${sourceId}-${index}`;
  const advancedBtnId = `advanced-btn-${sourceId}-${index}`;
  const thumbnailClass =
    searchType === "video"
      ? "song-thumbnail video-thumbnail"
      : "song-thumbnail";

  card.innerHTML = `
    ${createLazyImageHTML(thumbnailUrl, song.title, thumbnailClass)}
    <div class="song-title">${song.title}</div>
    <div class="song-artist">${artistDisplay}</div>
    ${metadataHTML}
    <div class="song-actions" style="display: flex; gap: 5px;">
      <button id="${buttonId}" class="download-btn" style="flex: 1;"
        data-song-url="${song.url}" data-song-title="${song.title}">
        Download
      </button>
      <button id="${advancedBtnId}" class="advanced-btn"
        data-song-url="${song.url}" data-song-title="${song.title}"
        style="padding: 10px 15px; background: var(--secondary-color); border: none; border-radius: 5px; cursor: pointer; font-size: 0.9em; transition: all 0.3s ease; position: relative; z-index: 999;"
        title="Advanced Options">
        ${ICON.gear}
      </button>
    </div>
  `;

  setTimeout(() => {
    const dlBtn = document.getElementById(buttonId) as HTMLButtonElement | null;
    if (dlBtn) {
      dlBtn.addEventListener("click", () => {
        onDownload(song.url, song.title, dlBtn);
      });
    }
    const advBtn = document.getElementById(
      advancedBtnId,
    ) as HTMLButtonElement | null;
    if (advBtn) {
      advBtn.addEventListener("click", () => {
        onAdvanced(song.url, song.title, advBtn);
      });
    }
  }, 0);

  return card;
}

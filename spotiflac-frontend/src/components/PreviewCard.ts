/**
 * PreviewCard — reusable component for non-YouTube preview cards.
 *
 * Usage:
 *   PreviewCard.buildHTML(preview, info)              → preview section only
 *   PreviewCard.buildHTML(preview, info, recs)        → preview + recommendations grid
 *   PreviewCard.buildRecommendationsHTML(tracks)      → standalone recs grid
 *   PreviewCard.wireRecommendationPreviews(el, playFn)→ attach preview button events
 */

import type { DirectUrlInfo, PreviewData } from "@/types";
import { createLazyImageHTML } from "@/utils/imageUtils";

export interface RecommendationTrack {
  title: string;
  artist: string;
  url: string;
  thumbnail?: string;
  duration?: string;
  plays?: number;
}

const PREVIEW_ICON_PLAY =
  '<svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16"><path d="M8 5v14l11-7z"/></svg>';

/** Returns true when the URL belongs to a source that supports audio preview. */
export function previewSupported(url: string): boolean {
  const u = url.toLowerCase();
  return (
    u.includes("soundcloud.com") ||
    u.includes("jiosaavn.com") ||
    u.includes("saavn.com") ||
    u.includes("music.youtube.com") ||
    u.includes("youtube.com/watch") ||
    u.includes("youtu.be/")
  );
}

export class PreviewCard {
  /**
   * Builds the full preview card HTML for non-YouTube sources.
   * Pass `recommendations` to append a recommendations grid below the preview info.
   */
  static buildHTML(
    preview: PreviewData | null,
    processedInfo: DirectUrlInfo,
    recommendations?: RecommendationTrack[],
  ): string {
    const previewSection = this._buildPreviewSection(preview, processedInfo);
    const recsSection =
      recommendations && recommendations.length > 0
        ? this.buildRecommendationsHTML(recommendations)
        : "";
    return previewSection + recsSection;
  }

  /** Builds the thumbnail + metadata section. */
  private static _buildPreviewSection(
    preview: PreviewData | null,
    processedInfo: DirectUrlInfo,
  ): string {
    if (preview && !preview.error && preview.thumbnail) {
      return `
        <div class="preview-grid-generic">
          <div class="preview-thumb">${createLazyImageHTML(preview.thumbnail, "Thumbnail", "lazy-image", "width:100%;border-radius:10px;box-shadow:0 4px 15px rgba(0,0,0,0.3);")}</div>
          <div class="preview-info">
            <h3 style="font-size:1.5em;margin-bottom:12px;color:var(--text-primary);line-height:1.3;">${preview.title}</h3>
            <div style="color:var(--text-secondary);">
              <p style="margin:5px 0;"><strong>Artist:</strong> ${preview.uploader || preview.channel || "Unknown"}</p>
              ${preview.album ? `<p style="margin:5px 0;"><strong>Album:</strong> ${preview.album}</p>` : ""}
              ${preview.language ? `<p style="margin:5px 0;"><strong>Language:</strong> ${preview.language}</p>` : ""}
              ${preview.duration ? `<p style="margin:5px 0;"><strong>Duration:</strong> ${preview.duration}</p>` : ""}
              ${preview.plays ? `<p style="margin:5px 0;"><strong>Plays:</strong> ${Number(preview.plays).toLocaleString()}</p>` : ""}
              ${preview.likes ? `<p style="margin:5px 0;"><strong>Likes:</strong> ${Number(preview.likes).toLocaleString()}</p>` : ""}
              ${preview.genre ? `<p style="margin:5px 0;"><strong>Genre:</strong> ${preview.genre}</p>` : ""}
              <p style="margin:5px 0;"><strong>Source:</strong> ${preview.source || processedInfo.source}</p>
            </div>
          </div>
        </div>`;
    }

    if (preview && !preview.error) {
      return `
        <div style="margin-bottom:20px;">
          <h3 style="font-size:1.6em;margin-bottom:12px;color:var(--text-primary);">${preview.title}</h3>
          <p style="color:var(--text-secondary);margin:5px 0;"><strong>Artist:</strong> ${preview.uploader || preview.channel || "Unknown"}</p>
          ${preview.album ? `<p style="color:var(--text-secondary);margin:5px 0;"><strong>Album:</strong> ${preview.album}</p>` : ""}
          ${preview.duration ? `<p style="color:var(--text-secondary);margin:5px 0;"><strong>Duration:</strong> ${preview.duration}</p>` : ""}
          <p style="color:var(--text-secondary);margin:5px 0;"><strong>Source:</strong> ${preview.source || processedInfo.source}</p>
        </div>`;
    }

    return `
      <div style="margin-bottom:20px;">
        <h3 style="font-size:1.8em;margin-bottom:10px;color:var(--accent-color);">URL Validated</h3>
        <p style="color:var(--text-secondary);font-size:1.1em;"><strong>Source:</strong> ${processedInfo.source}</p>
        <p style="color:var(--text-tertiary);font-size:0.9em;word-break:break-all;">${processedInfo.url}</p>
      </div>`;
  }

  /** Builds a full recommendations grid from an array of tracks. */
  static buildRecommendationsHTML(tracks: RecommendationTrack[]): string {
    return `
      <div class="recommendations-section" style="margin:25px 0;">
        <h3 style="font-size:1.4em;margin-bottom:15px;color:var(--info-color);border-bottom:2px solid var(--info-color);padding-bottom:8px;">
          Recommended Tracks (${tracks.length})
        </h3>
        <div class="recommended-tracks-grid" style="display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:15px;">
          ${tracks.map((t) => this.buildRecommendationCard(t)).join("")}
        </div>
      </div>`;
  }

  /** Builds a single recommendation track card (download + optional preview button). */
  static buildRecommendationCard(track: RecommendationTrack): string {
    const hasThumb =
      track.thumbnail &&
      track.thumbnail.trim() !== "" &&
      track.thumbnail !== "null";

    const thumbHTML = hasThumb
      ? `<img src="${track.thumbnail}" alt="${track.title}" loading="lazy"
           style="width:60px;height:60px;border-radius:6px;object-fit:cover;" />`
      : `<div style="width:60px;height:60px;border-radius:6px;background:var(--bg-secondary);
           display:flex;align-items:center;justify-content:center;color:var(--text-tertiary);font-size:24px;">♪</div>`;

    const safeTitle = track.title.replace(/'/g, "\\'");
    const btnId = `rec-btn-${Math.random().toString(36).slice(2, 8)}`;
    const prevBtnId = `rec-prev-${Math.random().toString(36).slice(2, 8)}`;
    const showPreview = previewSupported(track.url);

    return `
      <div class="recommended-track-card"
           style="background:var(--bg-card);border-radius:10px;padding:15px;border:1px solid var(--border-color);">
        <div style="display:flex;gap:12px;">
          <div style="flex-shrink:0;">${thumbHTML}</div>
          <div style="flex:1;min-width:0;">
            <h5 style="font-size:1em;margin-bottom:4px;color:var(--text-primary);
                overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${track.title}</h5>
            <p style="font-size:0.85em;color:var(--text-secondary);margin-bottom:6px;">${track.artist}</p>
            <div style="font-size:0.75em;color:var(--text-tertiary);margin-bottom:8px;">
              ${track.duration || ""} ${track.plays ? "• " + track.plays.toLocaleString() + " plays" : ""}
            </div>
            <div style="display:flex;gap:6px;">
              <button class="download-btn rec-download" id="${btnId}"
                data-url="${track.url}" data-title="${safeTitle}"
                style="padding:6px 10px;font-size:0.85em;">Download</button>
              ${
                showPreview
                  ? `<button class="preview-btn rec-preview" id="${prevBtnId}"
                       data-url="${track.url}" data-title="${safeTitle}"
                       title="Preview" style="padding:6px 10px;">${PREVIEW_ICON_PLAY}</button>`
                  : ""
              }
            </div>
          </div>
        </div>
      </div>`;
  }

  /**
   * Wires all `.rec-preview` buttons inside `container`.
   * `playFn` is called with (url, title, cardElement, button) when clicked.
   */
  static wireRecommendationPreviews(
    container: HTMLElement,
    playFn: (
      url: string,
      title: string,
      card: HTMLElement,
      btn: HTMLButtonElement,
    ) => void,
  ): void {
    container
      .querySelectorAll<HTMLButtonElement>(".rec-preview")
      .forEach((btn) => {
        btn.addEventListener("click", () => {
          const url = btn.dataset.url!;
          const title = btn.dataset.title!;
          const cardEl =
            (btn.closest(".recommended-track-card") as HTMLElement) ??
            (btn.parentElement as HTMLElement);
          playFn(url, title, cardEl, btn);
        });
      });
  }
}

import { SUGGESTION_DEBOUNCE } from "@/config";
import { SuggestionService } from "@/services/SuggestionService";
import type { SearchType } from "@/types";
import { debounce } from "@/utils/debounce";
import { isAnyUrl, isMusicUrl } from "@/utils/urlDetector";

export type SearchCallback = () => void;
export type SearchTypeCallback = (type: SearchType) => void;

/**
 * Manages the search input, type selector, suggestions dropdown, and query hint.
 */
export class SearchBox {
  readonly input: HTMLInputElement;
  readonly button: HTMLButtonElement;
  readonly queryHint: HTMLElement;
  readonly suggestionsEl: HTMLElement;

  private currentSuggestions: string[] = [];
  private highlightedIndex = -1;
  private suggestionsVisible = false;
  private searchInProgress = false;
  private suggestionRequestId = 0;

  searchType: SearchType = "music";

  onSearch: SearchCallback = () => {};
  onTypeChange: SearchTypeCallback = () => {};

  constructor() {
    this.input = document.getElementById("searchInput") as HTMLInputElement;
    this.button = document.getElementById("searchBtn") as HTMLButtonElement;
    this.queryHint = document.getElementById("queryHint") as HTMLElement;
    this.suggestionsEl = document.getElementById(
      "searchSuggestions",
    ) as HTMLElement;

    this.bindEvents();
  }

  get query(): string {
    return this.input.value.trim();
  }
  set query(v: string) {
    this.input.value = v;
  }

  private bindEvents(): void {
    const debouncedFetch = debounce(
      (q: string) => this.fetchSuggestions(q),
      SUGGESTION_DEBOUNCE,
    );

    this.input.addEventListener("input", () => {
      const q = this.query;
      if (!q) {
        this.clearUrlState();
        this.hideSuggestions();
        return;
      }

      if (isMusicUrl(q)) {
        this.queryHint.className = "query-hint url-detected";
        this.queryHint.innerHTML =
          '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:inline;margin-right:5px;"><path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"></path><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"></path></svg>Music URL detected! Click search to download.';
        this.hideSuggestions();
      } else if (isAnyUrl(q)) {
        this.queryHint.className = "query-hint";
        this.queryHint.style.color = "var(--error-color)";
        this.queryHint.innerHTML =
          '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="display:inline;margin-right:5px;"><circle cx="12" cy="12" r="10"></circle><line x1="15" y1="9" x2="9" y2="15"></line><line x1="9" y1="9" x2="15" y2="15"></line></svg>Invalid URL! Only music URLs supported.';
        this.hideSuggestions();
      } else {
        this.queryHint.className = "query-hint";
        this.queryHint.style.color = "";
        this.queryHint.innerHTML =
          '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="display:inline;margin-right:5px;"><circle cx="12" cy="12" r="10"></circle><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"></path><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>Search by name or paste a music URL';
        debouncedFetch(q);
      }
    });

    this.input.addEventListener("keydown", (e) => {
      if (e.key === "Enter") {
        e.preventDefault();
        if (this.suggestionsVisible && this.highlightedIndex >= 0) {
          this.selectSuggestion(this.currentSuggestions[this.highlightedIndex]);
        } else {
          this.hideSuggestions();
          this.onSearch();
        }
      } else if (e.key === "ArrowDown") {
        e.preventDefault();
        this.navigateSuggestions("down");
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        this.navigateSuggestions("up");
      } else if (e.key === "Escape") {
        this.hideSuggestions();
      }
    });

    this.button.addEventListener("click", () => this.onSearch());

    document.addEventListener("click", (e) => {
      if (
        !this.input.contains(e.target as Node) &&
        !this.suggestionsEl.contains(e.target as Node)
      ) {
        this.hideSuggestions();
      }
    });

    document.querySelectorAll<HTMLButtonElement>(".type-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const type = btn.dataset.type as SearchType;
        this.selectSearchType(type);
      });
    });
  }

  /** Programmatically select a search type. */
  selectSearchType(type: SearchType): void {
    this.searchType = type;

    document.querySelectorAll<HTMLButtonElement>(".type-btn").forEach((btn) => {
      btn.classList.toggle("active", btn.dataset.type === type);
    });

    const labels: Record<SearchType, string> = {
      music: "Search Music",
      video: "Search Videos",
      all: "Search All Sources",
      spotify: "Search Spotify",
    };
    this.button.innerHTML = labels[type] || "Search";

    this.onTypeChange(type);
  }

  private async fetchSuggestions(query: string): Promise<void> {
    if (this.searchInProgress) return;

    const requestId = ++this.suggestionRequestId;
    const suggestions = await SuggestionService.fetchSuggestions(query);

    if (requestId !== this.suggestionRequestId || this.searchInProgress) return;

    if (suggestions.length > 0) {
      this.showSuggestions(suggestions);
    } else {
      this.hideSuggestions();
    }
  }

  private showSuggestions(suggestions: string[]): void {
    if (this.searchInProgress) return;

    this.currentSuggestions = suggestions;
    this.highlightedIndex = -1;

    this.suggestionsEl.innerHTML = suggestions
      .map(
        (s, i) => `
        <div class="suggestion-item" data-index="${i}">
          <svg class="suggestion-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <circle cx="11" cy="11" r="8"></circle>
            <path d="M21 21l-4.35-4.35"></path>
          </svg>
          <span class="suggestion-text">${s}</span>
        </div>`,
      )
      .join("");

    this.suggestionsEl
      .querySelectorAll<HTMLElement>(".suggestion-item")
      .forEach((el) => {
        el.addEventListener("click", () => {
          const idx = parseInt(el.dataset.index || "0", 10);
          this.selectSuggestion(this.currentSuggestions[idx]);
        });
      });

    this.suggestionsEl.classList.add("show");
    this.suggestionsVisible = true;
  }

  hideSuggestions(): void {
    this.suggestionsEl.classList.remove("show");
    this.suggestionsVisible = false;
    this.highlightedIndex = -1;
  }

  /** Mark that a search has started (prevents suggestions from showing) */
  setSearchInProgress(inProgress: boolean): void {
    this.searchInProgress = inProgress;
    if (inProgress) {
      this.hideSuggestions();

      this.suggestionRequestId++;
    }
  }

  private selectSuggestion(text: string): void {
    this.input.value = text;
    this.hideSuggestions();
    this.onSearch();
  }

  private navigateSuggestions(direction: "up" | "down"): void {
    if (!this.suggestionsVisible || this.currentSuggestions.length === 0)
      return;

    const prev = this.suggestionsEl.querySelector(
      ".suggestion-item.highlighted",
    );
    if (prev) prev.classList.remove("highlighted");

    if (direction === "down") {
      this.highlightedIndex =
        (this.highlightedIndex + 1) % this.currentSuggestions.length;
    } else {
      this.highlightedIndex =
        this.highlightedIndex <= 0
          ? this.currentSuggestions.length - 1
          : this.highlightedIndex - 1;
    }

    const next = this.suggestionsEl.querySelector(
      `[data-index="${this.highlightedIndex}"]`,
    );
    if (next) {
      next.classList.add("highlighted");
      this.input.value = this.currentSuggestions[this.highlightedIndex];
    }
  }

  /** Clear URL-related query parameters. */
  private clearUrlState(): void {
    const newUrl = new URL(window.location.href);
    newUrl.searchParams.delete("q");
    newUrl.searchParams.delete("type");
    window.history.replaceState({}, "", newUrl.pathname);
  }
}

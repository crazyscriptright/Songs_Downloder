import type { SourceId, SourceInfo } from '@/types';

export type SwitchSourceCallback = (sourceId: SourceId) => void;

/**
 * Renders the source-navigation tab bar (JioSaavn, YouTube Music, SoundCloud, etc.).
 */
export class SourceNavigation {
  private container: HTMLElement;
  onSwitch: SwitchSourceCallback = () => {};

  /** The source the user most recently clicked (persists across incremental updates). */
  userSelectedTab: SourceId | null = null;

  constructor() {
    this.container = document.getElementById('sourceNavigation') as HTMLElement;
  }

  /** Render navigation buttons for the given sources. */
  render(sources: SourceInfo[]): void {
    this.container.innerHTML = '';
    this.container.className = sources.length > 0 ? 'source-navigation active' : 'source-navigation';

    sources.forEach((source, index) => {
      const isActive = this.userSelectedTab
        ? source.id === this.userSelectedTab
        : index === 0;

      const btn = document.createElement('button');
      btn.className = 'source-nav-btn' + (isActive ? ' active' : '');
      btn.innerHTML = `${source.name} <span class="count">${source.count}</span>`;
      btn.addEventListener('click', () => {
        this.userSelectedTab = source.id;
        this.setActive(source.id);
        this.onSwitch(source.id);
      });
      this.container.appendChild(btn);
    });
  }

  /** Highlight a specific source button (and deactivate others). */
  setActive(sourceId: SourceId): void {
    this.container.querySelectorAll<HTMLButtonElement>('.source-nav-btn').forEach((btn) => {
      btn.classList.remove('active');
    });
    // Find button whose text starts with the source name
    const btns = Array.from(this.container.querySelectorAll<HTMLButtonElement>('.source-nav-btn'));
    for (const btn of btns) {
      if (btn.textContent?.includes(sourceId)) {
        btn.classList.add('active');
      }
    }
  }

  /** Reset user selection (e.g. for a new search). */
  reset(): void {
    this.userSelectedTab = null;
    this.container.innerHTML = '';
    this.container.className = 'source-navigation';
  }
}
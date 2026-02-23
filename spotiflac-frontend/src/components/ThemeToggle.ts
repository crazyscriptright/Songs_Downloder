import { StorageService } from "@/services/StorageService";

const MOON_SVG =
  '<path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path>';
const SUN_SVG =
  '<circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line>';

/**
 * Manages light / dark theme toggling.
 */
export class ThemeToggle {
  private iconEl: SVGElement | null;
  private textEl: HTMLElement | null;

  constructor() {
    this.iconEl = document.getElementById(
      "themeIcon",
    ) as unknown as SVGElement | null;
    this.textEl = document.getElementById("themeText");
  }

  /** Apply the saved theme (or default to dark). Called on DOMContentLoaded. */
  init(): void {
    const saved = StorageService.getTheme();

    if (!saved) StorageService.setTheme("dark");

    if (saved === "light") {
      document.documentElement.classList.add("light-theme");
      document.body.classList.add("light-theme");
      this.setIcon(true);
    } else {
      this.setIcon(false);
    }
  }

  /** Toggle between light and dark themes. */
  toggle(): void {
    document.documentElement.classList.toggle("light-theme");
    document.body.classList.toggle("light-theme");
    const isLight = document.body.classList.contains("light-theme");
    this.setIcon(isLight);
    StorageService.setTheme(isLight ? "light" : "dark");
  }

  private setIcon(isLight: boolean): void {
    if (this.iconEl) this.iconEl.innerHTML = isLight ? SUN_SVG : MOON_SVG;
    if (this.textEl) this.textEl.textContent = isLight ? "Light" : "Dark";
  }
}

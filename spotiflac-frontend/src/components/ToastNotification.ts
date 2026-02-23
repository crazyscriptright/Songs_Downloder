export type ToastType = "success" | "error" | "info";

const ICONS: Record<ToastType, string> = {
  success: "✓",
  error: "✕",
  info: "ℹ",
};

/**
 * A lightweight toast notification manager.
 */
export class ToastNotification {
  private container: HTMLElement;

  constructor() {
    this.container =
      document.getElementById("toastContainer") || this.createContainer();
  }

  private createContainer(): HTMLElement {
    const el = document.createElement("div");
    el.id = "toastContainer";
    el.className = "toast-container";
    document.body.appendChild(el);
    return el;
  }

  /**
   * Show a toast notification.
   * @param type     'success' | 'error' | 'info'
   * @param title    Bold heading text
   * @param message  Description text
   * @param duration Auto-dismiss in ms (0 = sticky)
   */
  show(type: ToastType, title: string, message: string, duration = 5000): void {
    const toast = document.createElement("div");
    toast.className = `toast ${type}`;

    toast.innerHTML = `
      <div class="toast-icon">${ICONS[type] || "ℹ"}</div>
      <div class="toast-content">
        <div class="toast-title">${title}</div>
        <div class="toast-message">${message}</div>
      </div>
      <button class="toast-close" onclick="this.parentElement.remove()">×</button>
    `;

    this.container.appendChild(toast);

    if (duration > 0) {
      setTimeout(() => {
        toast.classList.add("removing");
        setTimeout(() => toast.remove(), 300);
      }, duration);
    }
  }
}

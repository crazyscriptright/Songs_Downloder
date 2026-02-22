import { MUSIC_PLACEHOLDER_SVG } from './imageUtils';

let imageObserver: IntersectionObserver | null = null;

/** Initialise the IntersectionObserver for lazy-loading images. */
export function initLazyLoading(): void {
  if ('IntersectionObserver' in window) {
    imageObserver = new IntersectionObserver(
      (entries, observer) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            const img = entry.target as HTMLImageElement;
            loadImage(img);
            observer.unobserve(img);
          }
        });
      },
      { rootMargin: '100px', threshold: 0.01 },
    );
  }
}

/** Load a single image from its `data-src` attribute. */
export function loadImage(img: HTMLImageElement): void {
  const src = img.dataset.src;
  if (!src) return;

  const renderedWidth = img.clientWidth || img.offsetWidth || 150;

  let size = 'medium';
  if (renderedWidth < 200) size = 'small';
  else if (renderedWidth >= 200 && renderedWidth <= 400) size = 'medium';
  else size = 'large';

  let finalSrc = src;
  if (src.includes('/api/proxy-image?')) {
    if (src.includes('&size=')) {
      finalSrc = src.replace(/&size=(small|medium|large)/, `&size=${size}`);
    } else {
      finalSrc = `${src}&size=${size}`;
    }
  }

  img.classList.add('loading');

  const loader = new Image();

  loader.onload = () => {
    img.src = finalSrc;
    img.classList.remove('loading');
    img.classList.add('loaded');
    delete img.dataset.src;
  };

  loader.onerror = () => {
    img.src = (img.dataset.fallback as string) || MUSIC_PLACEHOLDER_SVG;
    img.classList.remove('loading');
    img.classList.add('loaded');
    delete img.dataset.src;
  };

  loader.src = finalSrc;
}

/** Start observing an image element for lazy loading. */
export function observeImage(img: HTMLImageElement): void {
  if (imageObserver) {
    imageObserver.observe(img);
  } else {
    loadImage(img);
  }
}

/** Observe any newly-added lazy images that haven't been processed yet. */
export function initLazyLoadingForNewImages(): void {
  const lazyImages = document.querySelectorAll<HTMLImageElement>(
    'img[data-src]:not(.loaded):not(.loading)',
  );
  lazyImages.forEach((img) => observeImage(img));
}
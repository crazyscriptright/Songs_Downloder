/**
 * Creates a debounced version of a function that delays invocation
 * until `delay` ms have elapsed since the last call.
 */
export function debounce<A extends unknown[], R>(
  func: (...args: A) => R,
  delay: number,
): (...args: A) => void {
  let timeoutId: ReturnType<typeof setTimeout> | null = null;

  return function (this: unknown, ...args: A) {
    if (timeoutId !== null) {
      clearTimeout(timeoutId);
    }
    timeoutId = setTimeout(() => {
      func.apply(this, args);
      timeoutId = null;
    }, delay);
  };
}

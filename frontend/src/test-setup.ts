import '@testing-library/jest-dom/vitest';

/* jsdom has no canvas; the globe draws nothing there and says so by getting
   no context, instead of jsdom logging "not implemented" for every render. */
if (typeof HTMLCanvasElement !== 'undefined') {
  HTMLCanvasElement.prototype.getContext = (() => null) as unknown as HTMLCanvasElement['getContext'];
}

/**
 * Which of the ranking's caveats about the aid to show first.
 *
 * The remaining cost comes with warnings from the ranking, and a card has
 * room for one or two. First come the ones that explain the figures
 * themselves (a cost and an award from different years or currencies - the
 * reason a remainder may not be computed at all), then the ones that say
 * whether the aid can be won (competitive, needs a nomination), then the
 * rest. Order only: nothing is reworded or dropped from the full list.
 */

function weight(text: string): number {
  if (/not directly comparable|different (academic )?year|currenc/i.test(text)) return 0;
  if (/competitive|nomination/i.test(text)) return 1;
  return 2;
}

export function orderCaveats(warnings: readonly string[] | null | undefined, limit = 2): string[] {
  return [...(warnings ?? [])]
    .map((text, index) => ({ text, index }))
    .sort((a, b) => weight(a.text) - weight(b.text) || a.index - b.index)
    .slice(0, limit)
    .map((item) => item.text);
}

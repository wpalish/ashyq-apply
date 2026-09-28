/**
 * The share sheet, loaded when it is first opened: the story cards and their
 * drawing are never on the path to the list, so a budget phone does not pay
 * for them on the first screen.
 */

import { lazy, Suspense, type ComponentProps } from 'react';

const Sheet = lazy(() => import('@/components/ShareSheet').then((m) => ({ default: m.ShareSheet })));

export function LazyShareSheet(props: ComponentProps<typeof Sheet>) {
  return (
    <Suspense fallback={null}>
      <Sheet {...props} />
    </Suspense>
  );
}

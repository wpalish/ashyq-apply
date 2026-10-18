import type { ReactNode } from 'react';
import { LazyMotion, MotionConfig } from 'motion/react';
const features = () => import('./bookMotionFeatures').then(module => module.default);
/** Stable wrapper: no route/case keys or exits that can retire forms or stores. */
export function BookMotion({ children }: { children: ReactNode }) {
  return <MotionConfig reducedMotion="user" transition={{ duration: .18, ease: [.16, 1, .3, 1] }}><LazyMotion features={features} strict>{children}</LazyMotion></MotionConfig>;
}

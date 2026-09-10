# AppShell and CaseScreen

## 1. Metadata

Category: navigation and case overview. Status: first redesign slice. Source: App.tsx and CaseScreen.tsx. Epics: E00, E04, E10, E16; epics.md section 5.

## 2. Overview

Five primary destinations: Case, Shortlist, Plan, Community, More. Context navigation preserves all existing screens: Community contains Feed, Discover and Messages, while the user's community profile and moderation remain account-adjacent under More. The case overview chooses a next action from actual saved-profile, run and result state. Do not imply readiness from unvalidated draft fields or invent deadlines. Scrolling or focusing a content control must keep that control clear of the fixed BottomNav.

## 3. Anatomy

Desktop sidebar / mobile bottom navigation; horizontally scrollable contextual links on mobile; mode badge; case switcher; global running banner; main landmark. Account controls move into More on mobile. BottomNav is a direct AppShell child rather than a descendant of the off-screen sidebar stacking context. The mobile context strip does not wrap: each real control can be scrolled into view, focused and activated. Overview: editorial greeting, next-action panel, three workflow steps, real result counts (unavailable summary explicitly says no data), source/data explanation.

## 4. Tokens

Use existing color, space, font-family, font-size, border-width, radius, size-touch-target and z-header aliases. All styling is in redesign.css and imports after global/components CSS. No raw visual literals in declarations.

## 5. Props/API

CaseScreen receives onNavigate(screen). Store supplies hydration, savedProfile, run, results, dirty, summary. App retains existing screen hashes and gates. #/case is the new default. Primary destinations stay visible but are disabled with the existing gate explanation when no child screen is available. Case switcher appears only for multiple cases; new-case action remains available. On mobile, theme and language controls are in More.

## 6. States

Hydrating; no saved profile; saved profile/no run; queued/running; failed/cancelled; results ready. Failed or cancelled research offers progress/retry before results. Button focus/hover/disabled inherits the design system. No artificial success or progress percentages. Mobile navigation reserves bottom space, owns the bottom pointer hit area above long screen content, keeps every target at least 44 px, and remains keyboard reachable.

## 7. Example

```tsx
<CaseScreen onNavigate={setScreen} />
```

## 8. Cross-references

[Design system](../design-system.md), [Panel](panel.md), [Button](button.md), [Notice](notice.md).

# Unimatch UI book implementation

Source: owner-selected UNIMATCH_UI_BOOK.pdf, 40 desktop/mobile pairs. Full inventory and unmodified reference renders live alongside this checkout in ../reference/.

## Tokens
Inter 400/500/600/700, self-hosted. Navy #0b1739; muted #526582. Royal blue #1454ff, white action text; hover #0c42d4. Cool paper #f5f9ff, white panels, subtle blue separators. Body 16px, helper 13–14px, titles fluid 32–52px. Radius 12px panels, 8px fields, pills only compact controls. 4px spacing scale, max content 1200px.

## Composition
Desktop top navigation; secondary workflow rail beside forms; main area remains readable at 65–75ch. Mobile stacks forms and details, fixed primary bottom navigation with safe-area inset. Tables have labelled scroll containers when genuinely tabular. No document-level horizontal overflow.

## Interaction
Keyboard focus uses a visible blue ring; primary controls at least44px. Existing native details menus stay keyboard operable. Status colours retain evidence semantics, never rebrand all outcomes blue. Saving, conflict, unknown outcome and current draft remain distinct. Animated button feedback160ms; first landing globe entrance600ms; no repeated page entrance motion.

## Implementation map
See docs/design/ui-book/coverage.md. Every book screen is mapped to a route or an actual contextual state; recovery is tested as a response outcome rather than offered as a fake normal page.

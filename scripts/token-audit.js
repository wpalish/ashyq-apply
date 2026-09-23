#!/usr/bin/env node

/*
 * CI-ready design-token audit.
 *
 * Component CSS must consume project aliases (`--color-*`, `--space-*`, etc.).
 * Raw values are allowed only while defining custom properties in tokens.css,
 * where upstream primitives and project-alias fallbacks necessarily live.
 */

const fs = require('node:fs');
const path = require('node:path');

const ROOT = path.resolve(__dirname, '..');
const INCLUDE_TOKEN_DEFINITIONS = process.argv.includes('--include-token-definitions');
const JSON_OUTPUT = process.argv.includes('--json');
const SUMMARY_ONLY = process.argv.includes('--summary');
const EXTENSIONS = new Set(['.css', '.scss']);
const SKIP_DIRS = new Set(['.git', '.claude', '.venv', 'node_modules', 'dist', 'coverage', 'playwright-report', 'test-results']);

const RAW_COLOR = /#[0-9a-f]{3,8}\b|\b(?:rgb|rgba|hsl|hsla|oklch|oklab|lab|lch|color)\([^)]*\)/gi;
const RAW_LENGTH = /(?<![\w-])-?(?:\d*\.)?\d+(?:px|rem|em)\b/gi;
const RAW_TIME = /(?<![\w-])(?:\d*\.)?\d+m?s\b/gi;

const spacingSuggestions = new Map([
  ['-1px', 'var(--space-negative-hairline)'],
  ['0px', 'var(--space-0)'],
  ['1px', 'var(--space-hairline)'],
  ['2px', 'var(--space-0-5)'],
  ['3px', 'var(--space-0-75)'],
  ['4px', 'var(--space-1)'],
  ['5px', 'var(--space-1-25)'],
  ['6px', 'var(--space-1-5)'],
  ['8px', 'var(--space-2)'],
  ['10px', 'var(--space-2-5)'],
  ['12px', 'var(--space-3)'],
  ['16px', 'var(--space-4)'],
  ['20px', 'var(--space-5)'],
  ['24px', 'var(--space-6)'],
  ['32px', 'var(--space-7)'],
  ['48px', 'var(--space-8)'],
  ['0.25rem', 'var(--space-1)'],
  ['0.5rem', 'var(--space-2)'],
  ['0.75rem', 'var(--space-3)'],
  ['1rem', 'var(--space-4)'],
  ['1.5rem', 'var(--space-6)'],
  ['2rem', 'var(--space-7)'],
  ['3rem', 'var(--space-8)'],
]);

function walk(directory, files = []) {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    if (entry.isDirectory() && SKIP_DIRS.has(entry.name)) continue;
    const absolute = path.join(directory, entry.name);
    if (entry.isDirectory()) walk(absolute, files);
    else if (EXTENSIONS.has(path.extname(entry.name).toLowerCase())) files.push(absolute);
  }
  return files;
}

function withoutComments(source) {
  return source.replace(/\/\*[\s\S]*?\*\//g, (comment) => comment.replace(/[^\n]/g, ' '));
}

function lineAt(source, index) {
  return source.slice(0, index).split('\n').length;
}

function colorSuggestion(property, value) {
  if (/border|outline/.test(property)) return 'var(--color-border) or var(--color-focus-ring)';
  if (/background/.test(property)) {
    if (/rgb\(0 0 0/.test(value)) return 'var(--color-overlay)';
    return 'var(--color-background) or a semantic surface/status alias';
  }
  return 'var(--color-text), var(--color-text-muted), or a semantic status alias';
}

function suggestionFor(category, property, value) {
  if (category === 'color') return colorSuggestion(property, value);
  if (category === 'spacing') return spacingSuggestions.get(value.toLowerCase()) || 'the nearest var(--space-*) or var(--size-*) alias';
  if (category === 'font-size') return 'the matching var(--font-size-*) alias';
  if (category === 'font-weight') return 'the matching var(--font-weight-*) alias';
  if (category === 'line-height') return 'the matching var(--line-height-*) alias';
  if (category === 'border-radius') return 'var(--radius-sm), var(--radius-md), var(--radius-lg), or var(--radius-full)';
  if (category === 'z-index') return 'the matching var(--z-*) layer alias';
  if (category === 'box-shadow') return 'var(--shadow-sm), var(--shadow-md), var(--shadow-lg), or var(--shadow-focus-ring)';
  if (category === 'motion') return 'var(--motion-duration-fast), var(--motion-duration-normal), or var(--motion-duration-reduced)';
  if (category === 'uncommon') return 'a named var(--size-*), var(--effect-*), or other project alias';
  if (category === 'layer-boundary') return 'a Layer 2 project alias; component CSS must not reference --ds-* directly';
  return 'an existing project alias from tokens.css';
}

function pushOccurrence(issues, base, category, severity, violation, value = violation) {
  issues.push({
    ...base,
    category,
    severity,
    violation,
    suggestion: suggestionFor(category, base.property, value),
  });
}

function scanFile(filename) {
  const original = fs.readFileSync(filename, 'utf8');
  const source = withoutComments(original);
  const relativeFile = path.relative(ROOT, filename).replaceAll(path.sep, '/');
  const issues = [];
  const declaration = /(^|[;{])\s*([\w-]+)\s*:\s*([^;{}]+);/gm;
  let match;

  while ((match = declaration.exec(source))) {
    const property = match[2].toLowerCase();
    const value = match[3].trim();
    const valueIndex = match.index + match[0].indexOf(match[3]);
    const base = { file: relativeFile, line: lineAt(source, valueIndex), property };
    const tokenDefinition = property.startsWith('--') && path.basename(filename) === 'tokens.css';
    if (tokenDefinition && !INCLUDE_TOKEN_DEFINITIONS) continue;

    if (tokenDefinition && INCLUDE_TOKEN_DEFINITIONS) {
      if (/shadow/.test(property)) {
        pushOccurrence(issues, base, 'box-shadow', 'error', value, value);
        continue;
      }
      if (/radius/.test(property)) {
        pushOccurrence(issues, base, 'border-radius', 'error', value, value);
        continue;
      }
      if (/duration/.test(property)) {
        pushOccurrence(issues, base, 'motion', 'warning', value, value);
        continue;
      }
      if (/weight/.test(property)) {
        pushOccurrence(issues, base, 'font-weight', 'error', value, value);
        continue;
      }
      if (/^(?:--text-|--font-size)/.test(property)) {
        pushOccurrence(issues, base, 'font-size', 'error', value, value);
        continue;
      }
      if (/^--z-/.test(property)) {
        pushOccurrence(issues, base, 'z-index', 'error', value, value);
        continue;
      }
    }

    if (!tokenDefinition && value.includes('var(--ds-')) {
      pushOccurrence(issues, base, 'layer-boundary', 'error', value, value);
      continue;
    }

    if (property === 'box-shadow') {
      RAW_LENGTH.lastIndex = 0;
      RAW_COLOR.lastIndex = 0;
      if (!value.includes('var(') || RAW_LENGTH.test(value) || RAW_COLOR.test(value)) {
        RAW_LENGTH.lastIndex = 0;
        RAW_COLOR.lastIndex = 0;
        pushOccurrence(issues, base, 'box-shadow', 'error', value, value);
      }
      continue;
    }

    if (property === 'border-radius') {
      if (!value.includes('var(') || RAW_LENGTH.test(value) || /\b(?:50|100)%\b/.test(value)) {
        RAW_LENGTH.lastIndex = 0;
        pushOccurrence(issues, base, 'border-radius', 'error', value, value);
      }
      continue;
    }

    if (property === 'font-size') {
      RAW_LENGTH.lastIndex = 0;
      if (!value.includes('var(') || RAW_LENGTH.test(value)) {
        RAW_LENGTH.lastIndex = 0;
        pushOccurrence(issues, base, 'font-size', 'error', value, value);
      }
      continue;
    }

    if (property === 'font-weight') {
      if (!value.includes('var(')) {
        pushOccurrence(issues, base, 'font-weight', 'error', value, value);
      }
      continue;
    }

    if (property === 'line-height' && /^-?(?:\d*\.)?\d+(?:px|rem|em)?$/.test(value)) {
      pushOccurrence(issues, base, 'line-height', 'error', value, value);
      continue;
    }

    if (property === 'z-index') {
      if (!value.includes('var(')) {
        pushOccurrence(issues, base, 'z-index', 'error', value, value);
      }
      continue;
    }

    if (property === 'transition' || property === 'transition-duration' || property === 'animation' || property === 'animation-duration') {
      const times = [...value.matchAll(RAW_TIME)];
      for (const time of times) {
        pushOccurrence(issues, base, 'motion', 'warning', time[0], time[0]);
      }
    }

    const requiresProjectAlias =
      property === 'color' ||
      property === 'background' ||
      property === 'background-color' ||
      property === 'background-image' ||
      property === 'padding' || property.startsWith('padding-') ||
      property === 'margin' || property.startsWith('margin-') ||
      property === 'gap' || property === 'row-gap' || property === 'column-gap' ||
      property === 'transition' || property === 'transition-duration';
    if (requiresProjectAlias && !value.includes('var(')) {
      const category = property.startsWith('transition') ? 'motion' :
        (property.startsWith('background') || property === 'color' ? 'color' : 'spacing');
      const severity = category === 'motion' ? 'warning' : 'error';
      RAW_TIME.lastIndex = 0;
      if (category === 'motion' && RAW_TIME.test(value)) {
        RAW_TIME.lastIndex = 0;
        continue;
      }
      pushOccurrence(issues, base, category, severity, value, value);
      continue;
    }

    const colors = [...value.matchAll(RAW_COLOR)];
    for (const color of colors) {
      if (color[0].includes('var(')) continue;
      pushOccurrence(issues, base, 'color', 'error', color[0], color[0]);
    }

    const lengths = [...value.matchAll(RAW_LENGTH)];
    for (const length of lengths) {
      const spacingProperty =
        property === 'padding' || property.startsWith('padding-') ||
        property === 'margin' || property.startsWith('margin-') ||
        property === 'gap' || property === 'row-gap' || property === 'column-gap' ||
        property === 'inset' || property === 'top' || property === 'right' ||
        property === 'bottom' || property === 'left' || property.startsWith('border') ||
        property.startsWith('outline') || property === 'text-underline-offset';
      pushOccurrence(
        issues,
        base,
        spacingProperty ? 'spacing' : 'uncommon',
        spacingProperty ? 'error' : 'warning',
        length[0],
        length[0],
      );
    }
  }

  return issues;
}

const files = walk(ROOT).sort();
const issues = files.flatMap(scanFile);
const errors = issues.filter((issue) => issue.severity === 'error');
const warnings = issues.filter((issue) => issue.severity === 'warning');
const countsByCategory = Object.fromEntries(
  [...new Set(issues.map((issue) => issue.category))]
    .sort()
    .map((category) => [category, issues.filter((issue) => issue.category === category).length]),
);
const countsByFile = Object.fromEntries(
  [...new Set(issues.map((issue) => issue.file))]
    .sort()
    .map((file) => [file, issues.filter((issue) => issue.file === file).length]),
);

if (JSON_OUTPUT) {
  const payload = { filesScanned: files.length, errors: errors.length, warnings: warnings.length, countsByCategory, countsByFile };
  if (!SUMMARY_ONLY) payload.issues = issues;
  process.stdout.write(`${JSON.stringify(payload, null, 2)}\n`);
} else if (issues.length === 0) {
  console.log(`Token audit passed: ${files.length} CSS/SCSS files scanned, 0 errors, 0 warnings.`);
} else {
  for (const issue of issues) {
    console.log(`${issue.severity.toUpperCase()} ${issue.file}:${issue.line} [${issue.category}] ${issue.property}: ${issue.violation}`);
    console.log(`  Suggestion: ${issue.suggestion}`);
  }
  console.log(`\nToken audit: ${files.length} files, ${errors.length} errors, ${warnings.length} warnings.`);
}

process.exitCode = errors.length > 0 ? 1 : 0;

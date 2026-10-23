import { readFileSync, existsSync } from 'node:fs';
import { resolve } from 'node:path';
import { expect, it } from 'vitest';
import branding from '@/data/universityBranding.json';
import { universityDirectory } from './universityDirectory';

it('ships every referenced local identity asset and complete, passive SVG documents', () => {
  const paths = new Set([...universityDirectory.map(row => row.image), ...Object.values(branding)]);
  for (const path of paths) {
    expect(path).toMatch(/^\/universities\/[a-zA-Z0-9_.-]+$/);
    const file = resolve(process.cwd(), 'public', path!.slice(1));
    expect(existsSync(file), path!).toBe(true);
    if (!path!.endsWith('.svg')) continue;
    const document = new DOMParser().parseFromString(readFileSync(file, 'utf8'), 'image/svg+xml');
    expect(document.querySelector('parsererror'), path!).toBeNull();
    expect(document.documentElement.localName, path!).toBe('svg');
    expect(document.querySelector('script,foreignObject'), path!).toBeNull();
    for (const node of document.querySelectorAll('*')) {
      for (const attribute of node.attributes) {
        expect(attribute.name, path!).not.toMatch(/^on/i);
        if (attribute.localName === 'href') expect(attribute.value, path!).toMatch(/^(data:image\/|#)/);
      }
    }
  }
});

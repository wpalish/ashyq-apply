/** Three-way JSON fields: absent != null; arrays are atomic, never index-merged. */
export interface ProfileFieldValue { present: boolean; value?: unknown }
export interface ProfileDifference {
  path: string[]; base: ProfileFieldValue; local: ProfileFieldValue; server: ProfileFieldValue;
  conflict: boolean; proposed: 'local' | 'server';
}
function object(v: unknown): v is Record<string, unknown> { return !!v && typeof v === 'object' && !Array.isArray(v); }
function equal(a: ProfileFieldValue, b: ProfileFieldValue): boolean {
  if (a.present !== b.present) return false;
  if (!a.present) return true;
  if (object(a.value) && object(b.value)) {
    const keys = new Set([...Object.keys(a.value), ...Object.keys(b.value)]);
    return [...keys].every(key => equal(field(a.value, key), field(b.value, key)));
  }
  return JSON.stringify(a.value) === JSON.stringify(b.value);
}
function field(obj: unknown, key: string): ProfileFieldValue {
  return object(obj) && Object.hasOwn(obj, key) ? { present: true, value: obj[key] } : { present: false };
}
export function compareProfiles(base: Record<string, unknown>, local: Record<string, unknown>, server: Record<string, unknown>): ProfileDifference[] {
  const out: ProfileDifference[] = [];
  function visit(b: ProfileFieldValue, l: ProfileFieldValue, s: ProfileFieldValue, path: string[]) {
    if (equal(l, s)) return;
    if (object(b.value) && object(l.value) && object(s.value)) {
      for (const key of new Set([...Object.keys(b.value), ...Object.keys(l.value), ...Object.keys(s.value)])) visit(field(b.value, key), field(l.value, key), field(s.value, key), [...path,key]);
      return;
    }
    const localChanged = !equal(b,l), serverChanged = !equal(b,s);
    out.push({ path, base:b, local:l, server:s, conflict: localChanged && serverChanged, proposed: localChanged ? 'local' : 'server' });
  }
  for (const key of new Set([...Object.keys(base),...Object.keys(local),...Object.keys(server)])) visit(field(base,key),field(local,key),field(server,key),[key]);
  return out;
}
export function mergeProfiles(server: Record<string, unknown>, differences: ProfileDifference[], choices: Record<string, 'local' | 'server'>): Record<string, unknown> {
  const result = structuredClone(server);
  for (const item of differences) {
    const choice = choices[JSON.stringify(item.path)] ?? (item.conflict ? undefined : item.proposed);
    if (!choice) throw new Error('Choose a value for every conflicting field.');
    const selected = item[choice]; let target = result;
    for (const key of item.path.slice(0,-1)) {
      if (!Object.hasOwn(target,key) || !object(target[key])) Object.defineProperty(target,key,{value:{},enumerable:true,configurable:true,writable:true});
      target = target[key] as Record<string, unknown>;
    }
    const last = item.path.at(-1)!;
    if (selected.present) Object.defineProperty(target, last, { value: structuredClone(selected.value), enumerable:true, configurable:true, writable:true });
    else delete target[last];
  }
  return result;
}

/**
 * Path-based reads and immutable writes over the profile draft.
 *
 * The profile is a deep, mostly-static shape edited field by field. Threading
 * a setter per field would be dozens of near-identical closures; a path is the
 * smaller idea, and every write returns a new object so React sees the change.
 */

export type Path = (string | number)[];

export function get(obj: unknown, path: Path): unknown {
  return path.reduce<unknown>(
    (acc, key) => (acc == null ? undefined : (acc as Record<string | number, unknown>)[key]),
    obj,
  );
}

export function setIn<T>(obj: T, path: Path, value: unknown): T {
  if (path.length === 0) return value as T;
  const [head, ...rest] = path;
  const key = head as string | number;

  if (Array.isArray(obj)) {
    const next = [...obj];
    next[key as number] = setIn(next[key as number], rest, value);
    return next as T;
  }
  const source = (obj ?? {}) as Record<string | number, unknown>;
  return { ...source, [key]: setIn(source[key], rest, value) } as T;
}

/** Cast a form input's string to the type the field actually holds. */
export function castInput(raw: string, cast: 'string' | 'number' | 'float'): unknown {
  if (cast === 'string') return raw;
  if (raw === '') return null;
  const parsed = cast === 'number' ? Number.parseInt(raw, 10) : Number.parseFloat(raw);
  return Number.isNaN(parsed) ? null : parsed;
}

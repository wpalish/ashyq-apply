from pathlib import Path
import hashlib,json
r=Path(__file__).resolve().parent;repo=r.parents[1]/'work/unimatch-calendar-materials';out=r/'dates5b-proposal';out.mkdir(exist_ok=False)
paths=['frontend/src/lib/format.ts','frontend/src/lib/format.test.ts','frontend/src/lib/format.dates.test.ts','frontend/src/screens/ApprovedScreen.tsx','frontend/src/screens/DocumentsScreen.tsx','frontend/src/screens/ShortlistScreen.tsx','frontend/src/components/ResultDetail.tsx'];rows={}
for p in paths:
 f=repo/p;raw=f.read_bytes() if f.exists() else None;rows[p]=hashlib.sha256(raw).hexdigest() if raw is not None else None
 if raw is not None:q=r/'dates5b-preimages'/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_bytes(raw)
def put(p,t):q=out/p;q.parent.mkdir(parents=True,exist_ok=True);q.write_text(t)
(r/'DATES_5B_PREPARATION.json').write_text(json.dumps({'status':'EXTERNAL_ONLY_NOT_GRANTED_NOT_APPLIED','paths':rows,'baseline':'9e41e0b3','scope':'Calendar-only display preserves exact date in all browser time zones; real Instant timezone display separated. Source date comparison only in known IANA zone, earlier calendar date not official closure. Do not consume stored deadline_passed in visible current deadline highlights.'},indent=2)+'\n')
p=paths[0];t=(repo/p).read_text();a=t.index('export function date(');b=t.index('\n/** Turn any ',a)
t=t[:a]+'''/** A calendar date remains a calendar date. UTC is only the Intl formatting carrier. */
export function localDate(iso: string | null | undefined, locale = DISPLAY_LOCALE): string {
  if (!iso) return NOT_FOUND;
  const match = /^(\\d{4})-(\\d{2})-(\\d{2})$/.exec(iso); if (!match) return iso;
  const year = Number(match[1]); const month = Number(match[2]); const day = Number(match[3]);
  const carrier = new Date(0); carrier.setUTCFullYear(year, month - 1, day); carrier.setUTCHours(12, 0, 0, 0);
  if (carrier.getUTCFullYear() !== year || carrier.getUTCMonth() !== month - 1 || carrier.getUTCDate() !== day) return iso;
  return new Intl.DateTimeFormat(locale, { day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC' }).format(carrier);
}
export function date(iso: string | null | undefined): string {
  if (!iso) return NOT_FOUND;
  if (/^\\d{4}-\\d{2}-\\d{2}$/.test(iso)) return localDate(iso);
  const d = new Date(iso); if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleDateString(DISPLAY_LOCALE, { day: '2-digit', month: 'short', year: 'numeric' });
}
/** Only an offset-bearing timestamp is an Instant; a date-only value has no event time. */
export function dateTime(iso: string | null | undefined, timezone?: string): string {
  if (!iso) return 'never';
  if (!/T.*(?:Z|[+-]\\d{2}:\\d{2})$/.test(iso)) return iso;
  const d = new Date(iso); if (Number.isNaN(d.getTime())) return iso;
  try { return d.toLocaleString(DISPLAY_LOCALE, {
    day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', ...(timezone ? { timeZone: timezone } : {}),
  }); } catch { return iso; }
}
/** Calendar ordering never establishes the actual university closing time. */
export function sourceDatePosition(iso: string | null | undefined, timezone: string | null | undefined, now = new Date()): 'earlier' | 'same' | 'later' | 'unknown' {
  if (!iso || !timezone || !/^\\d{4}-\\d{2}-\\d{2}$/.test(iso) || Number.isNaN(now.getTime())) return 'unknown';
  try {
    const parts = new Intl.DateTimeFormat('en-CA', { timeZone: timezone, year: 'numeric', month: '2-digit', day: '2-digit' }).formatToParts(now);
    const part = (type: string) => parts.find(item => item.type === type)?.value;
    const today = `${part('year')}-${part('month')}-${part('day')}`;
    return iso < today ? 'earlier' : iso > today ? 'later' : 'same';
  } catch { return 'unknown'; }
}
''' +t[b:];put(p,t)
p=paths[1];t=(repo/p).read_text().replace("day: '2-digit', month: 'short', year: 'numeric',\n      }),", "day: '2-digit', month: 'short', year: 'numeric', timeZone: 'UTC',\n      }),",1);put(p,t)
put(paths[2],'''import { afterEach, expect, it, vi } from 'vitest';
import { date, dateTime, localDate, sourceDatePosition } from './format';
afterEach(() => { vi.restoreAllMocks(); });
it.each(['America/New_York', 'Asia/Almaty', 'UTC'])('keeps calendar date under an Intl default zone of %s', zone => {
  const NativeFormatter = Intl.DateTimeFormat;
  vi.spyOn(Intl, 'DateTimeFormat').mockImplementation((locales, options) => new NativeFormatter(locales, { timeZone: zone, ...options }));
  expect(localDate('2027-01-15', 'en-GB')).toBe('15 Jan 2027'); expect(date('2027-01-15')).toMatch(/15/);
});
it('compares known zones across midnight without using the current UTC day', () => {
  const midnight = new Date('2026-10-14T00:30:00Z');
  expect(sourceDatePosition('2026-10-13', 'America/New_York', midnight)).toBe('same');
  expect(sourceDatePosition('2026-10-13', 'Asia/Almaty', midnight)).toBe('earlier');
  expect(sourceDatePosition('2026-10-14', 'UTC', midnight)).toBe('same');
});
it('keeps unknown zones and missing dates explicitly incomparable', () => {
  const now = new Date('2026-10-14T00:30:00Z');
  expect(sourceDatePosition('2020-01-01', null, now)).toBe('unknown');
  expect(sourceDatePosition('2026-10-13', 'Not/AZone', now)).toBe('unknown'); expect(sourceDatePosition(null, 'UTC', now)).toBe('unknown');
});
it('formats an actual Instant across New York DST and does not invent time for LocalDate', () => {
  const early = dateTime('2026-11-01T05:30:00Z', 'America/New_York'); const late = dateTime('2026-11-01T06:30:00Z', 'America/New_York');
  expect(early).toBe(late); expect(dateTime('2026-11-01')).toBe('2026-11-01');
});
it('never normalizes an invalid leap date into a different calendar day', () => {
  expect(localDate('2027-02-29', 'en-GB')).toBe('2027-02-29'); expect(localDate('2028-02-29', 'en-GB')).toBe('29 Feb 2028');
});
''')
p=paths[3];t=(repo/p).read_text().replace('fundingClassTone, money','fundingClassTone, money, sourceDatePosition',1)
t=t.replace("  const today = new Date().toISOString().slice(0, 10);\n",'').replace("result.admission_deadline && result.admission_deadline >= today", "result.admission_deadline && sourceDatePosition(result.admission_deadline, result.admission_deadline_timezone) !== 'earlier'",1)
t=t.replace('`Next deadline: ${nextDeadline.university}`', '`Closest recorded date: ${nextDeadline.university}`',1)
t=t.replace('No future admission deadline has been confirmed for these programmes.', 'No current admission date is confirmed here. Review the original programme requirements.',1)
t=t.replace("            {shortlisted === 0 && onFind", "            {nextDeadline && <p className=\"small muted\">A calendar date does not establish the closing time. {nextDeadline.admission_deadline_timezone ?? 'Time zone unknown.'}</p>}\n            {shortlisted === 0 && onFind",1);put(p,t)
p=paths[4];t=(repo/p).read_text().replace('date, dateTime','date, dateTime, sourceDatePosition',1).replace("    const today = new Date().toISOString().slice(0, 10);\n",'').replace('past: r.admission_deadline < today',"past: sourceDatePosition(r.admission_deadline, r.admission_deadline_timezone) === 'earlier'").replace('past: s.deadline < today',"past: sourceDatePosition(s.deadline, s.deadline_timezone) === 'earlier'").replace('<Chip tone="risk">passed</Chip>','<Chip tone="warn">Earlier calendar date</Chip>')
t=t.replace('          <div className="timeline">', '          <p className="small muted">Calendar dates have no confirmed closing time here. An unknown time zone prevents a precise expiry comparison.</p>\n          <div className="timeline">',1);put(p,t)
p=paths[5];t=(repo/p).read_text().replace('percent, ratio,','percent, ratio, sourceDatePosition,',1).replace('{r.deadline_passed && <div><Chip tone="risk">passed</Chip></div>}',"{sourceDatePosition(r.admission_deadline, r.admission_deadline_timezone) === 'earlier' && <div><Chip tone=\"warn\">Earlier calendar date</Chip></div>}\n                          {r.admission_deadline && !r.admission_deadline_timezone && <div className=\"xs muted\">Time zone unknown</div>}");put(p,t)
p=paths[6];t=(repo/p).read_text().replace('percent, ratio,','percent, ratio, sourceDatePosition,',1).replace('{result.deadline_passed && <Chip tone="risk">deadline passed</Chip>}', "{sourceDatePosition(result.admission_deadline, result.admission_deadline_timezone) === 'earlier' && <Chip tone=\"warn\">Earlier calendar date</Chip>}\n        {result.admission_deadline && <span className=\"xs muted\">Closing time not confirmed{!result.admission_deadline_timezone ? ' · time zone unknown' : ''}.</span>}");put(p,t)
print('External calendar display/comparison proposal; source unchanged during gate.')

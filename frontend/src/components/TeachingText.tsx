import { createElement, Fragment, type ReactNode } from 'react';

/** A finite, escaped student-text renderer. Unsupported syntax remains literal text. */
function inline(text: string): ReactNode[] {
  const parts: ReactNode[] = [];
  const tokens = /`([^`\n]+)`|\*\*([^*\n]+)\*\*|\*([^*\s](?:[^*\n]*[^*\s])?)\*/g;
  let from = 0;
  for (const match of text.matchAll(tokens)) {
    const at = match.index;
    parts.push(text.slice(from, at));
    const content = match[1] ?? match[2] ?? match[3];
    const tag = match[1] !== undefined ? 'code' : match[2] !== undefined ? 'strong' : 'em';
    parts.push(createElement(tag, { key: at }, content));
    from = at + match[0].length;
  }
  parts.push(text.slice(from));
  return parts;
}
function cells(line: string): string[] {
  let content = line.trim();
  if (content.startsWith('|')) content = content.slice(1);
  if (content.endsWith('|')) content = content.slice(0, -1);
  return content.split(/(?<!\\)\|/).map(cell => cell.trim().replace(/\\\|/g, '|'));
}
function tableHeader(lines: string[], at: number): boolean {
  const header = lines[at]; const separator = lines[at + 1];
  if (!header?.includes('|') || !separator?.includes('|')) return false;
  const labels = cells(header); const rules = cells(separator);
  return labels.length > 1 && labels.length === rules.length && rules.every(cell => /^:?-{3,}:?$/.test(cell));
}
const listItem = (line: string) => /^\s*(?:([-+*])|(\d+)[.)])\s+(.+)$/.exec(line);
const heading = (line: string) => /^(#{1,4})\s+(.+)$/.exec(line);

export function TeachingText({ text, minHeadingLevel=3 }: { text: string; minHeadingLevel?:2|3 }) {
  const lines = text.replace(/\r\n?/g, '\n').split('\n');
  const blocks: ReactNode[] = [];
  let at = 0;
  let tableNumber = 0;
  while (at < lines.length) {
    const line = lines[at]!;
    if (!line.trim()) { ++at; continue; }
    const title = heading(line);
    if (title) {
      blocks.push(createElement(`h${Math.max(minHeadingLevel, Math.min(6, title[1]!.length))}`, { key: at }, inline(title[2]!)));
      ++at; continue;
    }
    if (tableHeader(lines, at)) {
      const key = at; const header = cells(line); const rows: string[][] = [];
      at += 2;
      while (at < lines.length && lines[at]!.trim() && lines[at]!.includes('|')) {
        rows.push(cells(lines[at]!)); ++at;
      }
      blocks.push(<div key={key} className="preparation-teaching__table" tabIndex={0} role="region" aria-label={`Lesson table ${++tableNumber}`}>
        <table><thead><tr>{header.map((cell, index) => <th scope="col" key={index}>{inline(cell)}</th>)}</tr></thead>
          <tbody>{rows.map((row, index) => <tr key={index}>{row.map((cell, column) => <td key={column}>{inline(cell)}</td>)}</tr>)}</tbody>
        </table>
      </div>);
      continue;
    }
    const firstItem = listItem(line);
    if (firstItem) {
      const key = at; const ordered = firstItem[2] !== undefined; const items: ReactNode[] = [];
      while (at < lines.length) {
        const match = listItem(lines[at]!);
        if (!match || (match[2] !== undefined) !== ordered) break;
        items.push(<li key={at} value={ordered ? Number(match[2]) : undefined}>{inline(match[3]!)}</li>); ++at;
      }
      blocks.push(ordered ? <ol key={key} start={Number(firstItem[2])}>{items}</ol> : <ul key={key}>{items}</ul>);
      continue;
    }
    const key = at; const paragraph: string[] = [line]; ++at;
    while (at < lines.length && lines[at]!.trim() && !heading(lines[at]!) && !listItem(lines[at]!) && !tableHeader(lines, at)) {
      paragraph.push(lines[at]!); ++at;
    }
    blocks.push(<p key={key}>{paragraph.map((item, index) => <Fragment key={index}>{index > 0 && <br />}{inline(item)}</Fragment>)}</p>);
  }
  return <div className="preparation-teaching stack stack--tight">{blocks}</div>;
}

import { useEffect, useRef, useState, type InputHTMLAttributes } from 'react';

const EMPTY_ITEMS: readonly string[] = [];
const parseItems = (text: string) => text.split(',').map((item) => item.trim()).filter(Boolean);

type Props = Omit<InputHTMLAttributes<HTMLInputElement>, 'value' | 'defaultValue' | 'onChange'> & {
  items?: readonly string[];
  onItemsChange: (items: string[]) => void;
};

/** Keep unfinished separators in the input while the profile stores clean lists. */
export function CommaSeparatedInput({ items = EMPTY_ITEMS, onItemsChange, onBlur, ...props }: Props) {
  const [text, setText] = useState(() => items.join(', '));
  const emittedItems = useRef<readonly string[] | null>(null);

  useEffect(() => {
    // A store update from this input must preserve the text just typed.
    // A replacement from a case switch, demo load or clear must replace it.
    if (items !== emittedItems.current) {
      setText(items.join(', '));
      emittedItems.current = null;
    }
  }, [items]);

  return <input
    {...props}
    value={text}
    onChange={(event) => {
      const raw = event.currentTarget.value;
      const parsed = parseItems(raw);
      emittedItems.current = parsed;
      setText(raw);
      onItemsChange(parsed);
    }}
    onBlur={(event) => {
      setText(parseItems(event.currentTarget.value).join(', '));
      onBlur?.(event);
    }}
  />;
}

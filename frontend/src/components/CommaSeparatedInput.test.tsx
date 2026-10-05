import { useState } from 'react';
import { fireEvent, render, screen } from '@testing-library/react';
import { expect, it } from 'vitest';
import { CommaSeparatedInput } from './CommaSeparatedInput';

function Harness() {
  const [items, setItems] = useState<string[]>([]);
  const [counter, setCounter] = useState(0);
  return <>
    <CommaSeparatedInput aria-label="Countries" items={items} onItemsChange={setItems} />
    <output data-testid="items">{JSON.stringify(items)}</output>
    <button onClick={() => setCounter(counter + 1)}>unrelated update {counter}</button>
    <button onClick={() => setItems(['United Kingdom'])}>switch case</button>
    <button onClick={() => setItems([...items])}>replace list</button>
    <button onClick={() => setItems([])}>clear</button>
  </>;
}

it('keeps unfinished text through unrelated updates and normalizes only on blur', () => {
  render(<Harness />);
  const input = screen.getByLabelText('Countries');
  fireEvent.change(input, { target: { value: ' Canada,  Czech Republic, ' } });
  expect(input).toHaveValue(' Canada,  Czech Republic, ');
  expect(screen.getByTestId('items')).toHaveTextContent('["Canada","Czech Republic"]');
  fireEvent.click(screen.getByRole('button', { name: 'unrelated update 0' }));
  expect(input).toHaveValue(' Canada,  Czech Republic, ');
  fireEvent.blur(input);
  expect(input).toHaveValue('Canada, Czech Republic');
});

it('replaces local text when the parent loads a different case or clears the profile', () => {
  render(<Harness />);
  const input = screen.getByLabelText('Countries');
  fireEvent.change(input, { target: { value: 'Canada, ' } });
  fireEvent.click(screen.getByRole('button', { name: 'switch case' }));
  expect(input).toHaveValue('United Kingdom');
  fireEvent.click(screen.getByRole('button', { name: 'clear' }));
  expect(input).toHaveValue('');
  fireEvent.change(input, { target: { value: ', ' } });
  fireEvent.click(screen.getByRole('button', { name: 'clear' }));
  expect(input).toHaveValue('');
});

it('honours an external replacement even when its parsed values are unchanged', () => {
  render(<Harness />);
  const input = screen.getByLabelText('Countries');
  fireEvent.change(input, { target: { value: 'Canada, ' } });
  fireEvent.click(screen.getByRole('button', { name: 'replace list' }));
  expect(input).toHaveValue('Canada');
});

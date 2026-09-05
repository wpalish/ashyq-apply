/**
 * Community component guarantees.
 *
 * Three rules the UI must not break: an unstated status is shown as unstated
 * and never as a waitlist, the composer shows the tags it will publish before
 * you publish them, and a post that would be rejected by the server cannot be
 * submitted from the client.
 */

import { act, fireEvent, render, screen } from '@testing-library/react';
import { describe, expect, it, vi } from 'vitest';
import { Body, Composer, POST_MAX_CHARS, Retract, StatusChip, initials, statusLabel } from './social';

function type(value: string): HTMLTextAreaElement {
  const box = screen.getByRole('textbox') as HTMLTextAreaElement;
  fireEvent.change(box, { target: { value } });
  return box;
}

describe('status', () => {
  it('says a status was not stated rather than assuming a waitlist', () => {
    expect(statusLabel(null)).toBe('Status not stated');
    render(<StatusChip status={null} />);
    expect(screen.getByText('Status not stated')).toHaveAttribute(
      'title',
      expect.stringContaining('has not said'),
    );
  });

  it('labels the two statuses the product defines', () => {
    expect(statusLabel('accepted')).toBe('Accepted');
    expect(statusLabel('waitlist')).toBe('On a waitlist');
  });
});

describe('initials', () => {
  it('takes one letter from each of the first two words', () => {
    expect(initials('Aigerim Nurlanovna')).toBe('AN');
  });

  it('takes two letters when there is only one word', () => {
    expect(initials('Dias')).toBe('DI');
  });

  it('handles a name in Cyrillic', () => {
    expect(initials('Алишер Нурсаин')).toBe('АН');
  });

  it('never renders an empty tile', () => {
    expect(initials('   ')).toBe('?');
  });
});

describe('Body', () => {
  it('marks the tags inside a post without touching the rest of the text', () => {
    render(<Body text="Кто подаётся в #KBTU в этом году?" />);
    expect(screen.getByText('#KBTU')).toBeInTheDocument();
    expect(screen.getByText(/Кто подаётся в/)).toBeInTheDocument();
  });
});

describe('Retract', () => {
  it('asks before deleting, and names what goes', () => {
    render(<Retract question="Delete this post and its answers?" onConfirm={vi.fn()} />);

    fireEvent.click(screen.getByRole('button', { name: 'Delete' }));
    expect(screen.getByText('Delete this post and its answers?')).toBeInTheDocument();
  });

  it('deletes nothing if you change your mind', () => {
    const onConfirm = vi.fn();
    render(<Retract question="Delete this post?" onConfirm={onConfirm} />);

    fireEvent.click(screen.getByRole('button', { name: 'Delete' }));
    fireEvent.click(screen.getByRole('button', { name: 'Keep it' }));

    expect(onConfirm).not.toHaveBeenCalled();
    expect(screen.getByRole('button', { name: 'Delete' })).toBeInTheDocument();
  });

  it('deletes once confirmed', async () => {
    const onConfirm = vi.fn().mockResolvedValue(undefined);
    render(<Retract question="Delete this answer?" onConfirm={onConfirm} />);

    fireEvent.click(screen.getByRole('button', { name: 'Delete' }));
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Yes, delete' }));
    });

    expect(onConfirm).toHaveBeenCalledTimes(1);
  });
});

describe('Composer', () => {
  it('shows the tags it will publish while you type', () => {
    render(<Composer placeholder="Say something" submitLabel="Post" onSubmit={vi.fn()} />);
    type('еду в #Astana учиться в #KBTU');

    expect(screen.getByText('Will be tagged')).toBeInTheDocument();
    expect(screen.getByText('#Astana')).toBeInTheDocument();
    expect(screen.getByText('#KBTU')).toBeInTheDocument();
  });

  it('collapses two spellings of one tag into one', () => {
    render(<Composer placeholder="Say something" submitLabel="Post" onSubmit={vi.fn()} />);
    type('#KBTU и ещё раз #kbtu');

    expect(screen.getAllByText(/^#kbtu$/i)).toHaveLength(1);
  });

  it('says nothing about tags when there are none', () => {
    render(<Composer placeholder="Say something" submitLabel="Post" onSubmit={vi.fn()} />);
    type('обычный вопрос без тегов');

    expect(screen.queryByText('Will be tagged')).not.toBeInTheDocument();
  });

  it('will not send an empty post', () => {
    render(<Composer placeholder="Say something" submitLabel="Post" onSubmit={vi.fn()} />);
    expect(screen.getByRole('button', { name: 'Post' })).toBeDisabled();
  });

  it('refuses to send a post the server would reject, and says by how much', () => {
    const onSubmit = vi.fn();
    render(<Composer placeholder="Say something" submitLabel="Post" onSubmit={onSubmit} />);
    type('x'.repeat(POST_MAX_CHARS + 3));

    expect(screen.getByText('3 over')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Post' })).toBeDisabled();
    expect(onSubmit).not.toHaveBeenCalled();
  });

  it('counts down the characters that are left', () => {
    render(<Composer placeholder="Say something" submitLabel="Post" onSubmit={vi.fn()} />);
    type('привет');

    expect(screen.getByText(`${POST_MAX_CHARS - 6} left`)).toBeInTheDocument();
  });

  it('sends the trimmed text and then clears itself', async () => {
    const onSubmit = vi.fn().mockResolvedValue(undefined);
    render(<Composer placeholder="Say something" submitLabel="Post" onSubmit={onSubmit} />);
    const box = type('  привет  ');

    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: 'Post' }));
    });

    expect(onSubmit).toHaveBeenCalledWith('привет');
    expect(box).toHaveValue('');
  });
});

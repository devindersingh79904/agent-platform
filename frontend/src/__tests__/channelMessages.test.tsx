import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import ChannelMessages from '../pages/ChannelMessages';

vi.mock('../api/client', () => ({
  getChannelMessages: vi.fn(() => Promise.resolve({ content: [] }))
}));

describe('ChannelMessages Component', () => {
  it('renders table correctly', () => {
    render(
      <BrowserRouter>
        <ChannelMessages />
      </BrowserRouter>
    );
    expect(screen.getByText(/Channel Messages/i)).toBeTruthy();
  });
});

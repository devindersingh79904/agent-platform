import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import SchedulesManager from '../pages/SchedulesManager';

vi.mock('../api/client', () => ({
  getSchedules: vi.fn(() => Promise.resolve({ content: [] })),
  getWorkflows: vi.fn(() => Promise.resolve({ content: [] })),
  createSchedule: vi.fn(),
  triggerSchedule: vi.fn(),
}));

describe('SchedulesManager Component', () => {
  it('renders correctly', () => {
    render(
      <BrowserRouter>
        <SchedulesManager />
      </BrowserRouter>
    );
    expect(screen.getByText(/Schedules/i)).toBeTruthy();
  });
});

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import MemoryManager from '../pages/MemoryManager';

// Mock the API client
vi.mock('../api/client', () => ({
  getAgents: vi.fn(() => Promise.resolve([])),
  getAgentMemories: vi.fn(() => Promise.resolve({ content: [] })),
  createAgentMemory: vi.fn(),
  deleteAgentMemory: vi.fn(),
}));

describe('MemoryManager Component', () => {
  it('renders loading state initially or empty state', () => {
    render(
      <BrowserRouter>
        <MemoryManager />
      </BrowserRouter>
    );
    expect(screen.getByText(/Memory Manager/i)).toBeTruthy();
  });
});

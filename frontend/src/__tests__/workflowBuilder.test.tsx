import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';
import WorkflowBuilder from '../pages/WorkflowBuilder';
import { MemoryRouter, Routes, Route } from 'react-router-dom';

// Mock xyflow to avoid complex DOM/ResizeObserver errors in jsdom
vi.mock('@xyflow/react', async () => {
  const actual = await vi.importActual('@xyflow/react');
  return {
    ...actual,
    ReactFlow: () => <div data-testid="react-flow-mock"></div>,
    MiniMap: () => null,
    Controls: () => null,
    Background: () => null,
    useNodesState: (initial: any) => {
      const [nodes, setNodes] = React.useState(initial);
      return [nodes, setNodes, vi.fn()];
    },
    useEdgesState: (initial: any) => {
      const [edges, setEdges] = React.useState(initial);
      return [edges, setEdges, vi.fn()];
    },
    addEdge: vi.fn(),
  };
});

vi.mock('axios', () => ({
  default: {
    create: vi.fn().mockReturnThis(),
    interceptors: {
      request: { use: vi.fn(), eject: vi.fn() },
      response: { use: vi.fn(), eject: vi.fn() },
    },
    get: vi.fn().mockImplementation((url) => {
      if (url.includes('/graph')) {
        // Delay response to simulate loading
        return new Promise((resolve) => setTimeout(() => resolve({ data: { success: true, data: { workflow: { id: 'test', name: 'Test' }, nodes: [], edges: [] } } }), 100));
      }
      return Promise.resolve({ data: { success: true, data: { id: 'test', name: 'Test' } } });
    }),
    put: vi.fn().mockResolvedValue({ data: { success: true } }),
    post: vi.fn().mockResolvedValue({ data: { success: true } }),
  }
}));

describe('WorkflowBuilder Behavior', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('disables Run and Save buttons while loading', async () => {
    render(
      <MemoryRouter initialEntries={['/workflows/test-id']}>
        <Routes>
          <Route path="/workflows/:workflowId" element={<WorkflowBuilder />} />
        </Routes>
      </MemoryRouter>
    );

    // Because get is delayed by 100ms, it should be in loading state
    const runBtn = screen.getByRole('button', { name: /Run/i }) as HTMLButtonElement;
    const saveBtn = screen.getByRole('button', { name: /Save/i }) as HTMLButtonElement;
    
    expect(runBtn.disabled).toBe(true);
    expect(saveBtn.disabled).toBe(true);
    
    // Wait for load workflow attempt to finish
    await screen.findByText(/Workflow Builder: Test/);
  });

  it('validates JSON and prevents save if invalid, allows save if valid', async () => {
    render(
      <MemoryRouter initialEntries={['/workflows/test-id']}>
        <Routes>
          <Route path="/workflows/:workflowId" element={<WorkflowBuilder />} />
        </Routes>
      </MemoryRouter>
    );

    // Wait for load workflow attempt to finish
    await screen.findByText(/Workflow Builder: Test/);
    
    // Wait until the Tool button is enabled
    await waitFor(() => {
      const btn = screen.getByRole('button', { name: /Tool/i }) as HTMLButtonElement;
      expect(btn.disabled).toBe(false);
    });

    const toolBtn = screen.getByRole('button', { name: /Tool/i });

    // Open Add Tool panel
    fireEvent.click(toolBtn);

    // Panel should open
    expect(screen.getByText('Add Tool Node')).toBeDefined();

    // Find textarea for config
    const textboxes = screen.getAllByRole('textbox');
    const configTextarea = textboxes[textboxes.length - 1];
    
    // Enter invalid JSON
    fireEvent.change(configTextarea, { target: { value: '{ invalid: json }' } });

    // Click Add (Save)
    const addBtn = screen.getByText('Add');
    fireEvent.click(addBtn);

    // Should show error and NOT close modal
    expect(screen.getByText('Tool config must be valid JSON.')).toBeDefined();
    expect(screen.getByText('Add Tool Node')).toBeDefined(); // Still open

    // Enter valid JSON
    fireEvent.change(configTextarea, { target: { value: '{"valid": "json"}' } });

    // Click Add (Save) again
    fireEvent.click(addBtn);

    // Modal should close (no longer finding 'Add Tool Node')
    expect(screen.queryByText('Add Tool Node')).toBeNull();
  });
});

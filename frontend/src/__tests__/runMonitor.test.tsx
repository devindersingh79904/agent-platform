import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import RunMonitor from '../pages/RunMonitor';
import * as client from '../api/client';
import { WS_EVENTS } from '../constants/wsEvents';
import { WORKFLOW_RUN_STATUS } from '../constants/workflow';

// Mock the API calls
vi.mock('../api/client', async () => {
  const actual = await vi.importActual('../api/client');
  return {
    ...actual as any,
    getRun: vi.fn(),
    getRunLogs: vi.fn(),
    getRunMessages: vi.fn(),
    getRunToolCalls: vi.fn(),
    getRunTokenUsage: vi.fn(),
    WS_BASE_URL: 'ws://localhost:8000',
    getOrCreateCorrelationId: vi.fn(() => 'FRONT-123')
  };
});

// Mock WebSocket
class MockWebSocket {
  onopen: any;
  onmessage: any;
  onerror: any;
  onclose: any;
  readyState: number = 1;
  url: string;
  
  constructor(url: string) {
    this.url = url;
    setTimeout(() => {
      if (this.onopen) this.onopen();
    }, 10);
  }
  
  send() {}
  close() {}
}

describe('RunMonitor Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (globalThis as any).WebSocket = MockWebSocket;
    
    // Default successful API mocks
    vi.mocked(client.getRun).mockResolvedValue({ id: 'run-1', status: WORKFLOW_RUN_STATUS.RUNNING, workflow_id: 'wf-1' });
    vi.mocked(client.getRunLogs).mockResolvedValue([{ id: 1, event_id: 1, event_type: WS_EVENTS.RUN_STARTED, event_sequence: 1 }]);
    vi.mocked(client.getRunMessages).mockResolvedValue([]);
    vi.mocked(client.getRunToolCalls).mockResolvedValue([]);
    vi.mocked(client.getRunTokenUsage).mockResolvedValue([]);
  });

  it('passes last_event_id in WebSocket URL when logs exist', async () => {
    let wsUrl = '';
    class TrackingMockWebSocket extends MockWebSocket {
      constructor(url: string) {
        super(url);
        wsUrl = url;
      }
    }
    (globalThis as any).WebSocket = TrackingMockWebSocket;

    render(
      <MemoryRouter initialEntries={['/runs/run-1']}>
        <Routes>
          <Route path="/runs/:runId" element={<RunMonitor />} />
        </Routes>
      </MemoryRouter>
    );

    await waitFor(() => {
      expect(client.getRunLogs).toHaveBeenCalled();
      expect(wsUrl).toContain('last_event_id=1');
    }, { timeout: 2000 });
  });

  it('updates status on RUN_COMPLETED and RUN_FAILED events', async () => {
    let wsInstance: any;
    class InjectableMockWebSocket extends MockWebSocket {
      constructor(url: string) {
        super(url);
        wsInstance = this;
      }
    }
    (globalThis as any).WebSocket = InjectableMockWebSocket;

    render(
      <MemoryRouter initialEntries={['/runs/run-1']}>
        <Routes>
          <Route path="/runs/:runId" element={<RunMonitor />} />
        </Routes>
      </MemoryRouter>
    );

    // Wait for initial render and WS connection
    const runningElements = await screen.findAllByText(/RUNNING/i);
    expect(runningElements.length).toBeGreaterThan(0);

    // Send RUN_COMPLETED event
    wsInstance.onmessage({
      data: JSON.stringify({
        event_type: WS_EVENTS.RUN_COMPLETED,
        payload: {}
      })
    });

    const completedElements = await screen.findAllByText(/COMPLETED/i);
    expect(completedElements.length).toBeGreaterThan(0);

    // Send RUN_FAILED event
    wsInstance.onmessage({
      data: JSON.stringify({
        event_type: WS_EVENTS.RUN_FAILED,
        payload: {}
      })
    });

    const failedElements = await screen.findAllByText(/FAILED/i);
    expect(failedElements.length).toBeGreaterThan(0);
  });
});

import { describe, it, expect, vi } from 'vitest';
import { getOrCreateCorrelationId } from '../api/client';
import api, { getAgents } from '../api/client';

describe('API Client', () => {
  it('generates a correlation ID starting with FRONT-', () => {
    const id = getOrCreateCorrelationId();
    expect(id).toMatch(/^FRONT-/);
    
    // Ensure subsequent calls return the same ID
    const id2 = getOrCreateCorrelationId();
    expect(id2).toBe(id);
  });

  it('unwraps response envelope correctly', async () => {
    // Mock api.get to return a wrapped response
    const mockData = { data: { data: { content: [{ id: '1' }] } } };
    const getSpy = vi.spyOn(api, 'get').mockResolvedValue(mockData as any);
    
    const agents = await getAgents();
    expect(agents).toEqual([{ id: '1' }]);
    getSpy.mockRestore();
  });
});



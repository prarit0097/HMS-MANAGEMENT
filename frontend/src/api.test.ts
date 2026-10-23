import { afterEach, describe, expect, it, vi } from 'vitest';
import { api, ApiError } from './api';
afterEach(() => vi.unstubAllGlobals());
describe('authorised API boundary', () => {
  it('sends session cookies and the current CSRF token with a mutation', async () => {
    document.cookie = 'csrftoken=rotated-token';
    const fetcher = vi.fn().mockResolvedValue(new Response(JSON.stringify({id: 'new'})));
    vi.stubGlobal('fetch', fetcher);
    await api('patients/', {method: 'POST', body: JSON.stringify({full_name: 'Synthetic test'})});
    const [url, options] = fetcher.mock.calls[0];
    expect(url).toBe('/api/v1/patients/');
    expect(options.credentials).toBe('same-origin');
    expect(options.headers.get('X-CSRFToken')).toBe('rotated-token');
  });
  it('preserves the denied response and field errors instead of returning fake success', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(JSON.stringify({code: 'denied', message: 'Access denied', field_errors: {branch: ['Not assigned']}}), {status:403})));
    await expect(api('patients/')).rejects.toMatchObject({status:403, message:'Access denied', fields:{branch:['Not assigned']}});
  });
  it('turns an unreachable server into an actionable connection error', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new TypeError('Failed to fetch')));
    await expect(api('patients/')).rejects.toBeInstanceOf(ApiError);
    await expect(api('patients/')).rejects.toMatchObject({status:0});
  });
  it('accepts an empty logout response', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null,{status:204})));
    await expect(api('auth/logout/', {method:'POST'})).resolves.toBeUndefined();
  });
});

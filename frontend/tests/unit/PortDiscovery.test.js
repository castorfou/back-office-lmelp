/**
 * Tests for dynamic port discovery functionality in frontend
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import fs from 'fs';
import path from 'path';

// Mock fs module
vi.mock('fs');

describe('PortDiscovery - Frontend', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.resetAllMocks();
  });

  it('should read backend port from discovery file', async () => {
    // Mock file content
    const mockPortData = {
      port: 54321,
      host: "localhost",
      timestamp: Math.floor(Date.now() / 1000), // Current timestamp in seconds
      url: "http://localhost:54321"
    };

    // Mock fs.readFileSync to return our test data
    vi.mocked(fs.readFileSync).mockReturnValue(JSON.stringify(mockPortData));
    vi.mocked(fs.existsSync).mockReturnValue(true);

    // Import the function we'll create
    const { readBackendPort } = await import('../../src/utils/portDiscovery.js');

    const result = readBackendPort();

    expect(result.port).toBe(54321);
    expect(result.host).toBe("localhost");
    expect(result.url).toBe("http://localhost:54321");
  });

  it('should handle missing port discovery file gracefully', async () => {
    // Mock file not existing
    vi.mocked(fs.existsSync).mockReturnValue(false);

    const { readBackendPort } = await import('../../src/utils/portDiscovery.js');

    const result = readBackendPort();

    // Should return default values when file doesn't exist
    expect(result.port).toBe(54322); // Default fallback port from current vite.config.js
    expect(result.host).toBe("localhost");
    expect(result.url).toBe("http://localhost:54322");
  });

  it('should handle corrupted port discovery file', async () => {
    // Mock file existing but with invalid JSON
    vi.mocked(fs.existsSync).mockReturnValue(true);
    vi.mocked(fs.readFileSync).mockReturnValue('invalid json content');

    const { readBackendPort } = await import('../../src/utils/portDiscovery.js');

    const result = readBackendPort();

    // Should return default values when file is corrupted
    expect(result.port).toBe(54322);
    expect(result.host).toBe("localhost");
  });

  it('should use correct port discovery file path', async () => {
    const mockPortData = {
      port: 54321,
      host: "localhost",
      timestamp: Math.floor(Date.now() / 1000), // Current timestamp in seconds
      url: "http://localhost:54321"
    };

    vi.mocked(fs.readFileSync).mockReturnValue(JSON.stringify(mockPortData));
    vi.mocked(fs.existsSync).mockReturnValue(true);

    const { readBackendPort } = await import('../../src/utils/portDiscovery.js');

    readBackendPort();

    // Verify it's looking in the correct location (project root)
    const expectedPath = path.resolve(process.cwd(), '../.backend-port.json');
    expect(fs.existsSync).toHaveBeenCalledWith(expectedPath);
  });

  it('should handle stale port discovery file', async () => {
    // Mock old timestamp (older than 30 seconds)
    const staleTimestamp = Math.floor((Date.now() - 60000) / 1000); // 60 seconds ago in seconds
    const mockPortData = {
      port: 54321,
      host: "localhost",
      timestamp: staleTimestamp,
      url: "http://localhost:54321"
    };

    vi.mocked(fs.existsSync).mockReturnValue(true);
    vi.mocked(fs.readFileSync).mockReturnValue(JSON.stringify(mockPortData));

    const { readBackendPort } = await import('../../src/utils/portDiscovery.js');

    const result = readBackendPort();

    // Should return default values for stale file
    expect(result.port).toBe(54322);
    expect(result.host).toBe("localhost");
  });
});

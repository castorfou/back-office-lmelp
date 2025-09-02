/**
 * Port discovery utility for frontend to dynamically discover backend port
 */

import fs from 'fs';
import path from 'path';

/**
 * Maximum age for port discovery file (in milliseconds)
 * Files older than this are considered stale
 */
const MAX_FILE_AGE = 30 * 1000; // 30 seconds

/**
 * Default port configuration when discovery fails
 */
const DEFAULT_CONFIG = {
  port: 54322,
  host: 'localhost',
  url: 'http://localhost:54322'
};

/**
 * Read backend port information from discovery file
 * @returns {Object} Port configuration object
 */
function readBackendPort() {
  const portFilePath = path.resolve(process.cwd(), '../.backend-port.json');
  const isTestMode = process.env.NODE_ENV === 'test' || process.env.VITEST;

  try {
    // Check if file exists
    if (!fs.existsSync(portFilePath)) {
      if (!isTestMode) {
        console.warn('Backend port discovery file not found, using default port');
      }
      return DEFAULT_CONFIG;
    }

    // Read and parse file
    const fileContent = fs.readFileSync(portFilePath, 'utf8');
    const portData = JSON.parse(fileContent);

    // Check if file is stale
    const currentTime = Date.now();
    const fileAge = currentTime - (portData.timestamp * 1000);

    if (fileAge > MAX_FILE_AGE) {
      if (!isTestMode) {
        console.warn('Backend port discovery file is stale, using default port');
      }
      return DEFAULT_CONFIG;
    }

    // Validate required fields
    if (!portData.port || !portData.host) {
      if (!isTestMode) {
        console.warn('Invalid port discovery file format, using default port');
      }
      return DEFAULT_CONFIG;
    }

    return {
      port: portData.port,
      host: portData.host,
      url: portData.url || `http://${portData.host}:${portData.port}`
    };

  } catch (error) {
    if (!isTestMode) {
      console.warn('Failed to read backend port discovery file:', error.message);
    }
    return DEFAULT_CONFIG;
  }
}

export {
  readBackendPort
};

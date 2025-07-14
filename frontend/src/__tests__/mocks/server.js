/**
 * MSW server setup for testing
 * This sets up the mock service worker for intercepting HTTP requests during tests
 */

import { setupServer } from 'msw/node';
import { handlers } from './handlers';

// Setup MSW server with our handlers
export const server = setupServer(...handlers);

export { server as mockServer };
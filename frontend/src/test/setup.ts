// Test setup file
import { vi } from 'vitest';

// Mock window object for Phaser tests
global.window = global.window || {} as any;

// Mock localStorage
const localStorageMock = {
  getItem: vi.fn(),
  setItem: vi.fn(),
  removeItem: vi.fn(),
  clear: vi.fn(),
};
global.localStorage = localStorageMock as any;

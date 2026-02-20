// Test setup file
import { vi } from 'vitest';

// Mock window object for Phaser tests
global.window = global.window || {} as any;

// Mock localStorage с реальным хранилищем (setItem/getItem/removeItem/clear работают)
const store: Record<string, string> = {};
const localStorageMock = {
  getItem: vi.fn((key: string) => store[key] ?? null),
  setItem: vi.fn((key: string, value: string) => {
    store[key] = String(value);
  }),
  removeItem: vi.fn((key: string) => {
    delete store[key];
  }),
  clear: vi.fn(() => {
    for (const key of Object.keys(store)) delete store[key];
  }),
  get length() {
    return Object.keys(store).length;
  },
  key: vi.fn((i: number) => Object.keys(store)[i] ?? null),
};
global.localStorage = localStorageMock as Storage;

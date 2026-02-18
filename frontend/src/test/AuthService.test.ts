import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { AuthService, TokenData } from '../AuthService';

const API_URL = 'http://localhost:8000';

describe('AuthService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('login', () => {
    it('should successfully login with valid credentials', async () => {
      const mockTokenData: TokenData = {
        access_token: 'test-token',
        token_type: 'bearer',
        user_id: 'user123',
        username: 'testuser',
      };

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => mockTokenData,
      });

      const result = await AuthService.login('testuser', 'password123');

      expect(result).toEqual(mockTokenData);
      expect(global.fetch).toHaveBeenCalledWith(
        `${API_URL}/api/login`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ username: 'testuser', password: 'password123' }),
        }
      );
    });

    it('should throw error on failed login', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        json: async () => ({ detail: 'Incorrect username or password' }),
      });

      await expect(
        AuthService.login('testuser', 'wrongpassword')
      ).rejects.toThrow('Incorrect username or password');
    });

    it('should handle network errors', async () => {
      global.fetch = vi.fn().mockRejectedValue(new Error('Network error'));

      await expect(
        AuthService.login('testuser', 'password123')
      ).rejects.toThrow();
    });

    it('should handle invalid JSON response', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        json: async () => {
          throw new Error('Invalid JSON');
        },
      });

      await expect(
        AuthService.login('testuser', 'password123')
      ).rejects.toThrow('Ошибка входа');
    });
  });

  describe('register', () => {
    it('should successfully register a new user', async () => {
      const mockTokenData: TokenData = {
        access_token: 'new-token',
        token_type: 'bearer',
        user_id: 'newuser123',
        username: 'newuser',
      };

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => mockTokenData,
      });

      const result = await AuthService.register(
        'newuser',
        'newuser@example.com',
        'password123'
      );

      expect(result).toEqual(mockTokenData);
      expect(global.fetch).toHaveBeenCalledWith(
        `${API_URL}/api/register`,
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            username: 'newuser',
            email: 'newuser@example.com',
            password: 'password123',
          }),
        }
      );
    });

    it('should throw error on duplicate username', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
        json: async () => ({ detail: 'Username already registered' }),
      });

      await expect(
        AuthService.register('existinguser', 'existing@example.com', 'password123')
      ).rejects.toThrow('Username already registered');
    });

    it('should handle network errors during registration', async () => {
      global.fetch = vi.fn().mockRejectedValue(new Error('Network error'));

      await expect(
        AuthService.register('newuser', 'newuser@example.com', 'password123')
      ).rejects.toThrow();
    });
  });

  describe('getCurrentUser', () => {
    it('should successfully get current user data', async () => {
      const mockUserData = {
        user_id: 'user123',
        username: 'testuser',
      };

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => mockUserData,
      });

      const result = await AuthService.getCurrentUser('test-token');

      expect(result).toEqual(mockUserData);
      expect(global.fetch).toHaveBeenCalledWith(
        `${API_URL}/api/me`,
        {
          headers: {
            'Authorization': 'Bearer test-token',
          },
        }
      );
    });

    it('should throw error on invalid token', async () => {
      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
      });

      await expect(
        AuthService.getCurrentUser('invalid-token')
      ).rejects.toThrow('Ошибка получения данных пользователя');
    });

    it('should handle network errors', async () => {
      global.fetch = vi.fn().mockRejectedValue(new Error('Network error'));

      await expect(
        AuthService.getCurrentUser('test-token')
      ).rejects.toThrow();
    });
  });
});

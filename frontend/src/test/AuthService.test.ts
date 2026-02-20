import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { AuthService, TokenData } from '../AuthService';

const API_URL = 'http://localhost:8000';

describe('AuthService', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Очищаем localStorage перед каждым тестом
    localStorage.clear();
  });

  afterEach(() => {
    vi.restoreAllMocks();
    // Очищаем localStorage после каждого теста
    localStorage.clear();
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

  describe('saveToken', () => {
    it('should save token and user data to localStorage', () => {
      const tokenData: TokenData = {
        access_token: 'test-token-123',
        token_type: 'bearer',
        user_id: 'user456',
        username: 'saveduser',
      };

      AuthService.saveToken(tokenData);

      expect(localStorage.getItem('game_auth_token')).toBe('test-token-123');
      const userData = JSON.parse(localStorage.getItem('game_user_data')!);
      expect(userData).toEqual({
        user_id: 'user456',
        username: 'saveduser',
      });
    });
  });

  describe('getToken', () => {
    it('should return token from localStorage', () => {
      localStorage.setItem('game_auth_token', 'stored-token');

      const token = AuthService.getToken();

      expect(token).toBe('stored-token');
    });

    it('should return null if token does not exist', () => {
      const token = AuthService.getToken();

      expect(token).toBeNull();
    });
  });

  describe('getUserData', () => {
    it('should return user data from localStorage', () => {
      const userData = { user_id: 'user789', username: 'testuser' };
      localStorage.setItem('game_user_data', JSON.stringify(userData));

      const result = AuthService.getUserData();

      expect(result).toEqual(userData);
    });

    it('should return null if user data does not exist', () => {
      const result = AuthService.getUserData();

      expect(result).toBeNull();
    });

    it('should handle invalid JSON gracefully', () => {
      localStorage.setItem('game_user_data', 'invalid-json');

      expect(() => AuthService.getUserData()).toThrow();
    });
  });

  describe('clearToken', () => {
    it('should remove token and user data from localStorage', () => {
      localStorage.setItem('game_auth_token', 'test-token');
      localStorage.setItem('game_user_data', JSON.stringify({ user_id: '123', username: 'test' }));

      AuthService.clearToken();

      expect(localStorage.getItem('game_auth_token')).toBeNull();
      expect(localStorage.getItem('game_user_data')).toBeNull();
    });

    it('should not throw error if tokens do not exist', () => {
      expect(() => AuthService.clearToken()).not.toThrow();
    });
  });

  describe('hasToken', () => {
    it('should return true if token exists', () => {
      localStorage.setItem('game_auth_token', 'test-token');

      expect(AuthService.hasToken()).toBe(true);
    });

    it('should return false if token does not exist', () => {
      expect(AuthService.hasToken()).toBe(false);
    });
  });

  describe('validateToken', () => {
    it('should return token data if token is valid', async () => {
      const token = 'valid-token';
      localStorage.setItem('game_auth_token', token);
      localStorage.setItem('game_user_data', JSON.stringify({
        user_id: 'user123',
        username: 'testuser',
      }));

      const mockUserData = {
        user_id: 'user123',
        username: 'testuser',
      };

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => mockUserData,
      });

      const result = await AuthService.validateToken();

      expect(result).toEqual({
        access_token: token,
        token_type: 'bearer',
        user_id: 'user123',
        username: 'testuser',
      });
      expect(global.fetch).toHaveBeenCalledWith(
        `${API_URL}/api/me`,
        {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        }
      );
    });

    it('should return null if token does not exist', async () => {
      const result = await AuthService.validateToken();

      expect(result).toBeNull();
      expect(global.fetch).not.toHaveBeenCalled();
    });

    it('should return null and clear token if token is invalid', async () => {
      const token = 'invalid-token';
      localStorage.setItem('game_auth_token', token);
      localStorage.setItem('game_user_data', JSON.stringify({
        user_id: 'user123',
        username: 'testuser',
      }));

      global.fetch = vi.fn().mockResolvedValue({
        ok: false,
      });

      const result = await AuthService.validateToken();

      expect(result).toBeNull();
      expect(localStorage.getItem('game_auth_token')).toBeNull();
      expect(localStorage.getItem('game_user_data')).toBeNull();
    });

    it('should return null and clear token on network error', async () => {
      const token = 'test-token';
      localStorage.setItem('game_auth_token', token);

      global.fetch = vi.fn().mockRejectedValue(new Error('Network error'));

      const result = await AuthService.validateToken();

      expect(result).toBeNull();
      expect(localStorage.getItem('game_auth_token')).toBeNull();
    });
  });

  describe('login with token saving', () => {
    it('should save token to localStorage after successful login', async () => {
      const mockTokenData: TokenData = {
        access_token: 'login-token',
        token_type: 'bearer',
        user_id: 'user999',
        username: 'loggeduser',
      };

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => mockTokenData,
      });

      await AuthService.login('loggeduser', 'password123');

      expect(localStorage.getItem('game_auth_token')).toBe('login-token');
      const userData = JSON.parse(localStorage.getItem('game_user_data')!);
      expect(userData).toEqual({
        user_id: 'user999',
        username: 'loggeduser',
      });
    });
  });

  describe('register with token saving', () => {
    it('should save token to localStorage after successful registration', async () => {
      const mockTokenData: TokenData = {
        access_token: 'register-token',
        token_type: 'bearer',
        user_id: 'user888',
        username: 'newuser',
      };

      global.fetch = vi.fn().mockResolvedValue({
        ok: true,
        json: async () => mockTokenData,
      });

      await AuthService.register('newuser', 'newuser@example.com', 'password123');

      expect(localStorage.getItem('game_auth_token')).toBe('register-token');
      const userData = JSON.parse(localStorage.getItem('game_user_data')!);
      expect(userData).toEqual({
        user_id: 'user888',
        username: 'newuser',
      });
    });
  });
});

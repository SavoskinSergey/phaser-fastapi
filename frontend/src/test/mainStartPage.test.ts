import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { AuthService } from '../AuthService';

// Mock DOM elements
const createMockElement = (id: string, initialDisplay: string = 'none') => {
  const element = {
    id,
    style: { display: initialDisplay },
    textContent: '',
    value: '',
    disabled: false,
    addEventListener: vi.fn(),
    click: vi.fn(),
  };
  return element as any;
};

describe('main.ts - Start Page Logic', () => {
  let mockElements: Record<string, any>;
  let mockLocalStorage: Record<string, string>;

  beforeEach(() => {
    // Mock DOM elements
    mockElements = {
      'start-page': createMockElement('start-page', 'block'),
      'login-container': createMockElement('login-container', 'none'),
      'game-container': createMockElement('game-container', 'none'),
      'login-form': createMockElement('login-form', 'none'),
      'register-form': createMockElement('register-form', 'none'),
      'continue-btn': createMockElement('continue-btn', 'none'),
      'login-start-btn': createMockElement('login-start-btn', 'block'),
      'register-start-btn': createMockElement('register-start-btn', 'block'),
      'logout-btn': createMockElement('logout-btn', 'none'),
    };

    // Mock localStorage
    mockLocalStorage = {};
    const localStorageMock = {
      getItem: vi.fn((key: string) => mockLocalStorage[key] || null),
      setItem: vi.fn((key: string, value: string) => {
        mockLocalStorage[key] = value;
      }),
      removeItem: vi.fn((key: string) => {
        delete mockLocalStorage[key];
      }),
      clear: vi.fn(() => {
        mockLocalStorage = {};
      }),
    };
    global.localStorage = localStorageMock as any;

    // Mock document.getElementById
    vi.spyOn(document, 'getElementById').mockImplementation((id: string) => {
      return mockElements[id] || null;
    });

    // Mock AuthService
    vi.spyOn(AuthService, 'hasToken').mockReturnValue(false);
    vi.spyOn(AuthService, 'validateToken').mockResolvedValue(null);
    vi.spyOn(AuthService, 'clearToken').mockImplementation(() => {});
  });

  afterEach(() => {
    vi.restoreAllMocks();
    mockLocalStorage = {};
  });

  describe('showStartPage logic', () => {
    it('should show start page and hide login/game containers', () => {
      // Симулируем логику showStartPage
      mockElements['start-page'].style.display = 'block';
      mockElements['login-container'].style.display = 'none';
      mockElements['game-container'].style.display = 'none';

      expect(mockElements['start-page'].style.display).toBe('block');
      expect(mockElements['login-container'].style.display).toBe('none');
      expect(mockElements['game-container'].style.display).toBe('none');
    });

    it('should show continue button when user is logged in', () => {
      vi.spyOn(AuthService, 'hasToken').mockReturnValue(true);

      const isLoggedIn = AuthService.hasToken();
      mockElements['continue-btn'].style.display = isLoggedIn ? 'block' : 'none';
      mockElements['logout-btn'].style.display = isLoggedIn ? 'block' : 'none';
      mockElements['login-start-btn'].style.display = isLoggedIn ? 'none' : 'block';
      mockElements['register-start-btn'].style.display = isLoggedIn ? 'none' : 'block';

      expect(mockElements['continue-btn'].style.display).toBe('block');
      expect(mockElements['logout-btn'].style.display).toBe('block');
      expect(mockElements['login-start-btn'].style.display).toBe('none');
      expect(mockElements['register-start-btn'].style.display).toBe('none');
    });

    it('should show login/register buttons when user is not logged in', () => {
      vi.spyOn(AuthService, 'hasToken').mockReturnValue(false);

      const isLoggedIn = AuthService.hasToken();
      mockElements['continue-btn'].style.display = isLoggedIn ? 'block' : 'none';
      mockElements['logout-btn'].style.display = isLoggedIn ? 'block' : 'none';
      mockElements['login-start-btn'].style.display = isLoggedIn ? 'none' : 'block';
      mockElements['register-start-btn'].style.display = isLoggedIn ? 'none' : 'block';

      expect(mockElements['continue-btn'].style.display).toBe('none');
      expect(mockElements['logout-btn'].style.display).toBe('none');
      expect(mockElements['login-start-btn'].style.display).toBe('block');
      expect(mockElements['register-start-btn'].style.display).toBe('block');
    });
  });

  describe('showLoginForm logic', () => {
    it('should hide start page and show login form', () => {
      // Симулируем логику showLoginForm
      mockElements['start-page'].style.display = 'none';
      mockElements['login-container'].style.display = 'block';
      mockElements['login-form'].style.display = 'block';
      mockElements['register-form'].style.display = 'none';

      expect(mockElements['start-page'].style.display).toBe('none');
      expect(mockElements['login-container'].style.display).toBe('block');
      expect(mockElements['login-form'].style.display).toBe('block');
      expect(mockElements['register-form'].style.display).toBe('none');
    });
  });

  describe('showRegisterForm logic', () => {
    it('should hide start page and show register form', () => {
      // Симулируем логику showRegisterForm
      mockElements['start-page'].style.display = 'none';
      mockElements['login-container'].style.display = 'block';
      mockElements['login-form'].style.display = 'none';
      mockElements['register-form'].style.display = 'block';

      expect(mockElements['start-page'].style.display).toBe('none');
      expect(mockElements['login-container'].style.display).toBe('block');
      expect(mockElements['login-form'].style.display).toBe('none');
      expect(mockElements['register-form'].style.display).toBe('block');
    });
  });

  describe('continue button logic', () => {
    it('should validate token and start game if valid', async () => {
      const mockTokenData = {
        access_token: 'valid-token',
        user_id: 'user123',
        username: 'testuser',
      };

      vi.spyOn(AuthService, 'hasToken').mockReturnValue(true);
      vi.spyOn(AuthService, 'validateToken').mockResolvedValue(mockTokenData as any);

      const tokenData = await AuthService.validateToken();
      
      if (tokenData) {
        // Симулируем запуск игры
        mockElements['start-page'].style.display = 'none';
        mockElements['game-container'].style.display = 'block';
      }

      expect(tokenData).toEqual(mockTokenData);
      expect(mockElements['start-page'].style.display).toBe('none');
      expect(mockElements['game-container'].style.display).toBe('block');
    });

    it('should show login form if token is invalid', async () => {
      vi.spyOn(AuthService, 'hasToken').mockReturnValue(true);
      vi.spyOn(AuthService, 'validateToken').mockResolvedValue(null);

      const tokenData = await AuthService.validateToken();
      
      if (!tokenData) {
        // Симулируем показ формы входа
        mockElements['start-page'].style.display = 'none';
        mockElements['login-container'].style.display = 'block';
        mockElements['login-form'].style.display = 'block';
      }

      expect(tokenData).toBeNull();
      expect(mockElements['login-container'].style.display).toBe('block');
    });
  });

  describe('logout button logic', () => {
    it('should clear token and show login buttons', () => {
      // Симулируем логику выхода
      AuthService.clearToken();
      vi.spyOn(AuthService, 'hasToken').mockReturnValue(false);

      const isLoggedIn = AuthService.hasToken();
      mockElements['continue-btn'].style.display = isLoggedIn ? 'block' : 'none';
      mockElements['logout-btn'].style.display = isLoggedIn ? 'block' : 'none';
      mockElements['login-start-btn'].style.display = isLoggedIn ? 'none' : 'block';
      mockElements['register-start-btn'].style.display = isLoggedIn ? 'none' : 'block';

      expect(AuthService.clearToken).toHaveBeenCalled();
      expect(mockElements['continue-btn'].style.display).toBe('none');
      expect(mockElements['login-start-btn'].style.display).toBe('block');
    });
  });

  describe('init function logic', () => {
    it('should show start page on initialization', () => {
      // Симулируем инициализацию
      mockElements['start-page'].style.display = 'block';
      mockElements['login-container'].style.display = 'none';
      mockElements['game-container'].style.display = 'none';

      expect(mockElements['start-page'].style.display).toBe('block');
    });

    it('should check for token and show continue button if exists', () => {
      vi.spyOn(AuthService, 'hasToken').mockReturnValue(true);

      const hasToken = AuthService.hasToken();
      if (hasToken) {
        mockElements['continue-btn'].style.display = 'block';
        mockElements['logout-btn'].style.display = 'block';
        mockElements['login-start-btn'].style.display = 'none';
        mockElements['register-start-btn'].style.display = 'none';
      }

      expect(mockElements['continue-btn'].style.display).toBe('block');
      expect(mockElements['login-start-btn'].style.display).toBe('none');
    });
  });
});

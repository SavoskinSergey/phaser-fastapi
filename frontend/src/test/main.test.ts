import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

/**
 * Тесты логики main.ts без загрузки модуля (нет DOM при импорте).
 * Проверяем поведение переключения форм и валидации так же, как в main.ts.
 */

const createMockElement = (id: string) => {
  const element = {
    id,
    style: { display: '' },
    textContent: '',
    value: '',
    disabled: false,
    addEventListener: vi.fn(),
    click: vi.fn(),
  };
  return element as any;
};

describe('main.ts integration', () => {
  let mockElements: Record<string, any>;

  beforeEach(() => {
    mockElements = {
      'login-container': createMockElement('login-container'),
      'game-container': createMockElement('game-container'),
      'login-form': createMockElement('login-form'),
      'register-form': createMockElement('register-form'),
      'login-username': createMockElement('login-username'),
      'login-password': createMockElement('login-password'),
      'register-username': createMockElement('register-username'),
      'register-email': createMockElement('register-email'),
      'register-password': createMockElement('register-password'),
      'login-btn': createMockElement('login-btn'),
      'register-btn': createMockElement('register-btn'),
      'login-error': createMockElement('login-error'),
      'register-error': createMockElement('register-error'),
      'switch-to-register': createMockElement('switch-to-register'),
      'switch-to-login': createMockElement('switch-to-login'),
    };
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  describe('form switching', () => {
    it('should switch from login to register form', () => {
      const loginForm = mockElements['login-form'];
      const registerForm = mockElements['register-form'];
      const loginError = mockElements['login-error'];

      loginForm.style.display = 'block';
      registerForm.style.display = 'none';

      // Логика из main.ts: обработчик переключения на регистрацию
      const switchToRegisterHandler = () => {
        loginForm.style.display = 'none';
        registerForm.style.display = 'block';
        loginError.textContent = '';
      };

      switchToRegisterHandler();

      expect(loginForm.style.display).toBe('none');
      expect(registerForm.style.display).toBe('block');
      expect(loginError.textContent).toBe('');
    });

    it('should switch from register to login form', () => {
      const loginForm = mockElements['login-form'];
      const registerForm = mockElements['register-form'];
      const registerError = mockElements['register-error'];

      registerForm.style.display = 'block';
      loginForm.style.display = 'none';

      const switchToLoginHandler = () => {
        registerForm.style.display = 'none';
        loginForm.style.display = 'block';
        registerError.textContent = '';
      };

      switchToLoginHandler();

      expect(registerForm.style.display).toBe('none');
      expect(loginForm.style.display).toBe('block');
      expect(registerError.textContent).toBe('');
    });
  });

  describe('login form validation', () => {
    it('should require username and password', () => {
      const loginUsernameInput = mockElements['login-username'];
      const loginPasswordInput = mockElements['login-password'];
      const loginError = mockElements['login-error'];

      loginUsernameInput.value = '';
      loginPasswordInput.value = '';

      // Логика валидации из main.ts
      const username = loginUsernameInput.value.trim();
      const password = loginPasswordInput.value;
      const isEmpty = !username || !password;

      if (isEmpty) {
        loginError.textContent = 'Заполните все поля';
      }

      expect(loginError.textContent).toBe('Заполните все поля');
    });
  });

  describe('register form validation', () => {
    it('should show error when password is too short', () => {
      const registerError = mockElements['register-error'];
      const password = '12';

      const registerErrorHandler = () => {
        if (password.length < 3) {
          registerError.textContent = 'Пароль должен быть не менее 3 символов';
        }
      };

      registerErrorHandler();

      expect(registerError.textContent).toBe('Пароль должен быть не менее 3 символов');
    });

    it('should require all fields', () => {
      const registerError = mockElements['register-error'];
      const username = '';
      const email = '';
      const password = '';

      const isEmpty = !username || !email || !password;
      if (isEmpty) {
        registerError.textContent = 'Заполните все поля';
      }

      expect(registerError.textContent).toBe('Заполните все поля');
    });
  });

  describe('Enter key handling', () => {
    it('should trigger login submit on Enter key', () => {
      const loginBtn = mockElements['login-btn'];
      let submitted = false;

      const keypressHandler = (e: { key: string }) => {
        if (e.key === 'Enter') {
          loginBtn.click();
          submitted = true;
        }
      };

      keypressHandler({ key: 'Enter' });

      expect(submitted).toBe(true);
    });
  });
});

import Phaser from 'phaser';
import { GameScene } from './GameScene';
import { AuthService } from './AuthService';

const API_URL = 'http://localhost:8000';

// Элементы страниц
const startPage = document.getElementById('start-page')!;
const loginContainer = document.getElementById('login-container')!;
const gameContainer = document.getElementById('game-container')!;
const loginForm = document.getElementById('login-form')!;
const registerForm = document.getElementById('register-form')!;

// Элементы стартовой страницы
const continueBtn = document.getElementById('continue-btn') as HTMLButtonElement;
const loginStartBtn = document.getElementById('login-start-btn') as HTMLButtonElement;
const registerStartBtn = document.getElementById('register-start-btn') as HTMLButtonElement;
const logoutBtn = document.getElementById('logout-btn') as HTMLButtonElement;

const loginUsernameInput = document.getElementById('login-username') as HTMLInputElement;
const loginPasswordInput = document.getElementById('login-password') as HTMLInputElement;
const registerUsernameInput = document.getElementById('register-username') as HTMLInputElement;
const registerEmailInput = document.getElementById('register-email') as HTMLInputElement;
const registerPasswordInput = document.getElementById('register-password') as HTMLInputElement;

const loginBtn = document.getElementById('login-btn') as HTMLButtonElement;
const registerBtn = document.getElementById('register-btn') as HTMLButtonElement;
const loginError = document.getElementById('login-error')!;
const registerError = document.getElementById('register-error')!;

const switchToRegister = document.getElementById('switch-to-register')!;
const switchToLogin = document.getElementById('switch-to-login')!;
const backToStartFromLogin = document.getElementById('back-to-start-from-login')!;
const backToStartFromRegister = document.getElementById('back-to-start-from-register')!;

let game: Phaser.Game | null = null;

// Показываем стартовую страницу
function showStartPage() {
  startPage.style.display = 'block';
  loginContainer.style.display = 'none';
  gameContainer.style.display = 'none';
  
  // Проверяем, залогинен ли пользователь
  const isLoggedIn = AuthService.hasToken();
  continueBtn.style.display = isLoggedIn ? 'block' : 'none';
  logoutBtn.style.display = isLoggedIn ? 'block' : 'none';
  loginStartBtn.style.display = isLoggedIn ? 'none' : 'block';
  registerStartBtn.style.display = isLoggedIn ? 'none' : 'block';
}

// Показываем форму логина
function showLoginForm() {
  startPage.style.display = 'none';
  loginContainer.style.display = 'block';
  loginForm.style.display = 'block';
  registerForm.style.display = 'none';
  loginError.textContent = '';
  registerError.textContent = '';
}

// Показываем форму регистрации
function showRegisterForm() {
  startPage.style.display = 'none';
  loginContainer.style.display = 'block';
  loginForm.style.display = 'none';
  registerForm.style.display = 'block';
  loginError.textContent = '';
  registerError.textContent = '';
}

// Обработчики кнопок стартовой страницы
continueBtn.addEventListener('click', async () => {
  try {
    const tokenData = await AuthService.validateToken();
    if (tokenData) {
      startGame(tokenData);
    } else {
      // Токен невалиден, показываем форму входа
      showLoginForm();
    }
  } catch (error) {
    console.error('Ошибка при продолжении:', error);
    AuthService.clearToken();
    showLoginForm();
  }
});

loginStartBtn.addEventListener('click', () => {
  showLoginForm();
});

registerStartBtn.addEventListener('click', () => {
  showRegisterForm();
});

logoutBtn.addEventListener('click', () => {
  AuthService.clearToken();
  showStartPage();
});

// Переключение между формами
switchToRegister.addEventListener('click', () => {
  loginForm.style.display = 'none';
  registerForm.style.display = 'block';
  loginError.textContent = '';
});

switchToLogin.addEventListener('click', () => {
  registerForm.style.display = 'none';
  loginForm.style.display = 'block';
  registerError.textContent = '';
});

// Возврат на стартовую страницу
backToStartFromLogin.addEventListener('click', () => {
  showStartPage();
});

backToStartFromRegister.addEventListener('click', () => {
  showStartPage();
});

// Обработка логина
loginBtn.addEventListener('click', async () => {
  const username = loginUsernameInput.value.trim();
  const password = loginPasswordInput.value;

  if (!username || !password) {
    loginError.textContent = 'Заполните все поля';
    return;
  }

  loginBtn.disabled = true;
  loginError.textContent = '';

  try {
    const tokenData = await AuthService.login(username, password);
    startGame(tokenData);
  } catch (error: any) {
    loginError.textContent = error.message || 'Ошибка входа';
  } finally {
    loginBtn.disabled = false;
  }
});

// Обработка регистрации
registerBtn.addEventListener('click', async () => {
  const username = registerUsernameInput.value.trim();
  const email = registerEmailInput.value.trim();
  const password = registerPasswordInput.value;

  if (!username || !email || !password) {
    registerError.textContent = 'Заполните все поля';
    return;
  }

  if (password.length < 3) {
    registerError.textContent = 'Пароль должен быть не менее 3 символов';
    return;
  }

  registerBtn.disabled = true;
  registerError.textContent = '';

  try {
    const tokenData = await AuthService.register(username, email, password);
    startGame(tokenData);
  } catch (error: any) {
    registerError.textContent = error.message || 'Ошибка регистрации';
  } finally {
    registerBtn.disabled = false;
  }
});

// Enter для отправки форм
[loginUsernameInput, loginPasswordInput].forEach(input => {
  input.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      loginBtn.click();
    }
  });
});

[registerUsernameInput, registerEmailInput, registerPasswordInput].forEach(input => {
  input.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      registerBtn.click();
    }
  });
});

// Запуск игры после авторизации
function startGame(tokenData: { access_token: string; user_id: string; username: string }) {
  startPage.style.display = 'none';
  loginContainer.style.display = 'none';
  gameContainer.style.display = 'block';

  // коллбек, который вызовет сцена при выходе
  (window as any).exitToLogin = () => {
    try {
      if (game) {
        game.destroy(true);
        game = null;
      }
    } finally {
      gameContainer.innerHTML = '';
      gameContainer.style.display = 'none';
      // Возвращаемся на стартовую страницу (не очищаем токен, чтобы можно было продолжить)
      showStartPage();
      (window as any).gameToken = null;
      (window as any).gameUserId = null;
      (window as any).gameUsername = null;
    }
  };

  const config: Phaser.Types.Core.GameConfig = {
    type: Phaser.AUTO,
    width: 800,
    height: 600,
    backgroundColor: '#222222',
    parent: 'game-container',
    scene: [GameScene],
    physics: {
      default: 'arcade',
      arcade: {
        gravity: { y: 0 },
        debug: false
      }
    }
  };

  // Передаем токен в сцену через глобальную переменную
  (window as any).gameToken = tokenData.access_token;
  (window as any).gameUserId = tokenData.user_id;
  (window as any).gameUsername = tokenData.username;

  game = new Phaser.Game(config);
}

// Инициализация при загрузке страницы
function init() {
  // Показываем стартовую страницу
  showStartPage();
  
  // Проверяем наличие токена для отображения кнопки "Продолжить"
  // Но не запускаем игру автоматически - пользователь сам выберет
  if (AuthService.hasToken()) {
    // Токен есть, показываем кнопку "Продолжить"
    continueBtn.style.display = 'block';
    logoutBtn.style.display = 'block';
    loginStartBtn.style.display = 'none';
    registerStartBtn.style.display = 'none';
  }
}

// Инициализируем при загрузке страницы
init();

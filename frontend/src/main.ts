import Phaser from 'phaser';
import { GameScene } from './GameScene';
import { AuthService } from './AuthService';

const API_URL = 'http://localhost:8000';

// Элементы формы
const loginContainer = document.getElementById('login-container')!;
const gameContainer = document.getElementById('game-container')!;
const loginForm = document.getElementById('login-form')!;
const registerForm = document.getElementById('register-form')!;

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

let game: Phaser.Game | null = null;

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
      loginContainer.style.display = 'block';
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

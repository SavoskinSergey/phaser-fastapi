import Phaser from 'phaser';
import { GameScene } from './GameScene';
import { AuthService } from './AuthService';

const API_URL = 'http://localhost:8000';

// Элементы страниц
const startPage = document.getElementById('start-page')!;
const loginContainer = document.getElementById('login-container')!;
const gameContainer = document.getElementById('game-container')!;
const profilePage = document.getElementById('profile-page')!;
const loginForm = document.getElementById('login-form')!;
const registerForm = document.getElementById('register-form')!;

// Элементы стартовой страницы
const continueBtn = document.getElementById('continue-btn') as HTMLButtonElement;
const profileStartBtn = document.getElementById('profile-start-btn') as HTMLButtonElement;
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

const profileUsername = document.getElementById('profile-username')!;
const profileBalance = document.getElementById('profile-balance')!;
const profileBonusList = document.getElementById('profile-bonus-list')!;
const profileTaskList = document.getElementById('profile-task-list')!;
const profileToMainBtn = document.getElementById('profile-to-main-btn') as HTMLButtonElement;
const profileToGameBtn = document.getElementById('profile-to-game-btn') as HTMLButtonElement;
const profileLogoutBtn = document.getElementById('profile-logout-btn') as HTMLButtonElement;
const profileInventoryBtn = document.getElementById('profile-inventory-btn') as HTMLButtonElement;

const inventoryPage = document.getElementById('inventory-page')!;
const invBalance = document.getElementById('inv-balance')!;
const invList = document.getElementById('inv-list')!;
const invToMainBtn = document.getElementById('inv-to-main-btn') as HTMLButtonElement;
const invToGameBtn = document.getElementById('inv-to-game-btn') as HTMLButtonElement;
const invBackBtn = document.getElementById('inv-back-btn') as HTMLButtonElement;

const taskModal = document.getElementById('task-modal')!;
const taskRequiredText = document.getElementById('task-required-text')!;
const taskErrorText = document.getElementById('task-error-text')!;
const taskRewardText = document.getElementById('task-reward-text')!;
const taskSubmitBtn = document.getElementById('task-submit-btn') as HTMLButtonElement;
const taskCloseBtn = document.getElementById('task-close-btn') as HTMLButtonElement;

let game: Phaser.Game | null = null;
let profileOpenedFromGame = false;
let inventoryOpenedFromGame = false;

// Показываем стартовую страницу
function showStartPage() {
  startPage.style.display = 'block';
  loginContainer.style.display = 'none';
  gameContainer.style.display = 'none';
  profilePage.style.display = 'none';
  inventoryPage.style.display = 'none';
  taskModal.classList.remove('show');
  profileOpenedFromGame = false;
  inventoryOpenedFromGame = false;

  const isLoggedIn = AuthService.hasToken();
  continueBtn.style.display = isLoggedIn ? 'block' : 'none';
  profileStartBtn.style.display = isLoggedIn ? 'block' : 'none';
  logoutBtn.style.display = isLoggedIn ? 'block' : 'none';
  loginStartBtn.style.display = isLoggedIn ? 'none' : 'block';
  registerStartBtn.style.display = isLoggedIn ? 'none' : 'block';
}

// Показываем форму логина
function showLoginForm() {
  startPage.style.display = 'none';
  loginContainer.style.display = 'block';
  profilePage.style.display = 'none';
  inventoryPage.style.display = 'none';
  loginForm.style.display = 'block';
  registerForm.style.display = 'none';
  loginError.textContent = '';
  registerError.textContent = '';
}

// Показываем страницу профиля (с главной или из игры)
async function showProfilePage(fromGame: boolean = false) {
  profileOpenedFromGame = fromGame;
  startPage.style.display = 'none';
  loginContainer.style.display = 'none';
  gameContainer.style.display = 'none';
  inventoryPage.style.display = 'none';
  profilePage.style.display = 'block';
  profileToGameBtn.style.display = fromGame ? 'block' : 'none';

  const token = AuthService.getToken();
  if (!token) {
    showStartPage();
    return;
  }
  try {
    const res = await fetch(`${API_URL}/api/me/profile`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    if (!res.ok) {
      showStartPage();
      return;
    }
    const data = await res.json();
    profileUsername.textContent = data.username || '—';
    profileBalance.textContent = String(data.balance_points ?? 0);
    const bonusList = data.recent_bonus_collections || [];
    profileBonusList.innerHTML = bonusList.length === 0
      ? '<li style="color:#666">Пока нет собранных бонусов</li>'
      : bonusList.map((b: { points: number; bonus_type: number; collected_at: string | null }) => {
          const date = b.collected_at ? new Date(b.collected_at).toLocaleString() : '—';
          return `<li>+${b.points} (тип ${b.bonus_type}) — ${date}</li>`;
        }).join('');
    const taskList = data.recent_task_completions || [];
    profileTaskList.innerHTML = taskList.length === 0
      ? '<li style="color:#666">Пока нет выполненных заданий</li>'
      : taskList.map((t: { reward_points: number; reward_item_1: number; reward_item_2: number; completed_at: string | null }) => {
          const date = t.completed_at ? new Date(t.completed_at).toLocaleString() : '—';
          return `<li>+${t.reward_points} очков, полуфабрикаты: ${t.reward_item_1}, ${t.reward_item_2} — ${date}</li>`;
        }).join('');
  } catch {
    showStartPage();
  }
}

function hideProfilePage() {
  profilePage.style.display = 'none';
}

const ITEM_PRICES: Record<number, number> = { 1: 10, 2: 20, 3: 30 };

async function showInventoryPage(fromGame: boolean = false) {
  inventoryOpenedFromGame = fromGame;
  startPage.style.display = 'none';
  loginContainer.style.display = 'none';
  gameContainer.style.display = 'none';
  profilePage.style.display = 'none';
  inventoryPage.style.display = 'block';
  invToGameBtn.style.display = fromGame ? 'block' : 'none';

  const token = AuthService.getToken();
  if (!token) {
    showStartPage();
    return;
  }
  try {
    const [meRes, invRes] = await Promise.all([
      fetch(`${API_URL}/api/me`, { headers: { Authorization: `Bearer ${token}` } }),
      fetch(`${API_URL}/api/me/inventory`, { headers: { Authorization: `Bearer ${token}` } }),
    ]);
    if (!meRes.ok || !invRes.ok) {
      showStartPage();
      return;
    }
    const me = await meRes.json();
    const inv = await invRes.json();
    invBalance.textContent = String(me.balance_points ?? 0);
    const items = inv.items || {};
    invList.innerHTML = [1, 2, 3].map((t) => {
      const qty = Number(items[String(t)] ?? 0);
      const price = ITEM_PRICES[t] ?? 0;
      return `<div class="inv-item">
        <span>Элемент типа ${t}: ${qty} шт. (покупка: ${price} очков)</span>
        <button type="button" data-buy="${t}">Купить</button>
      </div>`;
    }).join('');
    invList.querySelectorAll('[data-buy]').forEach((b) => {
      (b as HTMLButtonElement).addEventListener('click', () => {
        buyItemAndRefresh(parseInt((b as HTMLElement).dataset.buy!, 10));
      });
    });
  } catch {
    showStartPage();
  }
}

async function buyItemAndRefresh(itemType: number) {
  const token = AuthService.getToken();
  if (!token) return;
  const res = await fetch(`${API_URL}/api/me/inventory/buy`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` },
    body: JSON.stringify({ item_type: itemType }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    alert(err.detail || 'Не удалось купить');
    return;
  }
  const data = await res.json();
  invBalance.textContent = String(data.balance_points);
  const items2 = data.items || {};
  invList.innerHTML = [1, 2, 3].map((t) => {
    const qty = Number(items2[String(t)] ?? 0);
    const price = ITEM_PRICES[t] ?? 0;
    return `<div class="inv-item">
      <span>Элемент типа ${t}: ${qty} шт. (покупка: ${price} очков)</span>
      <button type="button" data-buy="${t}">Купить</button>
    </div>`;
  }).join('');
  invList.querySelectorAll('[data-buy]').forEach((btn) => {
    (btn as HTMLButtonElement).addEventListener('click', () => buyItemAndRefresh(parseInt((btn as HTMLElement).dataset.buy!, 10)));
  });
}

function hideInventoryPage() {
  inventoryPage.style.display = 'none';
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

profileStartBtn.addEventListener('click', () => {
  showProfilePage(false);
});

profileInventoryBtn.addEventListener('click', () => {
  profilePage.style.display = 'none';
  showInventoryPage(false);
});

profileToMainBtn.addEventListener('click', () => {
  showStartPage();
});

profileToGameBtn.addEventListener('click', () => {
  hideProfilePage();
  gameContainer.style.display = 'block';
  profileToGameBtn.style.display = 'none';
});

profileLogoutBtn.addEventListener('click', () => {
  AuthService.clearToken();
  profileOpenedFromGame = false;
  showStartPage();
});

invToMainBtn.addEventListener('click', () => {
  showStartPage();
});
invToGameBtn.addEventListener('click', () => {
  hideInventoryPage();
  gameContainer.style.display = 'block';
});
invBackBtn.addEventListener('click', () => {
  if (inventoryOpenedFromGame) {
    hideInventoryPage();
    gameContainer.style.display = 'block';
  } else {
    hideInventoryPage();
    profilePage.style.display = 'block';
  }
});

taskCloseBtn.addEventListener('click', () => {
  taskModal.classList.remove('show');
  taskErrorText.style.display = 'none';
  taskRewardText.style.display = 'none';
});
taskSubmitBtn.addEventListener('click', () => {
  const submitTask = (window as any).gameSubmitTask;
  if (typeof submitTask === 'function') submitTask();
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
  profilePage.style.display = 'none';
  inventoryPage.style.display = 'none';
  gameContainer.style.display = 'block';

  (window as any).goToProfile = () => {
    gameContainer.style.display = 'none';
    showProfilePage(true);
  };

  (window as any).goToInventory = () => {
    gameContainer.style.display = 'none';
    showInventoryPage(true);
  };

  (window as any).openTaskModal = (task: { id: string; required_type_1: number; required_type_2: number; required_type_3: number; reward_points: number }) => {
    taskRequiredText.textContent = `Сдать: тип 1 — ${task.required_type_1} шт., тип 2 — ${task.required_type_2} шт., тип 3 — ${task.required_type_3} шт. Награда: ${task.reward_points} очков + 2 полуфабриката.`;
    taskErrorText.style.display = 'none';
    taskRewardText.style.display = 'none';
    (window as any).__currentTask = task;
    taskModal.classList.add('show');
  };
  (window as any).closeTaskModal = (reward?: { reward_points?: number; reward_item_1?: number; reward_item_2?: number }) => {
    if (reward && (reward.reward_points != null || reward.reward_item_1 != null)) {
      taskRewardText.textContent = `Получено: ${reward.reward_points ?? 0} очков, полуфабрикаты: тип ${reward.reward_item_1 ?? 0}, тип ${reward.reward_item_2 ?? 0}`;
      taskRewardText.style.display = 'block';
      taskErrorText.style.display = 'none';
      setTimeout(() => {
        taskModal.classList.remove('show');
        taskRewardText.style.display = 'none';
      }, 2500);
    } else {
      taskModal.classList.remove('show');
      taskRewardText.style.display = 'none';
    }
  };

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

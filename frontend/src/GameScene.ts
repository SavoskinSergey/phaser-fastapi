import Phaser from 'phaser';

const TILE_SIZE = 56;

interface PlayerState {
  x: number;
  y: number;
  username?: string;
  balance_points?: number;
}

interface PlayersState {
  [playerId: string]: PlayerState;
}

interface BonusItem {
  id: string;
  type: number; // 1 яблоко | 2 апельсин | 3 ананас
  tile_x: number;
  tile_y: number;
}

interface MapTaskItem {
  id: string;
  tile_x: number;
  tile_y: number;
  level: number; // 1 | 2 | 3
  required_type_1: number;
  required_type_2: number;
  required_type_3: number;
  reward_points: number;
  reward_ingredient_count: number;
}

export class GameScene extends Phaser.Scene {
  private ws?: WebSocket;
  private playerId: string = '';
  private username: string = '';
  private mySprite?: Phaser.GameObjects.Sprite;
  private myLabel?: Phaser.GameObjects.Text;
  private exitButton?: Phaser.GameObjects.Text;
  private profileButton?: Phaser.GameObjects.Text;
  private refreshButton?: Phaser.GameObjects.Text;
  private groundTile?: Phaser.GameObjects.TileSprite;
  private gridGraphics?: Phaser.GameObjects.Graphics;
  private bonusSprites: Phaser.GameObjects.Image[] = [];
  private bonusGraphicsFallback?: Phaser.GameObjects.Graphics;
  private taskSprites: Phaser.GameObjects.Image[] = [];
  private taskGraphicsFallback?: Phaser.GameObjects.Graphics;
  private balanceLabel?: Phaser.GameObjects.Text;
  private coinLabel?: Phaser.GameObjects.Text;
  private sessionCoins: number = 0;
  private otherPlayers: Map<string, { sprite: Phaser.GameObjects.Sprite; label: Phaser.GameObjects.Text }> = new Map();
  private keys!: {
    up: Phaser.Input.Keyboard.Key;
    down: Phaser.Input.Keyboard.Key;
    left: Phaser.Input.Keyboard.Key;
    right: Phaser.Input.Keyboard.Key;
    space: Phaser.Input.Keyboard.Key;
    e: Phaser.Input.Keyboard.Key;
  };
  private taskModalCooldown: number = 0;
  private readonly TASK_MODAL_COOLDOWN_MS = 500;
  private moveCooldown: number = 0;
  private readonly MOVE_COOLDOWN_TIME = 50;
  private hasExited: boolean = false;
  private currentDirection: 'idle' | 'up' | 'down' | 'left' | 'right' = 'idle';
  private tasksState: MapTaskItem[] = [];
  private bonusesState: BonusItem[] = [];
  private inventoryState: Record<string, number> = {};
  private inventoryButton?: Phaser.GameObjects.Text;
  private sessionId: string = '';
  private lobbyText?: Phaser.GameObjects.Text;
  private gameEndsAt: number = 0;
  private gameEndedText?: Phaser.GameObjects.Text;
  private gameInProgress: boolean = false;
  private currentScore: number = 0;
  private playerUsernames: Record<string, string> = {};

  constructor() {
    super('GameScene');
  }

  preload() {
    // Загружаем спрайт-лист mario.png
    // Структура: 4 строки по 4 кадра
    // Строка 0: движение вниз (кадры 0-3), кадр 0 - idle
    // Строка 1: движение влево (кадры 4-7)
    // Строка 2: движение вправо (кадры 8-11)
    // Строка 3: движение вверх (кадры 12-15)
    
    // Предполагаем размер одного кадра 32x32 (можно изменить при необходимости)
    // Если размер другой, измените frameWidth и frameHeight
    const frameWidth = 56;
    const frameHeight = 56;
    
    // Путь к спрайту (если файл в frontend/assets/, используйте '/assets/mario.png')
    // Если файл в public/assets/, используйте 'assets/mario.png'
    this.load.spritesheet('mario', '/assets/mario2.png', {
      frameWidth: frameWidth,
      frameHeight: frameHeight
    });

    // Бонусы: отдельные спрайты — тип 1 яблоко, 2 апельсин, 3 ананас
    this.load.image('apple', '/assets/apple.png');
    this.load.image('orange', '/assets/orange.png');
    this.load.image('pineapple', '/assets/pineapple.png');

    // Задания по уровням сложности
    this.load.image('task_1', '/assets/task_1.png');
    this.load.image('task_2', '/assets/task_2.png');
    this.load.image('task_3', '/assets/task_3.png');

    // Создаем текстуру земли для фона
    this.createGroundTexture();
  }

  private createGroundTexture() {
    // Размер одного шага персонажа (примерно равен размеру кадра)
    const stepSize = 56;
    // Размер тайла земли = 1 шаг персонажа (уменьшено в 10 раз)
    const tileSize = stepSize; // 56x56 пикселей
    
    // Создаем графику для текстуры земли (используем make для создания вне сцены)
    const graphics = this.make.graphics({ add: false });
    
    // Рисуем текстуру земли с зерном рельефа
    // Базовый цвет земли
    graphics.fillStyle(0x8B7355); // Коричневый цвет земли
    graphics.fillRect(0, 0, tileSize, tileSize);
    
    // Добавляем детали рельефа - случайные точки и линии для текстуры (уменьшено пропорционально)
    graphics.fillStyle(0x6B5B45); // Темнее
    for (let i = 0; i < 20; i++) {
      const x = Math.random() * tileSize;
      const y = Math.random() * tileSize;
      const size = Math.random() * 2 + 0.5;
      graphics.fillCircle(x, y, size);
    }
    
    // Добавляем более светлые участки
    graphics.fillStyle(0x9B8365);
    for (let i = 0; i < 15; i++) {
      const x = Math.random() * tileSize;
      const y = Math.random() * tileSize;
      const size = Math.random() * 1.5 + 0.3;
      graphics.fillCircle(x, y, size);
    }
    
    // Добавляем линии рельефа (трещины/неровности)
    graphics.lineStyle(1, 0x5A4A35, 0.3);
    for (let i = 0; i < 5; i++) {
      const x1 = Math.random() * tileSize;
      const y1 = Math.random() * tileSize;
      const x2 = x1 + (Math.random() - 0.5) * 15;
      const y2 = y1 + (Math.random() - 0.5) * 15;
      graphics.moveTo(x1, y1);
      graphics.lineTo(x2, y2);
    }
    
    // Добавляем небольшие камни/детали
    graphics.fillStyle(0x4A3A25);
    for (let i = 0; i < 8; i++) {
      const x = Math.random() * tileSize;
      const y = Math.random() * tileSize;
      const size = Math.random() * 2 + 1;
      graphics.fillCircle(x, y, size);
    }
    
    // Создаем текстуру из графики
    graphics.generateTexture('ground', tileSize, tileSize);
    graphics.destroy();
  }

  private createGrid() {
    // Размер одного тайла (1 шаг персонажа - уменьшено в 10 раз)
    const stepSize = 56;
    const tileSize = stepSize; // 56x56 пикселей
    
    const gameWidth = this.cameras.main.width;
    const gameHeight = this.cameras.main.height;
    
    // Создаем графику для сетки
    this.gridGraphics = this.add.graphics();
    this.gridGraphics.setDepth(0); // Сетка поверх земли, но под персонажами
    
    // Цвет линий сетки (темно-коричневый с прозрачностью)
    this.gridGraphics.lineStyle(1, 0x5A4A35, 0.5);
    
    // Вертикальные линии (границы между тайлами по X)
    for (let x = 0; x <= gameWidth; x += tileSize) {
      this.gridGraphics.moveTo(x, 0);
      this.gridGraphics.lineTo(x, gameHeight);
    }
    
    // Горизонтальные линии (границы между тайлами по Y)
    for (let y = 0; y <= gameHeight; y += tileSize) {
      this.gridGraphics.moveTo(0, y);
      this.gridGraphics.lineTo(gameWidth, y);
    }
    
    // Рисуем линии
    this.gridGraphics.strokePath();
  }

  create() {
    // Получаем токен и данные пользователя из глобальной переменной
    const token = (window as any).gameToken;
    this.playerId = (window as any).gameUserId;
    this.username = (window as any).gameUsername || 'Player';
    this.sessionId = (window as any).gameSessionId || '';

    if (!token || !this.playerId || !this.sessionId) {
      console.error('Токен, user_id или session_id не найдены');
      return;
    }

    // Проверяем, что текстура загружена перед созданием анимаций
    if (!this.textures.exists('mario')) {
      console.error('Текстура mario не загружена!');
      return;
    }

    // Создаем анимации из спрайт-листа
    this.createMarioAnimations();

    // Создаем фоновую тайловую карту земли
    const gameWidth = this.cameras.main.width;
    const gameHeight = this.cameras.main.height;
    this.groundTile = this.add.tileSprite(0, 0, gameWidth, gameHeight, 'ground');
    this.groundTile.setOrigin(0, 0);
    this.groundTile.setDepth(-1); // Фон должен быть за всем остальным

    // Создаем сетку с границами между тайлами
    this.createGrid();

    // Создаем свой анимированный спрайт
    this.mySprite = this.add.sprite(100, 100, 'mario');
    this.mySprite.setOrigin(0.5, 0.5);
    
    // Проверяем, что анимация существует перед воспроизведением
    if (this.anims.exists('mario_idle')) {
      this.mySprite.play('mario_idle');
    } else {
      console.warn('Анимация mario_idle не найдена');
    }
    this.myLabel = this.add.text(100, 80, this.username, {
      fontSize: '12px',
      color: '#00ff00',
      align: 'center'
    }).setOrigin(0.5);

    // Настройка клавиатуры
    this.keys = {
      up: this.input.keyboard!.addKey(Phaser.Input.Keyboard.KeyCodes.W),
      down: this.input.keyboard!.addKey(Phaser.Input.Keyboard.KeyCodes.S),
      left: this.input.keyboard!.addKey(Phaser.Input.Keyboard.KeyCodes.A),
      right: this.input.keyboard!.addKey(Phaser.Input.Keyboard.KeyCodes.D),
      space: this.input.keyboard!.addKey(Phaser.Input.Keyboard.KeyCodes.SPACE),
      e: this.input.keyboard!.addKey(Phaser.Input.Keyboard.KeyCodes.E),
    };


    // Баланс очков и монет
    this.balanceLabel = this.add.text(10, 32, 'Очки: 0', {
      fontSize: '16px',
      color: '#ffffff',
    });
    this.balanceLabel.setDepth(10);
    this.coinLabel = this.add.text(10, 54, 'Монеты: 0', {
      fontSize: '16px',
      color: '#ffcc00',
    });
    this.coinLabel.setDepth(10);

    const wsUrl = `ws://localhost:8000/ws/game?token=${encodeURIComponent(token)}&session_id=${encodeURIComponent(this.sessionId)}`;
    this.ws = new WebSocket(wsUrl);

    this.lobbyText = this.add.text(400, 300, 'Ожидание игроков...', {
      fontSize: '20px',
      color: '#ffffff',
      align: 'center',
    }).setOrigin(0.5).setDepth(100);
    this.gameEndedText = this.add.text(400, 300, '', {
      fontSize: '24px',
      color: '#00ff00',
      align: 'center',
    }).setOrigin(0.5).setDepth(101).setVisible(false);

    this.ws.onopen = () => {
      console.log('WebSocket подключен');
    };

    this.ws.onerror = (error) => {
      console.error('WebSocket ошибка:', error);
    };

    this.ws.onclose = () => {
      console.log('WebSocket отключен');
    };

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data) as {
          type: string;
          players?: PlayersState;
          bonuses?: BonusItem[];
          tasks?: MapTaskItem[];
          scores?: Record<string, number>;
          ends_at?: number;
          items?: Record<string, number>;
          task_completed?: { reward_points?: number; reward_item_1?: number; reward_item_2?: number };
          task_error?: string;
          detail?: string;
          players_count?: number;
          player_usernames?: Record<string, string>;
          countdown_seconds?: number;
          registration_closed?: boolean;
          winner_id?: string;
          winner_username?: string;
          duration_seconds?: number;
        };
        if (msg.type === 'lobby') {
          if (msg.player_usernames) this.playerUsernames = { ...this.playerUsernames, ...msg.player_usernames };
          const count = (msg.players && msg.players.length) || 0;
          const names = msg.player_usernames || this.playerUsernames;
          const namesStr = msg.players?.map((id: string) => names[id] || id).join(', ') || '—';
          const sec = msg.countdown_seconds ?? 0;
          const text = sec > 0
            ? `Игроки (${count}/4): ${namesStr}\nСтарт через ${sec} сек...`
            : `Ожидание игроков (${count}/4). Нужен ещё один для старта.\n${namesStr}`;
          if (this.lobbyText) this.lobbyText.setText(text);
        } else if (msg.type === 'game_started') {
          this.gameInProgress = true;
          this.gameEndsAt = (msg.ends_at ?? 0) * 1000;
          if (this.lobbyText) this.lobbyText.setVisible(false);
        } else if (msg.type === 'state') {
          if (msg.ends_at) {
            this.gameInProgress = true;
            this.gameEndsAt = msg.ends_at * 1000;
            if (this.lobbyText) this.lobbyText.setVisible(false);
          }
          this.syncPlayers(msg.players!);
          this.bonusesState = Array.isArray(msg.bonuses) ? msg.bonuses : [];
          this.syncBonuses(this.bonusesState);
          if (msg.tasks) this.syncTasks(msg.tasks);
          if (msg.scores && this.balanceLabel) {
            this.currentScore = msg.scores[this.playerId] ?? 0;
            this.balanceLabel.setText(`Очки: ${this.currentScore}`);
          }
          const coins = (msg as any).coins;
          if (coins && this.playerId in coins) {
            this.sessionCoins = Number(coins[this.playerId]) || 0;
            if (this.coinLabel) this.coinLabel.setText(`Монеты: ${this.sessionCoins}`);
          }
          const ingredients = (msg as any).ingredients;
          if (ingredients && this.playerId in ingredients) {
            const inv = ingredients[this.playerId] as Record<number, number>;
            this.inventoryState = { '1': inv[1] ?? 0, '2': inv[2] ?? 0, '3': inv[3] ?? 0 };
          }
          this.updateGameInventory();
        } else if (msg.type === 'game_ended') {
          this.gameInProgress = false;
          if (this.lobbyText) this.lobbyText.setVisible(false);
          const winner = msg.winner_username ?? '—';
          const scores = msg.scores || {};
          const lines = Object.entries(scores).map(([id, pts]) => `${this.playerUsernames[id] || id}: ${pts}`).join('\n');
          if (this.gameEndedText) {
            this.gameEndedText.setText(`Игра окончена!\nПобедитель: ${winner}\n\n${lines}`);
            this.gameEndedText.setVisible(true);
          }
        } else if (msg.type === 'inventory') {
          this.inventoryState = msg.items || {};
          const coins = (msg as any).coins;
          if (typeof coins === 'number') {
            this.sessionCoins = coins;
            if (this.coinLabel) this.coinLabel.setText(`Монеты: ${this.sessionCoins}`);
          }
          this.updateGameInventory();
          if (msg.task_completed) {
            const closeTaskModal = (window as any).closeTaskModal;
            if (typeof closeTaskModal === 'function') closeTaskModal(msg.task_completed);
          }
          if (msg.task_error != null || msg.detail != null) {
            const errEl = document.getElementById('task-error-text');
            if (errEl) {
              errEl.textContent = (msg as any).task_error || (msg as any).detail || 'Ошибка';
              errEl.style.display = 'block';
            }
          }
        } else if (msg.type === 'task_error') {
          const errEl = document.getElementById('task-error-text');
          if (errEl) {
            errEl.textContent = (msg as any).detail || 'Ошибка';
            errEl.style.display = 'block';
          }
        }
      } catch (error) {
        console.error('Ошибка парсинга сообщения:', error);
      }
    };

    (window as any).gameSubmitTask = () => this.submitTask();
    (window as any).gameBuyIngredient = (itemType: number) => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        try {
          this.ws.send(JSON.stringify({ type: 'buy_ingredient', item_type: itemType }));
        } catch (e) {
          console.error('Ошибка покупки ингредиента:', e);
        }
      }
    };
    (window as any).__currentTask = null;

    // Инструкции на экране
    this.add.text(10, 10, 'WASD - движение, Пробел - бонус или задание', {
      fontSize: '16px',
      color: '#ffffff'
    });

    // Кнопка "Инвентарь"
    this.inventoryButton = this.add.text(400, 10, 'Инвентарь', {
      fontSize: '16px',
      color: '#ffffff',
      backgroundColor: '#444444',
      padding: { left: 10, right: 10, top: 6, bottom: 6 }
    })
      .setOrigin(0, 0)
      .setInteractive({ useHandCursor: true });
    this.inventoryButton.on('pointerover', () => this.inventoryButton?.setStyle({ backgroundColor: '#666666' }));
    this.inventoryButton.on('pointerout', () => this.inventoryButton?.setStyle({ backgroundColor: '#444444' }));
    this.inventoryButton.on('pointerdown', () => {
      const goToInventory = (window as any).goToInventory;
      if (typeof goToInventory === 'function') goToInventory();
    });

    // Кнопка "Обновить" — ручная синхронизация игроков и бонусов
    this.refreshButton = this.add.text(520, 10, 'Обновить', {
      fontSize: '16px',
      color: '#ffffff',
      backgroundColor: '#444444',
      padding: { left: 10, right: 10, top: 6, bottom: 6 }
    })
      .setOrigin(0, 0)
      .setInteractive({ useHandCursor: true });
    this.refreshButton.on('pointerover', () => {
      this.refreshButton?.setStyle({ backgroundColor: '#666666' });
    });
    this.refreshButton.on('pointerout', () => {
      this.refreshButton?.setStyle({ backgroundColor: '#444444' });
    });
    this.refreshButton.on('pointerdown', () => {
      try {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
          this.ws.send(JSON.stringify({ type: 'sync' }));
        }
      } catch (e) {
        console.error('Ошибка синхронизации:', e);
      }
    });

    // Кнопка "Профиль"
    this.profileButton = this.add.text(620, 10, 'Профиль', {
      fontSize: '16px',
      color: '#ffffff',
      backgroundColor: '#444444',
      padding: { left: 10, right: 10, top: 6, bottom: 6 }
    })
      .setOrigin(0, 0)
      .setInteractive({ useHandCursor: true });
    this.profileButton.on('pointerover', () => {
      this.profileButton?.setStyle({ backgroundColor: '#666666' });
    });
    this.profileButton.on('pointerout', () => {
      this.profileButton?.setStyle({ backgroundColor: '#444444' });
    });
    this.profileButton.on('pointerdown', () => {
      const goToProfile = (window as any).goToProfile;
      if (typeof goToProfile === 'function') goToProfile();
    });

    // Кнопка "Выйти" (в сцене)
    this.exitButton = this.add.text(790, 10, 'Выйти', {
      fontSize: '16px',
      color: '#ffffff',
      backgroundColor: '#444444',
      padding: { left: 10, right: 10, top: 6, bottom: 6 }
    })
      .setOrigin(1, 0)
      .setInteractive({ useHandCursor: true });

    this.exitButton.on('pointerover', () => {
      this.exitButton?.setStyle({ backgroundColor: '#666666' });
    });
    this.exitButton.on('pointerout', () => {
      this.exitButton?.setStyle({ backgroundColor: '#444444' });
    });
    this.exitButton.on('pointerdown', () => {
      void this.exitGame();
    });
  }

  update(time: number, delta: number) {
    if (this.gameInProgress && this.gameEndsAt > 0 && this.balanceLabel) {
      const remaining = Math.max(0, Math.ceil((this.gameEndsAt - Date.now()) / 1000));
      const m = Math.floor(remaining / 60);
      const s = remaining % 60;
      const timeStr = `${m}:${s.toString().padStart(2, '0')}`;
      this.balanceLabel.setText(`Очки: ${this.currentScore} | ${timeStr}`);
    }
    if (!this.gameInProgress || !this.ws || this.ws.readyState !== WebSocket.OPEN || !this.mySprite) return;

    // Проверка кулдауна для отправки движения
    if (this.moveCooldown > 0) {
      this.moveCooldown -= delta;
      return;
    }

    const speed = 3;
    let dx = 0;
    let dy = 0;
    let newDirection: 'idle' | 'up' | 'down' | 'left' | 'right' = 'idle';

    if (this.keys.left.isDown) {
      dx -= speed;
      newDirection = 'left';
    }
    if (this.keys.right.isDown) {
      dx += speed;
      newDirection = 'right';
    }
    if (this.keys.up.isDown) {
      dy -= speed;
      newDirection = 'up';
    }
    if (this.keys.down.isDown) {
      dy += speed;
      newDirection = 'down';
    }

    // Обновляем анимацию в зависимости от направления
    if (newDirection !== this.currentDirection && this.mySprite) {
      this.currentDirection = newDirection;
      const animKey = `mario_${newDirection === 'idle' ? 'idle' : `walk_${newDirection}`}`;
      
      // Проверяем, что анимация существует и не воспроизводится уже
      if (this.mySprite.anims.currentAnim?.key !== animKey) {
        try {
          // Проверяем существование анимации
          if (this.anims.exists(animKey)) {
            this.mySprite.play(animKey);
          } else {
            console.warn(`Анимация ${animKey} не найдена, используем idle`);
            this.mySprite.play('mario_idle');
          }
        } catch (error) {
          console.error(`Ошибка воспроизведения анимации ${animKey}:`, error);
          // Fallback на idle при ошибке
          if (this.anims.exists('mario_idle')) {
            this.mySprite.play('mario_idle');
          }
        }
      }
    }

    if (dx !== 0 || dy !== 0) {
      try {
        this.ws.send(JSON.stringify({ type: 'move', dx, dy }));
        this.moveCooldown = this.MOVE_COOLDOWN_TIME;
      } catch (error) {
        console.error('Ошибка отправки движения:', error);
      }
    }

    // Пробел — либо задание (окно), либо сбор бонуса
    if (this.taskModalCooldown > 0) this.taskModalCooldown -= delta;
    if (this.keys.space.isDown && this.taskModalCooldown <= 0 && this.mySprite) {
      const tile_x = Math.floor(this.mySprite.x / TILE_SIZE);
      const tile_y = Math.floor(this.mySprite.y / TILE_SIZE);
      const taskAtTile = this.tasksState.find((t) => t.tile_x === tile_x && t.tile_y === tile_y);
      const bonusAtTile = this.bonusesState.some((b) => b.tile_x === tile_x && b.tile_y === tile_y);
      if (taskAtTile) {
        this.taskModalCooldown = this.TASK_MODAL_COOLDOWN_MS;
        const openTaskModal = (window as any).openTaskModal;
        if (typeof openTaskModal === 'function') openTaskModal({ ...taskAtTile, tile_x, tile_y });
      } else if (bonusAtTile) {
        this.taskModalCooldown = this.TASK_MODAL_COOLDOWN_MS;
        try {
          this.ws!.send(JSON.stringify({ type: 'collect_bonus' }));
        } catch (error) {
          console.error('Ошибка отправки collect_bonus:', error);
        }
      }
    }

    if (dx === 0 && dy === 0 && this.currentDirection !== 'idle' && this.mySprite) {
      // Если не двигаемся, переключаемся на idle
      this.currentDirection = 'idle';
      if (this.mySprite.anims.currentAnim?.key !== 'mario_idle') {
        try {
          if (this.anims.exists('mario_idle')) {
            this.mySprite.play('mario_idle');
          }
        } catch (error) {
          console.error('Ошибка переключения на idle:', error);
        }
      }
    }
  }

  submitTask(): void {
    const task = (window as any).__currentTask as (MapTaskItem & { tile_x: number; tile_y: number }) | null;
    const transferred = (window as any).getTransferredForTask as (() => Record<number, number>) | undefined;
    if (!task || !this.ws || this.ws.readyState !== WebSocket.OPEN) return;
    const t = typeof transferred === 'function' ? transferred() : null;
    const type1 = t ? (t[1] ?? 0) : task.required_type_1;
    const type2 = t ? (t[2] ?? 0) : task.required_type_2;
    const type3 = t ? (t[3] ?? 0) : task.required_type_3;
    document.getElementById('task-error-text')?.setAttribute('style', 'display: none');
    try {
      this.ws.send(JSON.stringify({
        type: 'submit_task',
        tile_x: task.tile_x,
        tile_y: task.tile_y,
        type_1: type1,
        type_2: type2,
        type_3: type3,
      }));
    } catch (e) {
      console.error('Ошибка сдачи задания:', e);
    }
  }

  private updateGameInventory() {
    (window as any).gameInventory = {
      coins: this.sessionCoins,
      items: { ...this.inventoryState },
    };
    window.dispatchEvent(new CustomEvent('game-inventory-updated'));
  }

  private static readonly BONUS_TEXTURE_KEYS: Record<number, string> = {
    1: 'apple',
    2: 'orange',
    3: 'pineapple',
  };

  private syncBonuses(bonuses: BonusItem[]) {
    this.bonusSprites.forEach((s) => s.destroy());
    this.bonusSprites = [];
    const radius = 20;
    const hasAnyBonusImage =
      this.textures.exists('apple') || this.textures.exists('orange') || this.textures.exists('pineapple');
    if (hasAnyBonusImage && this.bonusGraphicsFallback) {
      this.bonusGraphicsFallback.clear();
    }
    if (!hasAnyBonusImage) {
      if (!this.bonusGraphicsFallback) {
        this.bonusGraphicsFallback = this.add.graphics();
        this.bonusGraphicsFallback.setDepth(0.5);
      }
      this.bonusGraphicsFallback.clear();
    }
    const list = Array.isArray(bonuses) ? bonuses : [];
    list.forEach((b) => {
      const tileX = Number(b.tile_x ?? 0);
      const tileY = Number(b.tile_y ?? 0);
      const x = tileX * TILE_SIZE + TILE_SIZE / 2;
      const y = tileY * TILE_SIZE + TILE_SIZE / 2;
      const type = Math.max(1, Math.min(3, Number(b.type) || 1));
      const textureKey = GameScene.BONUS_TEXTURE_KEYS[type];
      if (hasAnyBonusImage && textureKey && this.textures.exists(textureKey)) {
        const img = this.add.image(x, y, textureKey);
        img.setDisplaySize(TILE_SIZE * 0.8, TILE_SIZE * 0.8);
        img.setDepth(0.5);
        this.bonusSprites.push(img);
      } else {
        const color = type === 1 ? 0xcc0000 : type === 2 ? 0xff8800 : 0xffff00;
        this.bonusGraphicsFallback!.fillStyle(color, 0.9);
        this.bonusGraphicsFallback!.fillCircle(x, y, radius);
        this.bonusGraphicsFallback!.lineStyle(2, 0x000000, 0.3);
        this.bonusGraphicsFallback!.strokeCircle(x, y, radius);
      }
    });
  }

  private static readonly TASK_TEXTURE_KEYS: Record<number, string> = { 1: 'task_1', 2: 'task_2', 3: 'task_3' };

  private syncTasks(tasks: MapTaskItem[]) {
    this.tasksState = tasks;
    this.taskSprites.forEach((s) => s.destroy());
    this.taskSprites = [];
    if (this.taskGraphicsFallback) this.taskGraphicsFallback.clear();
    const levelKey = (l: number) => GameScene.TASK_TEXTURE_KEYS[Math.max(1, Math.min(3, l))] || 'task_1';
    const size = TILE_SIZE * 0.8;
    tasks.forEach((t) => {
      const x = t.tile_x * TILE_SIZE + TILE_SIZE / 2;
      const y = t.tile_y * TILE_SIZE + TILE_SIZE / 2;
      const key = levelKey(t.level ?? 1);
      if (this.textures.exists(key)) {
        const img = this.add.image(x, y, key);
        img.setDisplaySize(size, size);
        img.setDepth(0.5);
        this.taskSprites.push(img);
      } else {
        if (!this.taskGraphicsFallback) {
          this.taskGraphicsFallback = this.add.graphics();
          this.taskGraphicsFallback.setDepth(0.5);
        }
        this.taskGraphicsFallback.fillStyle(0x0088ff, 0.9);
        this.taskGraphicsFallback.fillRect(x - 10, y - 10, 20, 20);
      }
    });
  }

  private syncPlayers(players: PlayersState) {
    // Обновляем свой спрайт
    const me = players[this.playerId];
    if (me && this.mySprite && this.myLabel) {
      this.mySprite.setPosition(me.x, me.y);
      this.myLabel.setPosition(me.x, me.y - 25);
    }

    // Обновляем/создаем чужие спрайты (используем тот же спрайт-лист)
    Object.entries(players).forEach(([id, pos]) => {
      if (id === this.playerId) return;

      let playerData = this.otherPlayers.get(id);
      if (!playerData) {
        const sprite = this.add.sprite(pos.x, pos.y, 'mario');
        sprite.setOrigin(0.5, 0.5);
        sprite.setTint(0xff0000); // Красный оттенок для других игроков
        sprite.play('mario_idle');
        const label = this.add.text(pos.x, pos.y - 25, pos.username || 'Player', {
          fontSize: '12px',
          color: '#ff0000',
          align: 'center'
        }).setOrigin(0.5);
        this.otherPlayers.set(id, { sprite, label });
      } else {
        playerData.sprite.setPosition(pos.x, pos.y);
        playerData.label.setPosition(pos.x, pos.y - 25);
        if (pos.username) {
          playerData.label.setText(pos.username);
        }
        // Проигрываем idle анимацию для других игроков
        if (playerData.sprite.anims.currentAnim?.key !== 'mario_idle') {
          playerData.sprite.play('mario_idle');
        }
      }
    });

    // Удаляем ушедших игроков
    for (const [id, playerData] of this.otherPlayers.entries()) {
      if (!players[id]) {
        playerData.sprite.destroy();
        playerData.label.destroy();
        this.otherPlayers.delete(id);
      }
    }
  }

  private createMarioAnimations() {
    // Создаем анимации из спрайт-листа
    // Структура: 4 строки по 4 кадра
    // Строка 0 (кадры 0-3): движение вниз, кадр 0 - idle
    // Строка 1 (кадры 4-7): движение влево
    // Строка 2 (кадры 8-11): движение вправо
    // Строка 3 (кадры 12-15): движение вверх

    // Проверяем количество кадров в текстуре для отладки
    const texture = this.textures.get('mario');
    if (texture) {
      const frameCount = texture.frameTotal;
      console.log(`Текстура mario загружена. Всего кадров: ${frameCount}`);
      if (frameCount < 16) {
        console.warn(`Ожидалось 16 кадров, но найдено только ${frameCount}. Проверьте размер кадра (frameWidth=${60}, frameHeight=${60})`);
      }
    }

    try {
      // Idle - первый кадр первой строки (кадр 0)
      this.anims.create({
        key: 'mario_idle',
        frames: [{ key: 'mario', frame: 0 }],
        frameRate: 2,
        repeat: -1
      });

      // Движение вниз - все 4 кадра первой строки (кадры 0-3)
      this.anims.create({
        key: 'mario_walk_down',
        frames: this.anims.generateFrameNumbers('mario', { start: 0, end: 3 }),
        frameRate: 10,
        repeat: -1
      });

      // Движение влево - все 4 кадра второй строки (кадры 4-7)
      this.anims.create({
        key: 'mario_walk_left',
        frames: this.anims.generateFrameNumbers('mario', { start: 4, end: 7 }),
        frameRate: 10,
        repeat: -1
      });

      // Движение вправо - все 4 кадра третьей строки (кадры 8-11)
      this.anims.create({
        key: 'mario_walk_right',
        frames: this.anims.generateFrameNumbers('mario', { start: 8, end: 11 }),
        frameRate: 10,
        repeat: -1
      });

      // Движение вверх - все 4 кадра четвертой строки (кадры 12-15)
      // Проверяем, что кадры существуют перед созданием анимации
      try {
        const upFrames = this.anims.generateFrameNumbers('mario', { start: 12, end: 15 });
        if (upFrames && upFrames.length > 0) {
          // Проверяем, что все кадры валидны
          const validFrames = upFrames.filter((frame: any) => {
            const texture = this.textures.get('mario');
            return texture && frame.frame !== undefined;
          });
          
          if (validFrames.length === upFrames.length) {
            this.anims.create({
              key: 'mario_walk_up',
              frames: upFrames,
              frameRate: 10,
              repeat: -1
            });
            console.log('Анимация mario_walk_up создана успешно с кадрами:', upFrames.map((f: any) => f.frame));
          } else {
            console.warn('Некоторые кадры для движения вверх невалидны. Создаем fallback.');
            this.anims.create({
              key: 'mario_walk_up',
              frames: [{ key: 'mario', frame: 0 }],
              frameRate: 10,
              repeat: -1
            });
          }
        } else {
          console.error('Не удалось создать кадры для движения вверх. Проверьте размер кадра и структуру спрайт-листа.');
          // Создаем fallback анимацию с одним кадром
          this.anims.create({
            key: 'mario_walk_up',
            frames: [{ key: 'mario', frame: 0 }],
            frameRate: 10,
            repeat: -1
          });
        }
      } catch (error) {
        console.error('Ошибка создания анимации движения вверх:', error);
        // Fallback на idle кадр
        this.anims.create({
          key: 'mario_walk_up',
          frames: [{ key: 'mario', frame: 0 }],
          frameRate: 10,
          repeat: -1
        });
      }
    } catch (error) {
      console.error('Ошибка создания анимаций:', error);
    }
  }

  private async exitGame() {
    if (this.hasExited) return;
    this.hasExited = true;

    const x = this.mySprite?.x ?? 100;
    const y = this.mySprite?.y ?? 100;

    // Сообщаем серверу, чтобы он сохранил позицию
    try {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: 'exit', x, y }));
      }
    } catch {
      // ignore
    }

    // Закрываем соединение
    try {
      this.ws?.close();
    } catch {
      // ignore
    }

    // Возвращаемся на экран логина
    const exitToLogin = (window as any).exitToLogin;
    if (typeof exitToLogin === 'function') {
      exitToLogin();
    } else {
      // fallback
      this.game.destroy(true);
    }
  }
}

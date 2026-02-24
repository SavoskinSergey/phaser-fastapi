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
  type: number; // 100 | 200 | 500
  tile_x: number;
  tile_y: number;
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
  private bonusGraphics?: Phaser.GameObjects.Graphics;
  private balanceLabel?: Phaser.GameObjects.Text;
  private otherPlayers: Map<string, { sprite: Phaser.GameObjects.Sprite; label: Phaser.GameObjects.Text }> = new Map();
  private keys!: {
    up: Phaser.Input.Keyboard.Key;
    down: Phaser.Input.Keyboard.Key;
    left: Phaser.Input.Keyboard.Key;
    right: Phaser.Input.Keyboard.Key;
    space: Phaser.Input.Keyboard.Key;
  };
  private moveCooldown: number = 0;
  private readonly MOVE_COOLDOWN_TIME = 50; // мс между отправками движения
  private collectBonusCooldown: number = 0;
  private readonly COLLECT_BONUS_COOLDOWN = 400; // мс между нажатиями пробела
  private hasExited: boolean = false;
  private currentDirection: 'idle' | 'up' | 'down' | 'left' | 'right' = 'idle';

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

    if (!token || !this.playerId) {
      console.error('Токен или user_id не найдены');
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
    };

    // Графика для бонусов (кружки на карте)
    this.bonusGraphics = this.add.graphics();
    this.bonusGraphics.setDepth(0.5); // Между землёй и персонажами

    // Баланс очков игрока
    this.balanceLabel = this.add.text(10, 32, 'Очки: 0', {
      fontSize: '16px',
      color: '#ffffff',
    });
    this.balanceLabel.setDepth(10);

    // Подключение к WebSocket с токеном
    const wsUrl = `ws://localhost:8000/ws/game?token=${encodeURIComponent(token)}`;
    this.ws = new WebSocket(wsUrl);

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
        const msg = JSON.parse(event.data) as { type: string; players: PlayersState; bonuses?: BonusItem[] };
        if (msg.type === 'state') {
          this.syncPlayers(msg.players);
          if (msg.bonuses) {
            this.syncBonuses(msg.bonuses);
          }
          const me = msg.players[this.playerId];
          if (me?.balance_points !== undefined && this.balanceLabel) {
            this.balanceLabel.setText(`Очки: ${me.balance_points}`);
          }
        }
      } catch (error) {
        console.error('Ошибка парсинга сообщения:', error);
      }
    };

    // Инструкции на экране
    this.add.text(10, 10, 'WASD - движение, Пробел - собрать бонус', {
      fontSize: '16px',
      color: '#ffffff'
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
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN || !this.mySprite) return;

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

    // Сбор бонуса по пробелу (в той же клетке, что и бонус)
    if (this.collectBonusCooldown > 0) {
      this.collectBonusCooldown -= delta;
    }
    if (this.keys.space.isDown && this.collectBonusCooldown <= 0) {
      try {
        this.ws.send(JSON.stringify({ type: 'collect_bonus' }));
        this.collectBonusCooldown = this.COLLECT_BONUS_COOLDOWN;
      } catch (error) {
        console.error('Ошибка отправки collect_bonus:', error);
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

  private syncBonuses(bonuses: BonusItem[]) {
    if (!this.bonusGraphics) return;
    this.bonusGraphics.clear();
    const radius = 18;
    bonuses.forEach((b) => {
      const x = b.tile_x * TILE_SIZE + TILE_SIZE / 2;
      const y = b.tile_y * TILE_SIZE + TILE_SIZE / 2;
      const color = b.type === 100 ? 0x00ff00 : b.type === 200 ? 0xffff00 : 0xff0000; // зелёный, жёлтый, красный
      this.bonusGraphics!.fillStyle(color, 0.9);
      this.bonusGraphics!.fillCircle(x, y, radius);
      this.bonusGraphics!.lineStyle(2, 0x000000, 0.3);
      this.bonusGraphics!.strokeCircle(x, y, radius);
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

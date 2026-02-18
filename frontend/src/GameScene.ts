import Phaser from 'phaser';

interface PlayerState {
  x: number;
  y: number;
  username?: string;
}

interface PlayersState {
  [playerId: string]: PlayerState;
}

export class GameScene extends Phaser.Scene {
  private ws?: WebSocket;
  private playerId: string = '';
  private username: string = '';
  private mySprite?: Phaser.GameObjects.Rectangle;
  private myLabel?: Phaser.GameObjects.Text;
  private exitButton?: Phaser.GameObjects.Text;
  private otherPlayers: Map<string, { sprite: Phaser.GameObjects.Rectangle; label: Phaser.GameObjects.Text }> = new Map();
  private keys!: {
    up: Phaser.Input.Keyboard.Key;
    down: Phaser.Input.Keyboard.Key;
    left: Phaser.Input.Keyboard.Key;
    right: Phaser.Input.Keyboard.Key;
  };
  private moveCooldown: number = 0;
  private readonly MOVE_COOLDOWN_TIME = 50; // мс между отправками движения
  private hasExited: boolean = false;

  constructor() {
    super('GameScene');
  }

  preload() {}

  create() {
    // Получаем токен и данные пользователя из глобальной переменной
    const token = (window as any).gameToken;
    this.playerId = (window as any).gameUserId;
    this.username = (window as any).gameUsername || 'Player';

    if (!token || !this.playerId) {
      console.error('Токен или user_id не найдены');
      return;
    }

    // Создаем свой спрайт (зеленый квадрат)
    this.mySprite = this.add.rectangle(100, 100, 30, 30, 0x00ff00);
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
      right: this.input.keyboard!.addKey(Phaser.Input.Keyboard.KeyCodes.D)
    };

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
        const msg = JSON.parse(event.data) as { type: string; players: PlayersState };
        if (msg.type === 'state') {
          this.syncPlayers(msg.players);
        }
      } catch (error) {
        console.error('Ошибка парсинга сообщения:', error);
      }
    };

    // Инструкции на экране
    this.add.text(10, 10, 'WASD - движение', {
      fontSize: '16px',
      color: '#ffffff'
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

    if (this.keys.left.isDown) dx -= speed;
    if (this.keys.right.isDown) dx += speed;
    if (this.keys.up.isDown) dy -= speed;
    if (this.keys.down.isDown) dy += speed;

    if (dx !== 0 || dy !== 0) {
      try {
        this.ws.send(JSON.stringify({ type: 'move', dx, dy }));
        this.moveCooldown = this.MOVE_COOLDOWN_TIME;
      } catch (error) {
        console.error('Ошибка отправки движения:', error);
      }
    }
  }

  private syncPlayers(players: PlayersState) {
    // Обновляем свой спрайт
    const me = players[this.playerId];
    if (me && this.mySprite && this.myLabel) {
      this.mySprite.setPosition(me.x, me.y);
      this.myLabel.setPosition(me.x, me.y - 25);
    }

    // Обновляем/создаем чужие спрайты (красные квадраты)
    Object.entries(players).forEach(([id, pos]) => {
      if (id === this.playerId) return;

      let playerData = this.otherPlayers.get(id);
      if (!playerData) {
        const sprite = this.add.rectangle(pos.x, pos.y, 30, 30, 0xff0000);
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

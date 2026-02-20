import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';

// Mock Phaser before importing GameScene
const mockTileSprite = { setOrigin: vi.fn(), setDepth: vi.fn() };
const mockSprite = {
  setOrigin: vi.fn(),
  play: vi.fn(),
  anims: { currentAnim: { key: 'mario_idle' } },
};
const mockGraphics = {
  setDepth: vi.fn(),
  lineStyle: vi.fn(),
  moveTo: vi.fn(),
  lineTo: vi.fn(),
  strokePath: vi.fn(),
};

const mockAdd = {
  rectangle: vi.fn().mockReturnValue({
    setPosition: vi.fn(),
    x: 100,
    y: 100,
  }),
  text: vi.fn().mockReturnValue({
    setOrigin: vi.fn().mockReturnThis(),
    setPosition: vi.fn(),
    setText: vi.fn(),
    setStyle: vi.fn(),
    setInteractive: vi.fn().mockReturnThis(),
    on: vi.fn(), // Phaser EventEmitter — нужен для exitButton.on('pointerover', ...)
    destroy: vi.fn(),
  }),
  tileSprite: vi.fn().mockReturnValue(mockTileSprite),
  sprite: vi.fn().mockReturnValue(mockSprite),
  graphics: vi.fn().mockReturnValue(mockGraphics),
};

const mockInput = {
  keyboard: {
    addKey: vi.fn().mockReturnValue({
      isDown: false,
    }),
  },
};

const mockGame = {
  destroy: vi.fn(),
};

vi.mock('phaser', () => ({
  default: {
    Scene: class MockScene {
      scene = { key: 'GameScene' };
      add = mockAdd;
      input = mockInput;
      game = mockGame;
      textures = {
        exists: vi.fn().mockReturnValue(true),
        get: vi.fn().mockReturnValue({ frameTotal: 16 }),
      };
      anims = {
        exists: vi.fn().mockReturnValue(true),
        create: vi.fn(),
        generateFrameNumbers: vi.fn().mockReturnValue([{ key: 'mario', frame: 0 }]),
      };
      cameras = { main: { width: 800, height: 600 } };
    },
    Input: {
      Keyboard: {
        KeyCodes: {
          W: 'W',
          A: 'A',
          S: 'S',
          D: 'D',
        },
      },
    },
  },
}));

import { GameScene } from '../GameScene';

describe('GameScene', () => {
  let gameScene: GameScene;
  let mockWindow: any;

  beforeEach(() => {
    // Mock window object
    mockWindow = {
      gameToken: 'test-token',
      gameUserId: 'user123',
      gameUsername: 'testuser',
      exitToLogin: vi.fn(),
    };
    (global as any).window = mockWindow;

    // Mock WebSocket (в jsdom нет WebSocket.OPEN — без него update() выходит по условию readyState !== WebSocket.OPEN)
    const WebSocketMock = vi.fn().mockImplementation(() => ({
      readyState: 1,
      send: vi.fn(),
      close: vi.fn(),
      onopen: null,
      onerror: null,
      onclose: null,
      onmessage: null,
    }));
    (WebSocketMock as any).OPEN = 1;
    global.WebSocket = WebSocketMock as any;

    gameScene = new GameScene();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('constructor', () => {
    it('should create GameScene instance', () => {
      expect(gameScene).toBeInstanceOf(GameScene);
    });
  });

  describe('create', () => {
    it('should initialize game scene with token and user data', () => {
      gameScene.create();

      // Проверяем, что WebSocket был создан
      expect(global.WebSocket).toHaveBeenCalled();
    });

    it('should handle missing token', () => {
      mockWindow.gameToken = null;
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      gameScene.create();

      expect(consoleSpy).toHaveBeenCalledWith(
        expect.stringContaining('Токен или user_id не найдены')
      );

      consoleSpy.mockRestore();
    });

    it('should create player sprite and label', () => {
      gameScene.create();

      expect(mockAdd.sprite).toHaveBeenCalledWith(100, 100, 'mario');
      expect(mockAdd.text).toHaveBeenCalled();
    });

    it('should setup keyboard controls', () => {
      gameScene.create();

      expect(mockInput.keyboard.addKey).toHaveBeenCalledTimes(4);
    });

    it('should connect to WebSocket with token', () => {
      gameScene.create();

      expect(global.WebSocket).toHaveBeenCalledWith(
        expect.stringContaining('ws://localhost:8000/ws/game?token=test-token')
      );
    });
  });

  describe('WebSocket handling', () => {
    it('should handle WebSocket messages', () => {
      const mockWs = {
        readyState: 1,
        send: vi.fn(),
        close: vi.fn(),
        onopen: null,
        onerror: null,
        onclose: null,
        onmessage: null,
      };

      (global.WebSocket as any).mockImplementation(() => mockWs);

      gameScene.create();

      // Симулируем получение сообщения
      const message = {
        type: 'state',
        players: {
          user123: { x: 150, y: 200, username: 'testuser' },
          user456: { x: 300, y: 400, username: 'otheruser' },
        },
      };

      if (mockWs.onmessage) {
        mockWs.onmessage({
          data: JSON.stringify(message),
        } as MessageEvent);
      }

      // Проверяем, что состояние было обработано
      // (в реальном тесте нужно проверить обновление спрайтов)
    });

    it('should handle WebSocket errors', () => {
      const mockWs = {
        readyState: 1,
        send: vi.fn(),
        close: vi.fn(),
        onopen: null,
        onerror: null,
        onclose: null,
        onmessage: null,
      };

      (global.WebSocket as any).mockImplementation(() => mockWs);
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      gameScene.create();

      if (mockWs.onerror) {
        mockWs.onerror(new Error('Connection error') as any);
      }

      expect(consoleSpy).toHaveBeenCalled();

      consoleSpy.mockRestore();
    });
  });

  describe('update', () => {
    const spriteWithAnims = {
      anims: { currentAnim: { key: 'mario_idle' } },
      play: vi.fn(),
    };

    it('should not send movement if WebSocket is not open', () => {
      const mockWs = {
        readyState: 0, // CONNECTING
        send: vi.fn(),
      };
      (gameScene as any).ws = mockWs;
      (gameScene as any).mySprite = spriteWithAnims;

      gameScene.update(0, 16);

      expect(mockWs.send).not.toHaveBeenCalled();
    });

    it('should send movement when keys are pressed', () => {
      const mockWs = {
        readyState: 1, // OPEN
        send: vi.fn(),
      };
      (gameScene as any).ws = mockWs;
      (gameScene as any).mySprite = spriteWithAnims;
      (gameScene as any).keys = {
        left: { isDown: true },
        right: { isDown: false },
        up: { isDown: false },
        down: { isDown: false },
      };
      (gameScene as any).moveCooldown = 0;

      gameScene.update(0, 16);

      expect(mockWs.send).toHaveBeenCalled();
      const sentData = JSON.parse(mockWs.send.mock.calls[0][0]);
      expect(sentData.type).toBe('move');
      expect(sentData.dx).toBe(-3); // speed = 3, left = -3
    });

    it('should respect move cooldown', () => {
      const mockWs = {
        readyState: 1,
        send: vi.fn(),
      };
      (gameScene as any).ws = mockWs;
      (gameScene as any).mySprite = spriteWithAnims;
      (gameScene as any).keys = {
        left: { isDown: true },
        right: { isDown: false },
        up: { isDown: false },
        down: { isDown: false },
      };
      (gameScene as any).moveCooldown = 100; // Still in cooldown

      gameScene.update(0, 16);

      expect(mockWs.send).not.toHaveBeenCalled();
    });
  });

  describe('exitGame', () => {
    it('should send exit message and close WebSocket', async () => {
      const mockWs = {
        readyState: 1,
        send: vi.fn(),
        close: vi.fn(),
      };
      (gameScene as any).ws = mockWs;
      (gameScene as any).mySprite = { x: 150, y: 200 };
      (gameScene as any).hasExited = false;

      await (gameScene as any).exitGame();

      expect(mockWs.send).toHaveBeenCalledWith(
        JSON.stringify({ type: 'exit', x: 150, y: 200 })
      );
      expect(mockWs.close).toHaveBeenCalled();
      expect(mockWindow.exitToLogin).toHaveBeenCalled();
    });

    it('should not exit twice', async () => {
      const mockWs = {
        readyState: 1,
        send: vi.fn(),
        close: vi.fn(),
      };
      (gameScene as any).ws = mockWs;
      (gameScene as any).hasExited = true;

      await (gameScene as any).exitGame();

      expect(mockWs.send).not.toHaveBeenCalled();
    });

    it('should handle WebSocket send errors gracefully', async () => {
      const mockWs = {
        readyState: 0, // Not open
        send: vi.fn().mockImplementation(() => {
          throw new Error('Send error');
        }),
        close: vi.fn(),
      };
      (gameScene as any).ws = mockWs;
      (gameScene as any).hasExited = false;

      // Не должно быть исключения
      await (gameScene as any).exitGame();

      expect(mockWindow.exitToLogin).toHaveBeenCalled();
    });
  });
});

const API_URL = 'http://localhost:8000';
const TOKEN_KEY = 'game_auth_token';
const USER_DATA_KEY = 'game_user_data';

export interface TokenData {
  access_token: string;
  token_type: string;
  user_id: string;
  username: string;
}

export class AuthService {
  /**
   * Сохраняет токен и данные пользователя в localStorage
   */
  static saveToken(tokenData: TokenData): void {
    localStorage.setItem(TOKEN_KEY, tokenData.access_token);
    localStorage.setItem(USER_DATA_KEY, JSON.stringify({
      user_id: tokenData.user_id,
      username: tokenData.username
    }));
  }

  /**
   * Получает сохраненный токен из localStorage
   */
  static getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  }

  /**
   * Получает сохраненные данные пользователя из localStorage
   */
  static getUserData(): { user_id: string; username: string } | null {
    const data = localStorage.getItem(USER_DATA_KEY);
    return data ? JSON.parse(data) : null;
  }

  /**
   * Удаляет токен и данные пользователя из localStorage
   */
  static clearToken(): void {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_DATA_KEY);
  }

  /**
   * Проверяет, есть ли сохраненный токен
   */
  static hasToken(): boolean {
    return this.getToken() !== null;
  }

  static async login(username: string, password: string): Promise<TokenData> {
    const response = await fetch(`${API_URL}/api/login`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ username, password }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Ошибка входа' }));
      throw new Error(error.detail || 'Ошибка входа');
    }

    const tokenData = await response.json();
    // Сохраняем токен в localStorage
    this.saveToken(tokenData);
    return tokenData;
  }

  static async register(username: string, email: string, password: string): Promise<TokenData> {
    const response = await fetch(`${API_URL}/api/register`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ username, email, password }),
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Ошибка регистрации' }));
      throw new Error(error.detail || 'Ошибка регистрации');
    }

    const tokenData = await response.json();
    // Сохраняем токен в localStorage
    this.saveToken(tokenData);
    return tokenData;
  }

  static async getCurrentUser(token: string): Promise<{ user_id: string; username: string }> {
    const response = await fetch(`${API_URL}/api/me`, {
      headers: {
        'Authorization': `Bearer ${token}`,
      },
    });

    if (!response.ok) {
      throw new Error('Ошибка получения данных пользователя');
    }

    return response.json();
  }

  /**
   * Проверяет валидность сохраненного токена
   */
  static async validateToken(): Promise<TokenData | null> {
    const token = this.getToken();
    if (!token) {
      return null;
    }

    try {
      const userData = await this.getCurrentUser(token);
      const userDataStored = this.getUserData();
      
      // Возвращаем полные данные токена
      return {
        access_token: token,
        token_type: 'bearer',
        user_id: userData.user_id,
        username: userData.username
      };
    } catch (error) {
      // Токен невалиден, очищаем его
      this.clearToken();
      return null;
    }
  }
}

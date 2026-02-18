const API_URL = 'http://localhost:8000';

export interface TokenData {
  access_token: string;
  token_type: string;
  user_id: string;
  username: string;
}

export class AuthService {
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

    return response.json();
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

    return response.json();
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
}

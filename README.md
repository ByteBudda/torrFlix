# 🎬 TorrFLIX - Personal Streaming Hub

Легкий и быстрый медиа-комбайн для стриминга торрентов напрямую в браузер. Интеграция с TMDB для поиска и Jackett для поиска раздач.

## 🚀 Быстрый старт (Docker)

1. **Клонируйте репозиторий:**
   ```
   git clone https://github.com/ByteBudda/torrFlix.git
   cd torrFlix
`
###

 * Настройте конфиг:
   Создайте файл config.json в корневой папке:

```
{
  "tmdb_api_key": "ВАШ_TMDB_KEY",
  "jackett_url": "http://IP_СЕРВЕРА:9117",
  "jackett_api_key": "ВАШ_JACKETT_KEY"
}
```
 * Запустите контейнер:
 * ```
   docker compose up -d --build
`
 * Доступ:
   * Главная: http://localhost:8800
   * Админка: http://localhost:8800/admin (логин: admin, пароль: pass777)
   * 
🛠 Технологии
 * Backend: Python (Flask)
 * Frontend: HTML5, CSS3 (Atmospheric Dark UI)
 * Infrastructure: Docker & Docker Compose
 * API: TMDB API, Jackett API
🛡 Безопасность
Файл config.json и кэш изображений добавлены в .gitignore. Никогда не пушьте свои API-ключи в публичный доступ!
Developed by ByteBudda



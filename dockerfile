# Используем легкий образ Python
FROM python:3.10-slim

# Указываем рабочую директорию
WORKDIR /app

# Копируем зависимости и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальные файлы проекта
COPY . .

# Создаем папку для кэша изображений
RUN mkdir -p cache_img

# Открываем порт 8800
EXPOSE 8800

# Запускаем сервер
CMD ["python", "server.py"]
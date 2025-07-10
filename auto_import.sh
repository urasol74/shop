#!/bin/bash

cd /home/ubuntu/shop

WATCHED_FILE="/home/ubuntu/bot_art/data/Новый.xlsx"
TARGET_FILE="/home/ubuntu/shop/data/der.xlsx"
LOG_FILE="/home/ubuntu/shop/auto_import.log"

# Явно активируем виртуальное окружение
source /home/ubuntu/shop/venv/bin/activate

while true; do
    inotifywait -e close_write,move,create "$WATCHED_FILE"
    cp "$WATCHED_FILE" "$TARGET_FILE"

    {
        echo "--------------------------------------"
        echo "Дата: $(date)"
        echo "Каталог: $(pwd)"
        echo "Пользователь: $(whoami)"
        echo "Путь к python: $(which python)"
        echo "Импорт начат..."
    } >> "$LOG_FILE"

    # Запускаем скрипт
    python /home/ubuntu/shop/import_excel_to_db.py >> "$LOG_FILE" 2>&1
    echo "$(date): Импорт завершён с кодом $?" >> "$LOG_FILE"
done

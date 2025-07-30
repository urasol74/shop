#!/bin/bash

WATCHED_DIR="/home/ubuntu/bot_art/instance"
WATCHED_FILE="base.db"
LOG_FILE="/home/ubuntu/shop/auto_import.log"

cd /home/ubuntu/shop
source /home/ubuntu/shop/venv/bin/activate

while true; do
    inotifywait -e close_write,move,create,moved_to "$WATCHED_DIR"
    if [ -f "$WATCHED_DIR/$WATCHED_FILE" ]; then
    {
        echo "--------------------------------------"
        echo "Дата: $(date)"
        echo "Каталог: $(pwd)"
        echo "Пользователь: $(whoami)"
        echo "Путь к python: $(which python)"
        echo "Импорт из БД начат..."
    } >> "$LOG_FILE"
    python /home/ubuntu/shop/import_db_to_db_incremental.py >> "$LOG_FILE" 2>&1
    echo "$(date): Импорт завершён с кодом $?" >> "$LOG_FILE"
    fi
done

#!/usr/bin/env python3
"""
Тестовый скрипт для проверки системы отслеживания пользователей
"""

import json
import os
from datetime import datetime

def test_user_system():
    """Тестирует систему отслеживания пользователей"""
    
    print("Тестирование системы отслеживания пользователей...")
    
    # Проверяем файлы
    data_file = 'data/client.json'
    static_file = 'static/client.json'
    
    print(f"\n1. Проверка файлов:")
    print(f"   data/client.json: {'существует' if os.path.exists(data_file) else 'НЕ существует'}")
    print(f"   static/client.json: {'существует' if os.path.exists(static_file) else 'НЕ существует'}")
    
    # Загружаем данные
    if os.path.exists(data_file):
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"\n2. Данные из {data_file}:")
        print(f"   Всего пользователей: {len(data.get('users', {}))}")
        print(f"   Последнее обновление: {data.get('last_updated', 'Не указано')}")
        
        if 'migration_info' in data:
            print(f"   Информация о миграции: {data['migration_info']}")
        
        # Анализируем пользователей
        for user_id, user in data.get('users', {}).items():
            print(f"\n   Пользователь {user_id}:")
            print(f"     Имя: {user.get('first_name', '')} {user.get('last_name', '')}")
            print(f"     Username: @{user.get('username', 'не указан')}")
            print(f"     Статус: {user.get('status', 'не указан')}")
            print(f"     Посещения: {user.get('visits', 0)}")
            print(f"     Действий: {len(user.get('actions', []))}")
            print(f"     Сессий: {len(user.get('login_history', []))}")
            print(f"     Дата регистрации: {user.get('created_at', 'не указана')}")
            
            # Показываем последние действия
            actions = user.get('actions', [])
            if actions:
                print(f"     Последние действия:")
                for action in actions[-3:]:  # Последние 3 действия
                    print(f"       {action['action']} - {action['timestamp']}")
    
    # Проверяем структуру директорий
    print(f"\n3. Структура директорий:")
    data_dir = 'data'
    if os.path.exists(data_dir):
        files = os.listdir(data_dir)
        print(f"   data/: {', '.join(files)}")
    
    static_dir = 'static'
    if os.path.exists(static_dir):
        files = os.listdir(static_dir)
        json_files = [f for f in files if f.endswith('.json')]
        print(f"   static/ (JSON файлы): {', '.join(json_files)}")
    
    print(f"\nТестирование завершено!")

if __name__ == '__main__':
    test_user_system()

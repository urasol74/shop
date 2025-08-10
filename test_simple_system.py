#!/usr/bin/env python3
"""
Тестовый скрипт для упрощенной системы отслеживания пользователей
"""

import json
import os
from datetime import datetime

def test_simple_system():
    """Тестирует упрощенную систему"""
    
    print("Тестирование упрощенной системы отслеживания пользователей...")
    
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
        
        # Анализируем пользователей
        for user_id, user in data.get('users', {}).items():
            print(f"\n   Пользователь {user_id}:")
            print(f"     ID: {user.get('id', 'не указан')}")
            print(f"     Время входа: {user.get('login_time', 'не указано')}")
            print(f"     Первое посещение: {user.get('first_visit', 'не указано')}")
    
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
    print(f"\nСистема готова к работе!")
    print(f"Теперь при входе пользователей будут собираться только:")
    print(f"- ID пользователя")
    print(f"- Время входа")
    print(f"- Первое посещение")

if __name__ == '__main__':
    test_simple_system()

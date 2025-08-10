#!/usr/bin/env python3
"""
Тестовый скрипт для проверки отслеживания повторных посещений
"""

import json
import os
from datetime import datetime

def test_visit_history():
    """Тестирует новую функциональность отслеживания посещений"""
    
    print("Тестирование отслеживания повторных посещений...")
    
    # Проверяем файлы
    data_file = 'data/client.json'
    
    print(f"\n1. Проверка файла {data_file}:")
    if os.path.exists(data_file):
        print(f"   Файл существует")
        
        # Загружаем данные
        with open(data_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"\n2. Текущие данные:")
        print(f"   Всего пользователей: {len(data.get('users', {}))}")
        print(f"   Последнее обновление: {data.get('last_updated', 'Не указано')}")
        
        # Анализируем пользователей
        for user_id, user in data.get('users', {}).items():
            print(f"\n   Пользователь {user_id}:")
            print(f"     ID: {user.get('id', 'не указан')}")
            print(f"     Время входа: {user.get('login_time', 'не указано')}")
            print(f"     Первое посещение: {user.get('first_visit', 'не указано')}")
            
            # Проверяем историю посещений
            visit_history = user.get('visit_history', [])
            print(f"     История посещений: {len(visit_history)} записей")
            
            if visit_history:
                print(f"     Детали посещений:")
                for i, visit_time in enumerate(visit_history):
                    visit_type = "Первое посещение" if i == 0 else "Повторное посещение"
                    print(f"       {i+1}. {visit_type}: {visit_time}")
            else:
                print(f"     История посещений: не найдена")
        
        print(f"\n3. Проверка структуры данных:")
        print(f"   Поля для каждого пользователя:")
        if data.get('users'):
            sample_user = next(iter(data['users'].values()))
            for field, value in sample_user.items():
                if field == 'visit_history':
                    print(f"     {field}: список из {len(value)} элементов")
                else:
                    print(f"     {field}: {value}")
        
    else:
        print(f"   Файл НЕ существует")
    
    print(f"\nТестирование завершено!")
    print(f"\nТеперь система отслеживает:")
    print(f"- ID пользователя")
    print(f"- Время входа (последнее)")
    print(f"- Первое посещение")
    print(f"- Повторные посещения (история последних 10)")

if __name__ == '__main__':
    test_visit_history()

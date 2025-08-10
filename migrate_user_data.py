#!/usr/bin/env python3
"""
Скрипт для миграции и объединения данных пользователей
Объединяет данные из static/client.json и data/client.json
"""

import json
import os
import shutil
from datetime import datetime

def load_json_file(file_path):
    """Загружает JSON файл"""
    try:
        if os.path.exists(file_path):
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"Ошибка загрузки {file_path}: {e}")
    return None

def save_json_file(file_path, data):
    """Сохраняет JSON файл"""
    try:
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"Ошибка сохранения {file_path}: {e}")
        return False

def migrate_user_data():
    """Основная функция миграции"""
    
    # Пути к файлам
    static_file = 'static/client.json'
    data_file = 'data/client.json'
    backup_file = 'static/client.json.backup'
    
    print("Начинаем миграцию данных пользователей...")
    
    # Загружаем данные из static файла
    static_data = load_json_file(static_file)
    if not static_data:
        print("Не удалось загрузить данные из static/client.json")
        return False
    
    # Загружаем данные из data файла
    data_data = load_json_file(data_file)
    if not data_data:
        print("Не удалось загрузить данные из data/client.json")
        return False
    
    print(f"Найдено пользователей в static: {len(static_data.get('users', {}))}")
    print(f"Найдено пользователей в data: {len(data_data.get('users', {}))}")
    
    # Создаем backup static файла
    if os.path.exists(static_file):
        shutil.copyfile(static_file, backup_file)
        print(f"Создан backup: {backup_file}")
    
    # Объединяем данные
    merged_users = {}
    
    # Сначала добавляем пользователей из data файла
    for user_id, user_data in data_data.get('users', {}).items():
        merged_users[user_id] = user_data.copy()
        # Инициализируем недостающие поля
        if 'login_history' not in merged_users[user_id]:
            merged_users[user_id]['login_history'] = []
        if 'created_at' not in merged_users[user_id]:
            merged_users[user_id]['created_at'] = user_data.get('login_time', datetime.now().isoformat())
    
    # Затем добавляем/объединяем пользователей из static файла
    for user_id, user_data in static_data.get('users', {}).items():
        if user_id not in merged_users:
            # Новый пользователь
            merged_users[user_id] = user_data.copy()
            if 'login_history' not in merged_users[user_id]:
                merged_users[user_id]['login_history'] = []
            if 'created_at' not in merged_users[user_id]:
                merged_users[user_id]['created_at'] = user_data.get('login_time', datetime.now().isoformat())
        else:
            # Пользователь уже существует, объединяем действия
            existing_user = merged_users[user_id]
            if 'actions' in user_data and 'actions' in existing_user:
                # Создаем множество существующих действий для проверки дублирования
                existing_actions = {(a['action'], a['timestamp']) for a in existing_user['actions']}
                
                # Добавляем новые действия
                for action in user_data['actions']:
                    if (action['action'], action['timestamp']) not in existing_actions:
                        existing_user['actions'].append(action)
                
                # Сортируем по времени и ограничиваем количество
                existing_user['actions'].sort(key=lambda x: x['timestamp'])
                if len(existing_user['actions']) > 200:
                    existing_user['actions'] = existing_user['actions'][-200:]
    
    # Создаем объединенные данные
    merged_data = {
        'users': merged_users,
        'last_updated': datetime.now().isoformat(),
        'migration_info': {
            'migrated_at': datetime.now().isoformat(),
            'static_users_count': len(static_data.get('users', {})),
            'data_users_count': len(data_data.get('users', {})),
            'merged_users_count': len(merged_users)
        }
    }
    
    # Сохраняем объединенные данные в data файл
    if save_json_file(data_file, merged_data):
        print(f"Объединенные данные сохранены в {data_file}")
        print(f"Всего пользователей после объединения: {len(merged_users)}")
        
        # Показываем статистику
        total_actions = sum(len(user.get('actions', [])) for user in merged_users.values())
        total_sessions = sum(len(user.get('login_history', [])) for user in merged_users.values())
        print(f"Всего действий: {total_actions}")
        print(f"Всего сессий: {total_sessions}")
        
        return True
    else:
        print("Ошибка сохранения объединенных данных")
        return False

if __name__ == '__main__':
    success = migrate_user_data()
    if success:
        print("Миграция завершена успешно!")
    else:
        print("Миграция завершена с ошибками!")

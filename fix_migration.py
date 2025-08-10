#!/usr/bin/env python3
"""
Скрипт для исправления миграции данных пользователей
"""

import json
import os
import shutil
from datetime import datetime

def fix_migration():
    """Исправляет миграцию данных пользователей"""
    
    print("Исправление миграции данных пользователей...")
    
    # Пути к файлам
    legacy_file = 'static/client.json'
    main_file = 'data/client.json'
    backup_file = 'static/client.json.backup'
    
    print(f"\n1. Проверка файлов:")
    print(f"   Legacy файл: {'существует' if os.path.exists(legacy_file) else 'НЕ существует'}")
    print(f"   Основной файл: {'существует' if os.path.exists(main_file) else 'НЕ существует'}")
    print(f"   Резервная копия: {'существует' if os.path.exists(backup_file) else 'НЕ существует'}")
    
    # Загружаем данные из основного файла
    main_data = {"users": {}, "last_updated": datetime.now().isoformat()}
    if os.path.exists(main_file):
        try:
            with open(main_file, 'r', encoding='utf-8') as f:
                main_data = json.load(f)
            print(f"\n2. Данные из основного файла:")
            print(f"   Пользователей: {len(main_data.get('users', {}))}")
        except Exception as e:
            print(f"   Ошибка загрузки основного файла: {e}")
    
    # Загружаем данные из legacy файла
    legacy_data = {"users": {}, "last_updated": datetime.now().isoformat()}
    if os.path.exists(legacy_file):
        try:
            with open(legacy_file, 'r', encoding='utf-8') as f:
                legacy_data = json.load(f)
            print(f"\n3. Данные из legacy файла:")
            print(f"   Пользователей: {len(legacy_data.get('users', {}))}")
        except Exception as e:
            print(f"   Ошибка загрузки legacy файла: {e}")
    
    # Объединяем данные
    print(f"\n4. Объединение данных...")
    merged_users = main_data.get('users', {}).copy()
    
    for user_id, legacy_user in legacy_data.get('users', {}).items():
        if user_id not in merged_users:
            # Новый пользователь из legacy - конвертируем в новый формат
            print(f"   Добавляем пользователя {user_id} из legacy")
            merged_users[user_id] = {
                'id': int(user_id),
                'login_time': legacy_user.get('login_time', datetime.now().isoformat()),
                'first_visit': legacy_user.get('first_visit', legacy_user.get('login_time', datetime.now().isoformat())),
                'visit_history': [legacy_user.get('login_time', datetime.now().isoformat())]
            }
        else:
            # Пользователь уже существует - обновляем историю
            print(f"   Обновляем историю пользователя {user_id}")
            current_user = merged_users[user_id]
            
            # Инициализируем историю если её нет
            if 'visit_history' not in current_user:
                current_user['visit_history'] = []
            
            # Добавляем legacy время входа в историю
            legacy_time = legacy_user.get('login_time')
            if legacy_time and legacy_time not in current_user['visit_history']:
                current_user['visit_history'].append(legacy_time)
                current_user['visit_history'].sort()  # Сортируем по времени
    
    # Создаем объединенные данные
    merged_data = {
        "users": merged_users,
        "last_updated": datetime.now().isoformat()
    }
    
    print(f"\n5. Результат объединения:")
    print(f"   Всего пользователей: {len(merged_users)}")
    
    for user_id, user in merged_users.items():
        print(f"   Пользователь {user_id}:")
        print(f"     ID: {user.get('id')}")
        print(f"     Время входа: {user.get('login_time')}")
        print(f"     Первое посещение: {user.get('first_visit')}")
        print(f"     История посещений: {len(user.get('visit_history', []))} записей")
    
    # Сохраняем объединенные данные
    print(f"\n6. Сохранение объединенных данных...")
    try:
        # Создаем backup основного файла
        if os.path.exists(main_file):
            backup_main = main_file + '.backup.' + datetime.now().strftime('%Y%m%d_%H%M%S')
            shutil.copyfile(main_file, backup_main)
            print(f"   Создан backup основного файла: {backup_main}")
        
        # Сохраняем объединенные данные
        with open(main_file, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, ensure_ascii=False, indent=2)
        print(f"   Объединенные данные сохранены в {main_file}")
        
        # Перемещаем legacy файл в архив
        if os.path.exists(legacy_file):
            archive_file = legacy_file + '.archived.' + datetime.now().strftime('%Y%m%d_%H%M%S')
            shutil.move(legacy_file, archive_file)
            print(f"   Legacy файл перемещен в архив: {archive_file}")
        
        print(f"\n✅ Миграция успешно исправлена!")
        
    except Exception as e:
        print(f"   ❌ Ошибка сохранения: {e}")
        return False
    
    return True

if __name__ == '__main__':
    fix_migration()

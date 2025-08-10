#!/usr/bin/env python3
import sqlite3
import os

DB_PATH = "/home/ubuntu/shop/instance/db-der.db"

def show_db_structure():
    """Показывает структуру базы данных"""
    if not os.path.exists(DB_PATH):
        print(f"База данных {DB_PATH} не найдена!")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    print("=== СТРУКТУРА БАЗЫ ДАННЫХ ===")
    
    # Получаем список всех таблиц
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cur.fetchall()
    
    for table in tables:
        table_name = table[0]
        print(f"\n📋 ТАБЛИЦА: {table_name}")
        
        # Получаем информацию о колонках
        cur.execute(f"PRAGMA table_info({table_name})")
        columns = cur.fetchall()
        
        print("   Колонки:")
        for col in columns:
            col_id, col_name, col_type, not_null, default_val, pk = col
            pk_mark = " 🔑" if pk else ""
            not_null_mark = " NOT NULL" if not_null else ""
            default_mark = f" DEFAULT {default_val}" if default_val else ""
            print(f"     {col_id}. {col_name} ({col_type}){not_null_mark}{default_mark}{pk_mark}")
        
        # Получаем количество записей
        cur.execute(f"SELECT COUNT(*) FROM {table_name}")
        count = cur.fetchone()[0]
        print(f"   Записей: {count}")
        
        # Показываем примеры данных
        cur.execute(f"SELECT * FROM {table_name} LIMIT 3")
        examples = cur.fetchall()
        if examples:
            print("   Примеры данных:")
            for i, row in enumerate(examples, 1):
                print(f"     {i}. {row}")
    
    # Показываем внешние ключи
    print(f"\n🔗 ВНЕШНИЕ КЛЮЧИ:")
    cur.execute("PRAGMA foreign_key_list(products)")
    fk_products = cur.fetchall()
    for fk in fk_products:
        print(f"   products.category_id → categories.id")
    
    cur.execute("PRAGMA foreign_key_list(variants)")
    fk_variants = cur.fetchall()
    for fk in fk_variants:
        print(f"   variants.product_id → products.id")
    
    # Показываем индексы
    print(f"\n📊 ИНДЕКСЫ:")
    cur.execute("SELECT name, sql FROM sqlite_master WHERE type='index'")
    indexes = cur.fetchall()
    for idx in indexes:
        print(f"   {idx[0]}: {idx[1]}")
    
    # Показываем статистику по полу
    print(f"\n👥 СТАТИСТИКА ПО ПОЛУ:")
    cur.execute("""
        SELECT gender, COUNT(*) as count
        FROM products
        WHERE gender != ''
        GROUP BY gender
        ORDER BY count DESC
    """)
    gender_stats = cur.fetchall()
    for gender, count in gender_stats:
        print(f"   - {gender}: {count} продуктов")
    
    conn.close()

if __name__ == "__main__":
    show_db_structure() 
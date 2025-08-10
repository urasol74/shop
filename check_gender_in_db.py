#!/usr/bin/env python3
import sqlite3
import os

DB_PATH = "/home/ubuntu/shop/instance/db-der.db"

def check_gender_in_db():
    """Проверяем данные о поле в базе данных"""
    if not os.path.exists(DB_PATH):
        print(f"База данных {DB_PATH} не найдена!")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    print("=== ДАННЫЕ О ПОЛЕ В БАЗЕ ДАННЫХ ===")
    
    # Статистика по полу
    cur.execute("""
        SELECT gender, COUNT(*) as count
        FROM products
        WHERE gender != ''
        GROUP BY gender
        ORDER BY count DESC
    """)
    gender_stats = cur.fetchall()
    
    print(f"\n📊 СТАТИСТИКА ПО ПОЛУ:")
    for gender, count in gender_stats:
        print(f"  - {gender}: {count} продуктов")
    
    # Примеры продуктов с данными о поле
    print(f"\n📋 ПРИМЕРЫ ПРОДУКТОВ С ДАННЫМИ О ПОЛЕ:")
    cur.execute("""
        SELECT p.article, p.name, c.name as category, p.brand, p.season, p.gender
        FROM products p
        JOIN categories c ON p.category_id = c.id
        WHERE p.gender != ''
        LIMIT 15
    """)
    products = cur.fetchall()
    for prod in products:
        print(f"  - {prod[0]}: {prod[1]} ({prod[2]}) - {prod[3]} {prod[4]} - {prod[5]}")
    
    # Общая статистика
    cur.execute("SELECT COUNT(*) FROM products WHERE gender != ''")
    with_gender = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM products WHERE gender = ''")
    without_gender = cur.fetchone()[0]
    
    print(f"\n📈 ОБЩАЯ СТАТИСТИКА:")
    print(f"  - Продуктов с данными о поле: {with_gender}")
    print(f"  - Продуктов без данных о поле: {without_gender}")
    print(f"  - Всего продуктов: {with_gender + without_gender}")
    
    conn.close()

if __name__ == "__main__":
    check_gender_in_db() 
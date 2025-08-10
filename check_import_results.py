#!/usr/bin/env python3
import sqlite3
import os

DB_PATH = "/home/ubuntu/shop/instance/db-der.db"

def check_results():
    """Проверяем результаты импорта"""
    if not os.path.exists(DB_PATH):
        print(f"База данных {DB_PATH} не найдена!")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    
    print("=== РЕЗУЛЬТАТЫ ИМПОРТА ===")
    
    # Статистика
    cur.execute("SELECT COUNT(*) FROM categories")
    categories_count = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM products")
    products_count = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM variants")
    variants_count = cur.fetchone()[0]
    
    print(f"Категорий: {categories_count}")
    print(f"Продуктов: {products_count}")
    print(f"Вариантов: {variants_count}")
    
    # Примеры категорий
    print(f"\n=== ПРИМЕРЫ КАТЕГОРИЙ ===")
    cur.execute("SELECT name FROM categories LIMIT 10")
    categories = cur.fetchall()
    for cat in categories:
        print(f"  - {cat[0]}")
    
    # Примеры продуктов
    print(f"\n=== ПРИМЕРЫ ПРОДУКТОВ ===")
    cur.execute("""
        SELECT p.article, p.name, c.name as category, p.brand, p.season
        FROM products p
        JOIN categories c ON p.category_id = c.id
        LIMIT 10
    """)
    products = cur.fetchall()
    for prod in products:
        print(f"  - {prod[0]}: {prod[1]} ({prod[2]}) - {prod[3]} {prod[4]}")
    
    # Примеры вариантов
    print(f"\n=== ПРИМЕРЫ ВАРИАНТОВ ===")
    cur.execute("""
        SELECT p.article, v.size, v.color, COUNT(*) as count
        FROM variants v
        JOIN products p ON v.product_id = p.id
        GROUP BY p.article, v.size, v.color
        LIMIT 10
    """)
    variants = cur.fetchall()
    for var in variants:
        print(f"  - {var[0]} | Размер: {var[1]} | Цвет: {var[2]} | Количество: {var[3]}")
    
    # Статистика по размерам
    print(f"\n=== СТАТИСТИКА ПО РАЗМЕРАМ ===")
    cur.execute("""
        SELECT size, COUNT(*) as count
        FROM variants
        WHERE size != ''
        GROUP BY size
        ORDER BY count DESC
        LIMIT 10
    """)
    sizes = cur.fetchall()
    for size in sizes:
        print(f"  - {size[0]}: {size[1]} вариантов")
    
    conn.close()

if __name__ == "__main__":
    check_results() 
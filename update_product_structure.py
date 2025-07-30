from app import app, db, Product
import sqlite3

def update_product_structure():
    """
    Обновляет структуру товаров:
    - Заполняет поле cat основной категорией
    - Восстанавливает полное название в поле name
    """
    with app.app_context():
        try:
            # Подключаемся напрямую к SQLite для обновления
            conn = sqlite3.connect('instance/shop.db')
            cursor = conn.cursor()
            
            # Получаем все товары
            cursor.execute("SELECT id, art, name, size, color FROM product")
            products = cursor.fetchall()
            
            print(f"Найдено {len(products)} товаров для обновления")
            
            updated_count = 0
            
            for product_id, art, name, size, color in products:
                # Восстанавливаем полное название
                full_name = f"{name}, Размер: {size}, Цвет: {color}" if size and color else name
                
                # Обновляем запись
                cursor.execute("""
                    UPDATE product 
                    SET name = ?, cat = ? 
                    WHERE id = ?
                """, (full_name, name, product_id))
                
                updated_count += 1
            
            # Коммитим изменения
            conn.commit()
            conn.close()
            
            print(f"Обновление завершено!")
            print(f"Обновлено товаров: {updated_count}")
            
            # Показываем примеры
            print("\nПримеры обновленных товаров:")
            sample_products = Product.query.limit(5).all()
            for product in sample_products:
                print(f"- {product.art}: name='{product.name}', cat='{product.cat}'")
            
        except Exception as e:
            print(f"Ошибка при обновлении структуры: {e}")

if __name__ == "__main__":
    update_product_structure() 
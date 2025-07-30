from app import app, db, Product

def fix_product_names():
    """
    Исправляет названия товаров в базе данных:
    - Оставляет в поле name только основную категорию (до первой запятой)
    - Размер и цвет остаются в отдельных полях size и color
    """
    with app.app_context():
        try:
            # Получаем все товары
            products = Product.query.all()
            
            print(f"Найдено {len(products)} товаров для исправления")
            
            updated_count = 0
            
            for product in products:
                if product.name and ',' in product.name:
                    # Извлекаем основную категорию (до первой запятой)
                    category_name = product.name.split(',')[0].strip()
                    
                    # Исключения для категорий
                    if category_name.strip().upper() in ["НАБІР", "КОМПЛЕКТ"]:
                        category_name = "БЮСТГАЛЬТЕР"
                    
                    # Обновляем название товара
                    if product.name != category_name:
                        product.name = category_name
                        updated_count += 1
            
            # Коммитим изменения
            db.session.commit()
            
            print(f"Исправление завершено!")
            print(f"Обновлено товаров: {updated_count}")
            
            # Показываем примеры
            print("\nПримеры исправленных названий:")
            sample_products = Product.query.limit(5).all()
            for product in sample_products:
                print(f"- {product.art}: {product.name}")
            
        except Exception as e:
            print(f"Ошибка при исправлении названий: {e}")
            db.session.rollback()

if __name__ == "__main__":
    fix_product_names() 
from app import app, db, Category, Product

def update_categories():
    """
    Обновляет категории в существующей базе данных:
    - Извлекает основную категорию из названия товара
    - Создает новые категории если нужно
    - Обновляет связи товаров с категориями
    """
    with app.app_context():
        try:
            # Получаем все товары
            products = Product.query.all()
            
            print(f"Найдено {len(products)} товаров для обновления")
            
            updated_count = 0
            new_categories_count = 0
            
            for product in products:
                if product.name:
                    # Извлекаем основную категорию (до первой запятой)
                    category_name = product.name.split(',')[0].strip()
                    
                    # Исключения для категорий
                    if category_name.strip().upper() in ["НАБІР", "КОМПЛЕКТ"]:
                        category_name = "БЮСТГАЛЬТЕР"
                    
                    # Находим или создаем категорию
                    category = Category.query.filter_by(name_ua=category_name).first()
                    if not category:
                        category = Category(name_ua=category_name, name_ru=category_name)
                        db.session.add(category)
                        db.session.commit()
                        new_categories_count += 1
                        print(f"Создана новая категория: {category_name}")
                    
                    # Обновляем связь товара с категорией
                    if product.category_id != category.id:
                        product.category_id = category.id
                        updated_count += 1
            
            # Коммитим изменения
            db.session.commit()
            
            print(f"Обновление завершено!")
            print(f"Обновлено товаров: {updated_count}")
            print(f"Создано новых категорий: {new_categories_count}")
            
        except Exception as e:
            print(f"Ошибка при обновлении категорий: {e}")
            db.session.rollback()

if __name__ == "__main__":
    update_categories() 
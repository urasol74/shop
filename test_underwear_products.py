from app import app, Product
from sqlalchemy import func, or_, and_

app.app_context().push()

print("=== Тестирование товаров в категориях белья ===")
print()

# Тестируем функцию get_underwear_products_by_gender_and_category
def test_underwear_products(gender, category_name, section_name):
    # Базовый запрос
    query = Product.query.filter(
        func.lower(func.trim(Product.brand)) == 'undercolor',
        Product.cat == category_name
    )
    
    # Логика для унісекс товаров в белье
    if gender in ['жiн', 'чол']:
        # Для взрослых категорий (женщины/мужчины)
        # Включаем товары с соответствующим полом И унісекс товары без .K
        query = query.filter(
            or_(
                func.lower(func.trim(Product.gender)) == gender,
                and_(
                    Product.gender == 'унісекс',
                    ~Product.art.like('%.K')
                )
            )
        )
    elif gender in ['дiвч', 'хлопч']:
        # Для детских категорий (девочки/мальчики)
        # Включаем товары с соответствующим полом И унісекс товары с .K
        query = query.filter(
            or_(
                func.lower(func.trim(Product.gender)) == gender,
                and_(
                    Product.gender == 'унісекс',
                    Product.art.like('%.K')
                )
            )
        )
    else:
        # Для остальных случаев используем точное совпадение
        query = query.filter(func.lower(func.trim(Product.gender)) == gender)
    
    products = query.all()
    print(f"До фильтрации: {len(products)} товаров")
    
    # Фильтруем товары (исключаем товары без гендера и с qty 0)
    products = [p for p in products if p.gender and str(p.qty).replace('.', '').isdigit() and float(p.qty) > 0]
    print(f"После фильтрации: {len(products)} товаров")
    
    # Оставляем только по одному товару на артикул
    unique_products = {}
    for p in products:
        if p.art not in unique_products:
            unique_products[p.art] = p
    products = list(unique_products.values())
    print(f"После удаления дублей: {len(products)} товаров")
    
    return products

# Тестируем категорию ШКАРПЕТКИ для женщин
print("=== ШКАРПЕТКИ для женщин ===")
women_socks = test_underwear_products('жiн', 'ШКАРПЕТКИ', 'Женщина')
for sock in women_socks:
    print(f"- {sock.art}: {sock.name} | Пол: {sock.gender} | qty: {sock.qty}")

print("\n" + "="*50)
print()

# Тестируем категорию ШКАРПЕТКИ для мужчин
print("=== ШКАРПЕТКИ для мужчин ===")
men_socks = test_underwear_products('чол', 'ШКАРПЕТКИ', 'Мужчина')
for sock in men_socks:
    print(f"- {sock.art}: {sock.name} | Пол: {sock.gender} | qty: {sock.qty}") 
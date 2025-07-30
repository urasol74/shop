from app import app, get_unique_categories_by_gender

app.app_context().push()

print("=== Тестирование унісекс товаров ===")
print()

# Проверяем унісекс товары в базе
from app import Product
from sqlalchemy import func

unisex_products = Product.query.filter(Product.gender == 'унісекс').all()
print(f"Всего унісекс товаров: {len(unisex_products)}")

# Разделяем по типам артикулов
kids_unisex = [p for p in unisex_products if p.art.endswith('.K')]
adults_unisex = [p for p in unisex_products if not p.art.endswith('.K')]

print(f"Детские унісекс (с .K): {len(kids_unisex)}")
print(f"Взрослые унісекс (без .K): {len(adults_unisex)}")

if kids_unisex:
    print("\nПримеры детских унісекс товаров:")
    for p in kids_unisex[:3]:
        print(f"- {p.art}: {p.cat}")

if adults_unisex:
    print("\nПримеры взрослых унісекс товаров:")
    for p in adults_unisex[:3]:
        print(f"- {p.art}: {p.cat}")

print("\n" + "="*50)
print()

# Тестируем категории для женщин (должны включать взрослые унісекс)
print("Категории для женщин (включая взрослые унісекс):")
categories_women = get_unique_categories_by_gender('жiн')
print(f"Найдено категорий: {len(categories_women)}")
for i, cat in enumerate(categories_women[:5]):
    print(f"{i+1}. {cat['raw']}")

print("\n" + "="*50)
print()

# Тестируем категории для мужчин (должны включать взрослые унісекс)
print("Категории для мужчин (включая взрослые унісекс):")
categories_men = get_unique_categories_by_gender('чол')
print(f"Найдено категорий: {len(categories_men)}")
for i, cat in enumerate(categories_men[:5]):
    print(f"{i+1}. {cat['raw']}")

print("\n" + "="*50)
print()

# Тестируем категории для девочек (должны включать детские унісекс)
print("Категории для девочек (включая детские унісекс):")
categories_girls = get_unique_categories_by_gender('дiвч')
print(f"Найдено категорий: {len(categories_girls)}")
for i, cat in enumerate(categories_girls[:5]):
    print(f"{i+1}. {cat['raw']}")

print("\n" + "="*50)
print()

# Тестируем категории для мальчиков (должны включать детские унісекс)
print("Категории для мальчиков (включая детские унісекс):")
categories_boys = get_unique_categories_by_gender('хлопч')
print(f"Найдено категорий: {len(categories_boys)}")
for i, cat in enumerate(categories_boys[:5]):
    print(f"{i+1}. {cat['raw']}") 
from app import app, get_unique_categories_by_gender

app.app_context().push()

print("=== Отладка категорий ===")
print()

# Женщины
categories_women = get_unique_categories_by_gender('жiн')
print(f"Категории для женщин: {len(categories_women)}")
print("Первые 10 категорий:")
for i, cat in enumerate(categories_women[:10]):
    print(f"{i+1}. raw: '{cat['raw']}' -> pretty: '{cat['pretty']}'")
print()

# Мужчины
categories_men = get_unique_categories_by_gender('чол')
print(f"Категории для мужчин: {len(categories_men)}")
print("Первые 10 категорий:")
for i, cat in enumerate(categories_men[:10]):
    print(f"{i+1}. raw: '{cat['raw']}' -> pretty: '{cat['pretty']}'")
print()

# Дети
categories_girls = get_unique_categories_by_gender('дiвч')
categories_boys = get_unique_categories_by_gender('хлопч')
print(f"Категории для девочек: {len(categories_girls)}")
print(f"Категории для мальчиков: {len(categories_boys)}")
print("Первые 5 категорий для девочек:")
for i, cat in enumerate(categories_girls[:5]):
    print(f"{i+1}. raw: '{cat['raw']}' -> pretty: '{cat['pretty']}'") 
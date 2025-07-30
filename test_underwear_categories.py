from app import app, get_underwear_categories_by_gender

app.app_context().push()

print("=== Тестирование категорий белья ===")
print()

# Женщины
categories_women = get_underwear_categories_by_gender('жiн')
print(f"Категории белья для женщин: {len(categories_women)}")
print("Категории:")
for i, cat in enumerate(categories_women):
    print(f"{i+1}. {cat}")
print()

# Мужчины
categories_men = get_underwear_categories_by_gender('чол')
print(f"Категории белья для мужчин: {len(categories_men)}")
print("Категории:")
for i, cat in enumerate(categories_men):
    print(f"{i+1}. {cat}")
print()

# Девочки
categories_girls = get_underwear_categories_by_gender('дiвч')
print(f"Категории белья для девочек: {len(categories_girls)}")
print("Категории:")
for i, cat in enumerate(categories_girls):
    print(f"{i+1}. {cat}")
print()

# Мальчики
categories_boys = get_underwear_categories_by_gender('хлопч')
print(f"Категории белья для мальчиков: {len(categories_boys)}")
print("Категории:")
for i, cat in enumerate(categories_boys):
    print(f"{i+1}. {cat}")
print() 
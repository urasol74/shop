from app import app, get_unique_categories_by_gender

with app.app_context():
    # Тестируем категории для женщин
    categories_women = get_unique_categories_by_gender('жін')
    print(f'Категории для женщин: {len(categories_women)}')
    print('Первые 5 категорий:')
    for cat in categories_women[:5]:
        print(f'- {cat["raw"]}')
    
    print()
    
    # Тестируем категории для мужчин
    categories_men = get_unique_categories_by_gender('чол')
    print(f'Категории для мужчин: {len(categories_men)}')
    print('Первые 5 категорий:')
    for cat in categories_men[:5]:
        print(f'- {cat["raw"]}')
    
    print()
    
    # Тестируем категории для детей
    categories_kids = get_unique_categories_by_gender('діти')
    print(f'Категории для детей: {len(categories_kids)}')
    print('Первые 5 категорий:')
    for cat in categories_kids[:5]:
        print(f'- {cat["raw"]}') 
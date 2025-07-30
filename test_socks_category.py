from app import app, Product
from sqlalchemy import func, or_, and_

app.app_context().push()

print("=== Тестирование товаров в категории ШКАРПЕТКИ ===")
print()

# Проверяем все товары ШКАРПЕТКИ
all_socks = Product.query.filter(Product.cat == 'ШКАРПЕТКИ').all()
print(f"Всего товаров ШКАРПЕТКИ: {len(all_socks)}")

for sock in all_socks:
    print(f"- {sock.art}: {sock.name} | Пол: {sock.gender} | Бренд: {sock.brand}")

print("\n" + "="*50)
print()

# Проверяем товары ШКАРПЕТКИ для женщин (включая унісекс без .K)
women_socks_query = Product.query.filter(
    func.lower(func.trim(Product.brand)) == 'undercolor',
    Product.cat == 'ШКАРПЕТКИ'
).filter(
    or_(
        func.lower(func.trim(Product.gender)) == 'жiн',
        and_(
            Product.gender == 'унісекс',
            ~Product.art.like('%.K')
        )
    )
)

women_socks = women_socks_query.all()
print(f"Товары ШКАРПЕТКИ для женщин: {len(women_socks)}")
for sock in women_socks:
    print(f"- {sock.art}: {sock.name} | Пол: {sock.gender}")

print("\n" + "="*50)
print()

# Проверяем товары ШКАРПЕТКИ для мужчин (включая унісекс без .K)
men_socks_query = Product.query.filter(
    func.lower(func.trim(Product.brand)) == 'undercolor',
    Product.cat == 'ШКАРПЕТКИ'
).filter(
    or_(
        func.lower(func.trim(Product.gender)) == 'чол',
        and_(
            Product.gender == 'унісекс',
            ~Product.art.like('%.K')
        )
    )
)

men_socks = men_socks_query.all()
print(f"Товары ШКАРПЕТКИ для мужчин: {len(men_socks)}")
for sock in men_socks:
    print(f"- {sock.art}: {sock.name} | Пол: {sock.gender}")

print("\n" + "="*50)
print()

# Проверяем унісекс товары ШКАРПЕТКИ
unisex_socks = Product.query.filter(
    Product.cat == 'ШКАРПЕТКИ',
    Product.gender == 'унісекс'
).all()

print(f"Унісекс товары ШКАРПЕТКИ: {len(unisex_socks)}")
for sock in unisex_socks:
    print(f"- {sock.art}: {sock.name} | Бренд: {sock.brand}") 
from shop.models import db, Product

with db.session.begin():
    for product in Product.query.all():
        if product.new_price and product.new_price < 20:
            product.new_price = int(round(product.new_price * 1000))
        if product.old_price and product.old_price < 20:
            product.old_price = int(round(product.old_price * 1000))
    db.session.commit()
print("Цены исправлены!") 
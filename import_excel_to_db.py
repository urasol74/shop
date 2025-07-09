from flask import render_template, request
from app import app, Product, Category

@app.route('/category/<category_ua>')
def show_category(category_ua):
    # Найти категорию по украинскому названию
    category = Category.query.filter_by(name_ua=category_ua).first_or_404()
    # Получить все товары этой категории
    products = Product.query.filter_by(category_id=category.id).all()
    return render_template(
        'products.html',
        products=products,
        category=category.name_ru,
        section_verbose=category.name_ru,
        pretty_category=category.name_ru,
        back_url='/'
    )

@app.route('/search_db')
def search_db():
    art = request.args.get('art', '').upper()
    color = request.args.get('color', '')
    size = request.args.get('size', '')
    query = Product.query
    if art:
        query = query.filter(Product.art.contains(art))
    if color:
        query = query.filter(Product.color == color)
    if size:
        query = query.filter(Product.size == size)
    products = query.all()
    return render_template(
        'products.html',
        products=products,
        category='Результаты поиска',
        section_verbose='Результаты поиска',
        pretty_category='Результаты поиска',
        back_url='/'
    )
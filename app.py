from flask import Flask, render_template
import openpyxl
import os
import json
import shutil

app = Flask(__name__)

# Глобальная переменная для хранения категорий
kids_categories = []

def load_kids_categories():
    xlsx_path = os.path.join('data', 'der.xlsx')
    wb = openpyxl.load_workbook(xlsx_path)
    ws = wb.active
    categories = set()
    for row in ws.iter_rows(min_row=1):
        values = [str(cell.value) if cell.value is not None else "" for cell in row[:3]]
        combined = " ".join(values).strip()
        if not combined:
            continue
        parts = combined.split()
        if len(parts) < 2:
            continue
        article = parts[0]
        if ".K" in article:
            category = parts[1]
            categories.add(category)
    categories = sorted(categories)
    # Сохраняем в kids_sections.json
    with open('kids_sections.json', 'w', encoding='utf-8') as f:
        json.dump(categories, f, ensure_ascii=False, indent=2)
    return categories

# Загружаем категории один раз при запуске
kids_categories = load_kids_categories()

# Копируем файл Новый.xlsx в /home/ubuntu/shop/data/der.xlsx при запуске
src = "/home/ubuntu/bot_art/data/Новый.xlsx"
dst = "/home/ubuntu/shop/data/der.xlsx"
os.makedirs(os.path.dirname(dst), exist_ok=True)
shutil.copyfile(src, dst)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/kids')
def kids():
    categories = get_kids_categories()
    return render_template('kids.html', categories=categories)

@app.route('/kids/<category>')
def kids_category(category):
     return render_template('kids_category.html', category=category)

def get_kids_categories():
    wb = openpyxl.load_workbook(dst)
    ws = wb.active
    categories = set()
    for row in ws.iter_rows(min_row=2, values_only=True):
        cell = row[0]
        if not cell:
            continue
        cell = str(cell)
        # Проверяем наличие .K (kids)
        if ".K" in cell:
            after_k = cell.split(".K", 1)[1].strip()
            if "," in after_k:
                section = after_k.split(",", 1)[0].strip()
            else:
                section = after_k.strip()
            if section:
                categories.add(section)
    return sorted(categories)

def build_kids_products():
    wb = openpyxl.load_workbook(dst)
    ws = wb.active
    products_by_section = {}
    for row in ws.iter_rows(min_row=2, values_only=True):
        cell = row[0]
        if not cell:
            continue
        cell = str(cell)
        if ".K" in cell:
            after_k = cell.split(".K", 1)[1].strip()
            if "," in after_k:
                section = after_k.split(",", 1)[0].strip()
            else:
                section = after_k.strip()
            section_key = section.upper().strip()
            art = cell.split(".K", 1)[0].strip() + ".K"
            product = f"{section} {art}"
            products_by_section.setdefault(section_key, set()).add(product)
    products_by_section = {k: sorted(list(v)) for k, v in products_by_section.items()}
    with open("kids_products.json", "w", encoding="utf-8") as f:
        json.dump(products_by_section, f, ensure_ascii=False, indent=2)
    return products_by_section

# При запуске сервера
kids_products_by_section = build_kids_products()

@app.route('/kids/<section>')
def kids_section(section):
    section_key = section.upper().strip()
    products = kids_products_by_section.get(section_key, [])
    print(f"[DEBUG] section_key: {section_key}, products: {products}")
    return render_template('kids_products.html', section=section, products=products)

@app.route('/kids/<section>/<art>')
def kids_product(section, art):
    return render_template('kids_product.html', section=section, art=art)

# Заглушки для men и woman
# def get_men_categories():
#     return []
# def get_woman_categories():
#     return []

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)

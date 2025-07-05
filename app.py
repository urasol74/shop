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

def get_gender_map():
    base_path = os.path.join('data', 'base.xlsx')
    wb = openpyxl.load_workbook(base_path)
    ws = wb.active
    gender_map = {}
    for row in ws.iter_rows(min_row=2):
        art = str(row[0].value).replace('.0', '').replace('.K', '').strip().upper() if row[0].value else None
        gender_cell = row[9].value if len(row) > 9 else None
        if art and gender_cell:
            if 'дiвч' in str(gender_cell).lower():
                gender = 'Девочка'
            elif 'дит' in str(gender_cell).lower():
                gender = 'Детское'
            elif 'хлопч' in str(gender_cell).lower():
                gender = 'Мальчик'
            else:
                gender = None
            gender_map[art] = gender
    return gender_map

gender_map = get_gender_map()

@app.route('/kids_category/<category>')
def kids_category(category):
    # Получаем товары для категории (пример: как в kids_section)
    section_key = category.upper().strip()
    products = kids_products_by_section.get(section_key, [])
    # Добавляем поле gender для каждого товара
    for p in products:
        art_key = p['art'].replace('.K', '').strip().upper()
        p['gender'] = gender_map.get(art_key)
    return render_template('kids_category.html', category=category, products=products)

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
    all_rows = list(ws.iter_rows(min_row=2))
    for row in all_rows:
        cell = row[0].value
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
            art_no_k = art.replace('.K', '')
            # --- Уникальность по артикулу ---
            if section_key not in products_by_section:
                products_by_section[section_key] = []
                seen_arts = set()
            else:
                seen_arts = {p['art'] for p in products_by_section[section_key]}
            if art in seen_arts:
                continue
            name = section
            old_price = row[5].value if len(row) > 5 else None
            new_price = row[7].value if len(row) > 7 else None
            sale = row[9].value if len(row) > 9 else None
            # --- Форматирование sale ---
            sale_str = None
            try:
                if sale is not None:
                    sale_num = float(sale)
                    sale_rounded = int(round(sale_num / 10.0) * 10)
                    sale_str = f"-{sale_rounded}%"
            except Exception:
                sale_str = None
            image = f"/static/pic/{art_no_k}.jpg"
            # --- Собираем все строки с этим артикулом для meta-block ---
            color_size_map = {}
            for r in all_rows:
                c = r[0].value
                if not c:
                    continue
                c = str(c)
                if art in c:
                    # Парсим только из первой ячейки строки
                    color = None
                    size = None
                    if 'Цвет:' in c:
                        color = c.split('Цвет:')[-1].split(',')[0].strip()
                    if 'Размер:' in c:
                        size = c.split('Размер:')[-1].split(',')[0].strip()
                    if color:
                        if color not in color_size_map:
                            color_size_map[color] = []
                        if size and size not in color_size_map[color]:
                            color_size_map[color].append(size)
            color_size_list = [{"color": k, "sizes": v} for k, v in color_size_map.items()]
            product = {
                "name": name,
                "art": art,
                "old_price": old_price,
                "new_price": new_price,
                "sale": sale_str,
                "image": image,
                "color_size_map": color_size_list
            }
            products_by_section[section_key].append(product)
    with open("kids_products.json", "w", encoding="utf-8") as f:
        json.dump(products_by_section, f, ensure_ascii=False, indent=2)
    return products_by_section

# При запуске сервера
kids_products_by_section = build_kids_products()

@app.route('/kids/<section>')
def kids_section(section):
    section_key = section.upper().strip()
    products = kids_products_by_section.get(section_key, [])
    # Добавляем поле gender для каждого товара
    for p in products:
        art_key = p['art'].replace('.K', '').strip().upper()
        p['gender'] = gender_map.get(art_key)
    print(f"[DEBUG] section_key: {section_key}, products: {products}")
    return render_template('kids_products.html', section=section, products=products)

@app.route('/kids/<section>/<art>')
def kids_product(section, art):
    section_key = section.upper().strip()
    products = kids_products_by_section.get(section_key, [])
    product = next((p for p in products if p['art'] == art), None)
    return render_template('kids_product.html', section=section, product=product)

# Заглушки для men и woman
# def get_men_categories():
#     return []
# def get_woman_categories():
#     return []

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, debug=True)

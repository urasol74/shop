import openpyxl
import os
import json

# Путь к исходному xlsx-файлу
xlsx_path = os.path.join("file", "der.xlsx")
# Путь к json-файлу для фронта
output_path = "kids_sections.json"

# Открываем xlsx-файл
wb = openpyxl.load_workbook(xlsx_path)
ws = wb.active

categories = set()

# Проходим по всем строкам, ищем категории для kids
for row in ws.iter_rows(min_row=1):
    # Склеиваем значения из первых трёх колонок (A+B+C)
    values = [str(cell.value) if cell.value is not None else "" for cell in row[:3]]
    combined = " ".join(values).strip()
    if not combined:
        continue
    parts = combined.split()
    if len(parts) < 2:
        continue
    article = parts[0]
    if ".K" in article:
        # Слово после артикула — категория
        category = parts[1]
        categories.add(category)

# Сохраняем уникальные категории в JSON для фронта
with open(output_path, "w", encoding="utf-8") as f:
    json.dump(sorted(categories), f, ensure_ascii=False, indent=2)

print(f"Категории для kids сохранены в {output_path}")

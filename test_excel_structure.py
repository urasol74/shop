import pandas as pd
import os

EXCEL_PATH = "/home/ubuntu/shop/data/db-der.xlsx"

def test_excel_structure():
    """Тестируем структуру Excel файла"""
    if not os.path.exists(EXCEL_PATH):
        print(f"Файл {EXCEL_PATH} не найден!")
        return
    
    # Читаем первые 20 строк для анализа
    df = pd.read_excel(EXCEL_PATH, header=None, nrows=20)
    
    print("=== АНАЛИЗ СТРУКТУРЫ EXCEL ФАЙЛА ===")
    print(f"Размер файла: {df.shape}")
    print("\nПервые 10 строк:")
    print(df.head(10))
    
    print("\n=== ДЕТАЛЬНЫЙ АНАЛИЗ ===")
    for i, row in df.iterrows():
        if pd.notna(row[0]):
            print(f"Строка {i}: {row[0]}")
            if "|" in str(row[0]):
                print(f"  -> Это заголовок продукта")
                nomenclature = row[0].split("|")[0].strip()
                print(f"  -> Номенклатура: '{nomenclature}'")
                
                # Тестируем парсинг артикула
                import re
                match = re.match(r'^([A-Z0-9]+\.[A-Z0-9]+)\s+(.+)$', nomenclature)
                if match:
                    article = match.group(1)
                    category_name = match.group(2)
                    print(f"  -> Артикул: '{article}'")
                    print(f"  -> Категория: '{category_name}'")
                else:
                    print(f"  -> Не удалось распарсить артикул")
                
                if len(row) > 1 and pd.notna(row[1]):
                    print(f"  -> Бренд: '{row[1]}'")
                if len(row) > 2 and pd.notna(row[2]):
                    print(f"  -> Сезон: '{row[2]}'")
                if len(row) > 3 and pd.notna(row[3]):
                    print(f"  -> Пол: '{row[3]}'")
            else:
                print(f"  -> Это вариант товара")
                if len(row) > 1 and pd.notna(row[1]):
                    print(f"  -> Размер: '{row[1]}'")
                if len(row) > 2 and pd.notna(row[2]):
                    print(f"  -> Цвет: '{row[2]}'")
                if len(row) > 3 and pd.notna(row[3]):
                    print(f"  -> Штрихкод: '{row[3]}'")
                if len(row) > 4 and pd.notna(row[4]):
                    print(f"  -> Остаток: '{row[4]}'")
        print()

if __name__ == "__main__":
    test_excel_structure() 
#!/usr/bin/env python3
import pandas as pd
import os

def check_gender_data():
    """Проверяем данные о поле в файле db-der.xlsx"""
    file_path = "data/db-der.xlsx"
    
    if not os.path.exists(file_path):
        print(f"Файл {file_path} не найден!")
        return
    
    print("=== ПОИСК ДАННЫХ О ПОЛЕ ===")
    
    try:
        # Читаем больше строк для поиска данных о поле
        df = pd.read_excel(file_path, header=None, nrows=100)
        
        for i, row in df.iterrows():
            if pd.notna(row[0]) and str(row[0]).strip():
                cell_value = str(row[0]).strip()
                
                # Пропускаем заголовки отчета
                if any(skip in cell_value.lower() for skip in ['оценка', 'параметри', 'відбір', 'магазин', 'склад', 'номенклатура', 'артикул']):
                    continue
                
                # Ищем строки с артикулами (заголовки продуктов)
                if " " in cell_value and len(cell_value.split(" ")) > 1:
                    print(f"Строка {i}: {cell_value}")
                    
                    # Показываем все колонки для этой строки
                    for j in range(len(row)):
                        if pd.notna(row[j]):
                            print(f"  Колонка {j}: '{row[j]}'")
                    
                    # Ищем данные о поле в соседних строках
                    print("  Поиск данных о поле в соседних строках:")
                    for k in range(max(0, i-2), min(len(df), i+3)):
                        if k != i and pd.notna(df.iloc[k, 0]):
                            neighbor_value = str(df.iloc[k, 0]).strip()
                            if any(gender_word in neighbor_value.lower() for gender_word in ['жін', 'чол', 'жінка', 'чоловік', 'ж', 'ч']):
                                print(f"    Строка {k}: '{neighbor_value}'")
                    
                    print()
        
    except Exception as e:
        print(f"Ошибка при чтении файла: {e}")

if __name__ == "__main__":
    check_gender_data() 
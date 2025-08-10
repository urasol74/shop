#!/usr/bin/env python3
import pandas as pd
import os

def check_db_der():
    """Проверяем структуру файла db-der.xlsx"""
    file_path = "data/db-der.xlsx"
    
    if not os.path.exists(file_path):
        print(f"Файл {file_path} не найден!")
        return
    
    print(f"Файл {file_path} найден")
    print(f"Размер файла: {os.path.getsize(file_path)} байт")
    
    try:
        # Читаем больше строк
        df = pd.read_excel(file_path, header=None, nrows=50)
        print(f"\nРазмер данных: {df.shape}")
        
        print("\n=== ПОИСК РЕАЛЬНЫХ ДАННЫХ ===")
        data_rows = 0
        for i, row in df.iterrows():
            if pd.notna(row[0]) and str(row[0]).strip():
                # Ищем строки, которые выглядят как артикулы товаров
                cell_value = str(row[0]).strip()
                
                # Пропускаем заголовки отчета
                if any(skip in cell_value.lower() for skip in ['оценка', 'параметри', 'відбір', 'магазин', 'склад', 'номенклатура', 'артикул']):
                    continue
                
                # Ищем строки с артикулами (содержат буквы и цифры)
                if any(c.isalpha() for c in cell_value) and any(c.isdigit() for c in cell_value):
                    data_rows += 1
                    print(f"Строка {i}: {cell_value}")
                    
                    # Показываем соседние ячейки
                    for j in range(1, min(5, len(row))):
                        if pd.notna(row[j]):
                            print(f"  Колонка {j}: {row[j]}")
                    print()
        
        print(f"\nНайдено строк с товарами: {data_rows}")
        
        # Попробуем найти строки с разделителем "|"
        print("\n=== ПОИСК СТРОК С РАЗДЕЛИТЕЛЕМ '|' ===")
        pipe_rows = 0
        for i, row in df.iterrows():
            if pd.notna(row[0]) and "|" in str(row[0]):
                pipe_rows += 1
                print(f"Строка {i}: {row[0]}")
        print(f"\nНайдено строк с '|': {pipe_rows}")
        
    except Exception as e:
        print(f"Ошибка при чтении файла: {e}")

if __name__ == "__main__":
    check_db_der() 
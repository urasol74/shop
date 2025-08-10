#!/usr/bin/env python3
import pandas as pd
import os

def check_excel_file():
    file_path = "data/db-der.xlsx"
    
    if not os.path.exists(file_path):
        print(f"Файл {file_path} не найден!")
        return
    
    print(f"Файл {file_path} найден")
    print(f"Размер файла: {os.path.getsize(file_path)} байт")
    
    try:
        # Пробуем разные движки
        engines = ['openpyxl', 'xlrd', 'odf']
        
        for engine in engines:
            try:
                print(f"\nПробуем движок: {engine}")
                df = pd.read_excel(file_path, engine=engine, header=None, nrows=10)
                print(f"Успешно! Размер данных: {df.shape}")
                print("Первые 5 строк:")
                print(df.head())
                return df
            except Exception as e:
                print(f"Ошибка с движком {engine}: {e}")
                
    except Exception as e:
        print(f"Общая ошибка: {e}")

if __name__ == "__main__":
    check_excel_file() 
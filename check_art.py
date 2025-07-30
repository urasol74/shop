#!/usr/bin/env python3
import openpyxl
import sys

def check_art(art_code):
    wb = openpyxl.load_workbook('data/base.xlsx')
    ws = wb.active
    
    found = False
    for row in ws.iter_rows(min_row=2):
        if row[0].value and str(row[0].value).strip().upper() == art_code.upper():
            print(f'Артикул: {row[0].value}')
            print(f'Бренд (колонка 7): {row[6].value if len(row) > 6 else "НЕТ"}')
            print(f'Сезон (колонка 9): {row[8].value if len(row) > 8 else "НЕТ"}')
            print(f'Пол (колонка 10): {row[9].value if len(row) > 9 else "НЕТ"}')
            found = True
            break
    
    if not found:
        print(f'Артикул {art_code} не найден в base.xlsx')

if __name__ == "__main__":
    if len(sys.argv) > 1:
        check_art(sys.argv[1])
    else:
        print("Использование: python check_art.py <артикул>") 
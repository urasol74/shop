#!/usr/bin/env python3
import sqlite3
import openpyxl
import os

def check_kids_tshirts():
    # Читаем артикулы из base.db
    bot_db_path = "/home/ubuntu/bot_art/instance/base.db"
    conn = sqlite3.connect(bot_db_path)
    cursor = conn.cursor()
    
    cursor.execute("SELECT DISTINCT art FROM sklad_items WHERE name LIKE '%ФУТБОЛКА%' AND art LIKE '%.K' ORDER BY art")
    base_db_arts = [row[0].replace('.K', '') for row in cursor.fetchall()]
    conn.close()
    
    print(f"Артикулов футболок с .K в base.db: {len(base_db_arts)}")
    
    # Читаем артикулы из base.xlsx
    base_xlsx_path = os.path.join('data', 'base.xlsx')
    wb = openpyxl.load_workbook(base_xlsx_path)
    ws = wb.active
    
    base_xlsx_arts = set()
    for row in ws.iter_rows(min_row=2):
        if row[0].value:
            base_xlsx_arts.add(str(row[0].value).strip().upper())
    
    print(f"Всего артикулов в base.xlsx: {len(base_xlsx_arts)}")
    
    # Проверяем, какие есть в base.xlsx
    found = [art for art in base_db_arts if art in base_xlsx_arts]
    print(f"Найдено в base.xlsx: {len(found)}")
    print("Найденные артикулы:")
    for art in found:
        print(f"  {art}")
    
    # Проверяем, какие НЕ найдены
    not_found = [art for art in base_db_arts if art not in base_xlsx_arts]
    print(f"\nНЕ найдено в base.xlsx: {len(not_found)}")
    print("Отсутствующие артикулы:")
    for art in not_found[:10]:  # Показываем первые 10
        print(f"  {art}")
    if len(not_found) > 10:
        print(f"  ... и еще {len(not_found) - 10}")

if __name__ == "__main__":
    check_kids_tshirts() 
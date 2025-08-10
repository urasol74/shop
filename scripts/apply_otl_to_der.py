#!/usr/bin/env python3
"""
Скрипт вычитает количество брака (OTL) из основной БД db-der.db по ключу (article, color, size).

Источник: /home/ubuntu/baf-otl/instance/base-otl.db, таблица otl_items
Цель:    /home/ubuntu/shop/instance/db-der.db, таблица variants (через products.article)

Режимы:
  --dry-run  только отчёт без изменений
  --apply    применить изменения (по умолчанию dry-run)

Отчёт: сколько найдено совпадений, сколько изменено, список строк с нулевым или отрицательным остатком после вычитания.
"""
import argparse
import os
import sqlite3
from collections import defaultdict

DER_DB = "/home/ubuntu/shop/instance/db-der.db"
OTL_DB = "/home/ubuntu/baf-otl/instance/base-otl.db"


def fetch_otl_items(conn_otl):
    cur = conn_otl.cursor()
    cur.execute("SELECT art, color, size, qty FROM otl_items WHERE art IS NOT NULL")
    rows = cur.fetchall()
    otl = defaultdict(int)
    for art, color, size, qty in rows:
        key = (str(art or '').strip(), str(color or '').strip(), str(size or '').strip())
        try:
            qty_i = int(qty or 0)
        except Exception:
            qty_i = 0
        otl[key] += qty_i
    return otl


def main(apply: bool):
    if not os.path.exists(DER_DB):
        raise SystemExit(f"Не найдена БД {DER_DB}")
    if not os.path.exists(OTL_DB):
        raise SystemExit(f"Не найдена БД {OTL_DB}")

    conn_der = sqlite3.connect(DER_DB)
    conn_otl = sqlite3.connect(OTL_DB)
    cur_der = conn_der.cursor()

    otl_map = fetch_otl_items(conn_otl)
    print(f"OTL записей (агрегировано по (art,color,size)): {len(otl_map)}")

    # Подготовим быстрый доступ: article -> [product_id,...] (артикул может быть в нескольких сезонах)
    cur_der.execute("SELECT id, article FROM products")
    prod_ids_by_art = {}
    for pid, article in cur_der.fetchall():
        a = str(article or '').strip()
        if not a:
            continue
        prod_ids_by_art.setdefault(a, []).append(pid)

    updated = 0
    missing_products = []
    summary = []

    for (art, color, size), otl_qty in otl_map.items():
        pid_list = prod_ids_by_art.get(art)
        if not pid_list:
            missing_products.append((art, color, size, otl_qty))
            continue
        found_any = False
        for pid in pid_list:
            # Найдём варианты в этом сезоне
            cur_der.execute(
                "SELECT id, stock FROM variants WHERE product_id=? AND TRIM(COALESCE(color,''))=? AND TRIM(COALESCE(size,''))=?",
                (pid, color, size),
            )
            rows = cur_der.fetchall()
            for var_id, stock in rows:
                found_any = True
                old_stock = float(stock or 0)
                new_stock = old_stock - float(otl_qty)
                summary.append((art, color, size, old_stock, otl_qty, new_stock))
                if apply:
                    cur_der.execute("UPDATE variants SET stock=? WHERE id=?", (new_stock, var_id))
                    updated += 1
        if not found_any:
            missing_products.append((art, color, size, otl_qty))

    if apply:
        conn_der.commit()
    conn_der.close()
    conn_otl.close()

    # Отчёт
    print(f"Изменённых вариантов: {updated} (apply={'yes' if apply else 'no'})")
    negatives = [r for r in summary if r[5] < 0]
    zeros = [r for r in summary if r[5] == 0]
    print(f"Стали отрицательными: {len(negatives)}; Стали нулевыми: {len(zeros)}")
    if missing_products:
        print(f"Не найдены в нашей БД (article/color/size): {len(missing_products)}")
        for i, (a, c, s, q) in enumerate(missing_products[:20], start=1):
            print(f"  {i}. {a} | {c} | {s} | qty={q}")
        if len(missing_products) > 20:
            print(f"  ... ещё {len(missing_products) - 20} строк")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--apply', action='store_true', help='Применить изменения (по умолчанию dry-run)')
    args = parser.parse_args()
    main(apply=args.apply)



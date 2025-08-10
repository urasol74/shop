import os
import sqlite3

DB_PATH = '/home/ubuntu/shop/instance/shop.db'
IMG_DIR = '/home/ubuntu/shop/static/pic/'
OUTPUT_FILE = 'no-img.txt'

def main():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("SELECT art FROM product")
    arts = [row[0] for row in cursor.fetchall()]

    missing_images = []

    for art in arts:
        # Обрезаем суффикс после точки, если он есть
        base_art = art.split('.')[0]

        image_path = os.path.join(IMG_DIR, f"{base_art}.jpg")

        if not os.path.isfile(image_path):
            missing_images.append(art)  # Записываем оригинальный art, даже если он с .K

    with open(OUTPUT_FILE, 'w') as f:
        for art in missing_images:
            f.write(f"{art}\n")

    print(f"Готово. Найдено {len(missing_images)} артикулов без изображений. Список в {OUTPUT_FILE}")

if __name__ == '__main__':
    main()

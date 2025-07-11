import os
from PIL import Image

# Пути к папкам
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ORIGINALS_DIR = BASE_DIR
LIST_DIR = os.path.join(BASE_DIR, 'list')
CAT_DIR = os.path.join(BASE_DIR, 'cat')

# Размеры миниатюр
LIST_SIZE = (378, 378)   # для product.html (большая карточка)
CAT_SIZE = (180, 150)     # для products.html (маленькая карточка)

# Создаём папки, если их нет
os.makedirs(LIST_DIR, exist_ok=True)
os.makedirs(CAT_DIR, exist_ok=True)

def is_image(filename):
    return filename.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))

def make_thumbnail(src_path, dst_path, size):
    try:
        with Image.open(src_path) as img:
            img = img.convert('RGB')
            img.thumbnail(size, Image.LANCZOS)
            # Создаём белый фон нужного размера
            background = Image.new('RGB', size, (255, 255, 255))
            offset = ((size[0] - img.width) // 2, (size[1] - img.height) // 2)
            background.paste(img, offset)
            background.save(dst_path, 'JPEG', quality=90)
            print(f'Создано: {dst_path}')
    except Exception as e:
        print(f'Ошибка для {src_path}: {e}')

def main():
    for filename in os.listdir(ORIGINALS_DIR):
        src_path = os.path.join(ORIGINALS_DIR, filename)
        if not os.path.isfile(src_path) or not is_image(filename):
            continue
        # Миниатюра для product.html (list)
        dst_list = os.path.join(LIST_DIR, filename)
        make_thumbnail(src_path, dst_list, LIST_SIZE)
        # Миниатюра для products.html (cat)
        dst_cat = os.path.join(CAT_DIR, filename)
        make_thumbnail(src_path, dst_cat, CAT_SIZE)

if __name__ == '__main__':
    main() 
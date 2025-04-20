import os
from tqdm import tqdm  # Прогресс-бар (установка: pip install tqdm)


"""
Программа помогает очистить место с компа
Иногда где-то глубоко в папках хранятся больше файлы о которых мы даже не знаем
Это первая итерация программы, а значит будут баги и в будущем я буду её улучшать + добавлять новый функционал
В случае, если требуется найти папку не более 5ГБ, а более 10ГБ например, то смотрим в def find_large_folders и меняем min_size_gb на нужное кол-во ГБ
Спасибо за установку! Удачи :D
"""

#  Вес папки
def get_folder_size(folder_path):
    """Возвращает размер папки в байтах (рекурсивно)."""
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(folder_path):
        for filename in filenames:
            file_path = os.path.join(dirpath, filename)
            if os.path.exists(file_path):
                try:
                    total_size += os.path.getsize(file_path)
                except (OSError, PermissionError):
                    continue
    return total_size

#  Вес > указанного
def find_large_folders(root_path, min_size_gb=5):
    min_size_bytes = min_size_gb * 1024 ** 3
    large_folders = []

    # 1. Считаем общий размер корневой папки
    root_size = get_folder_size(root_path)
    root_size_gb = root_size / (1024 ** 3)

    # 2. Находим все подпапки и проверяем их размер
    all_subfolders = []
    for dirpath, dirnames, filenames in os.walk(root_path):
        for dirname in dirnames:
            full_path = os.path.join(dirpath, dirname)
            all_subfolders.append(full_path)

    # 3. Проверяем каждую подпапку
    for folder in tqdm(all_subfolders, desc="Сканирование"):
        try:
            folder_size = get_folder_size(folder)
            if folder_size >= min_size_bytes:
                size_gb = folder_size / (1024 ** 3)
                large_folders.append((folder, size_gb))
        except (PermissionError, OSError) as e:
            print(f"\nОшибка доступа к {folder}: {e}")
            continue

    return root_size_gb, large_folders

#  Запуск
if __name__ == "__main__":
    root_path = input("Введите путь к папке (например, C:\\Users\\user): ").strip()
    if not os.path.isdir(root_path):
        print("Ошибка: путь не существует!")
        exit(1)

    min_size_gb = 5  # Можно заменить на float(input("Минимальный размер (ГБ): "))

    print(f"\nПоиск папок > {min_size_gb} ГБ в {root_path}...")
    total_size, large_folders = find_large_folders(root_path, min_size_gb)

    print(f"\nОбщий размер папки {root_path}: {total_size:.2f} ГБ")

    if large_folders:
        print("\nБольшие вложенные папки:")
        for folder, size in sorted(large_folders, key=lambda x: -x[1]):  # Сортировка по убыванию
            print(f"{folder} - {size:.2f} ГБ")
    else:
        print("\nБольших вложенных папок не найдено.")
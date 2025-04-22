import os
from tqdm import tqdm


"""
Программа помогает очистить место с компа
Иногда где-то глубоко в папках хранятся больше файлы о которых мы даже не знаем
Это первая итерация программы, а значит будут баги и в будущем я буду её улучшать + добавлять новый функционал
В случае, если требуется найти папку не более 5ГБ, а более 10ГБ например, то смотрим в def find_large_folders и меняем min_size_gb на нужное кол-во ГБ
Спасибо за установку! Удачи :D
"""


#  Вес папки
def get_folder_size(folder_path):
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
    all_subfolders = []

    for dirpath, dirnames, filenames in os.walk(root_path):
        for dirname in dirnames:
            full_path = os.path.join(dirpath, dirname)
            all_subfolders.append(full_path)

    # Создаём кастомный прогресс-бар с градиентом
    with tqdm(total=len(all_subfolders), desc="Сканирование", ncols=100) as pbar:
        for i, folder in enumerate(all_subfolders):
            try:  # Работаю над этим, некоторые папки не сканируются из-за малого доступа
                folder_size = get_folder_size(folder)
                if folder_size >= min_size_bytes:
                    size_gb = folder_size / (1024 ** 3)
                    large_folders.append((folder, size_gb))
            except (PermissionError, OSError) as e:
                print(f"\nОшибка доступа к {folder}: {e}")

            # Меняем цвет каждые 5% (красный → зелёный)
            progress_percent = (i + 1) / len(all_subfolders) * 100
            red = int(255 * (1 - progress_percent / 100))
            green = int(255 * (progress_percent / 100))
            pbar.colour = f"#{red:02x}{green:02x}00"  # HEX-код цвета
            pbar.update(1)

    return large_folders


#  Запуск
if __name__ == "__main__":
    root_path = input("Введите путь к папке: ").strip()
    if not os.path.isdir(root_path):
        print("Ошибка: путь не существует!")
        exit(1)

    print(f"\nПоиск папок > 5 ГБ в {root_path}...")
    large_folders = find_large_folders(root_path)

    if large_folders:
        print("\nРезультаты:")
        for folder, size in sorted(large_folders, key=lambda x: -x[1]):
            print(f"{folder} - {size:.2f} ГБ")
    else:
        print("\nБольших папок не найдено.")
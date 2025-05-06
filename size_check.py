import os
import sys
import subprocess
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QProgressBar, QFileDialog,
                             QListWidget, QSpinBox, QCheckBox, QListWidgetItem,
                             QComboBox, QDoubleSpinBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QBrush, QFont


"""
Программа помогает очистить место с компа
Иногда где-то глубоко в папках хранятся больше файлы о которых мы даже не знаем и вот я тут чтобы помочь!
Спасибо за установку! Удачи :D
"""


class FolderScanner(QThread):
    """
    Класс для сканирования папок в отдельном потоке
    Находит все папки, превышающие заданный размер
    """
    progress_updated = pyqtSignal(int, int)  # current, total - прогресс сканирования
    folder_found = pyqtSignal(str, float, bool)  # path, size, is_top_level - найденная папка
    total_size_calculated = pyqtSignal(float)  # общий размер сканируемой папки
    error_occurred = pyqtSignal(str)  # ошибки при сканировании
    scan_complete = pyqtSignal()  # сигнал завершения сканирования

    def __init__(self, root_path, min_size_gb, skip_hidden=False):
        super().__init__()
        self.root_path = os.path.normpath(root_path)
        self.min_size_gb = min_size_gb
        self.skip_hidden = skip_hidden
        self.running = True  # флаг для остановки сканирования
        self.total_folders = 0  # общее количество папок
        self.processed_folders = 0  # обработанные папки

    def run(self):
        """Основной метод сканирования"""
        try:
            # Подсчет общего количества папок для прогресс-бара
            self.count_folders(self.root_path)

            # Быстрый расчет общего размера корневой папки
            total_size = self.fast_get_folder_size(self.root_path)
            self.total_size_calculated.emit(total_size / (1024 ** 3))  # конвертируем в ГБ

            # Определяем папки первого уровня (непосредственно в корневой папке)
            top_level_folders = set()
            with os.scandir(self.root_path) as it:
                for entry in it:
                    if entry.is_dir() and not (self.skip_hidden and entry.name.startswith('.')):
                        top_level_folders.add(os.path.normpath(entry.path))

            # Основной цикл сканирования
            for dirpath, dirnames, filenames in os.walk(self.root_path):
                if not self.running:  # проверка флага остановки
                    return

                # Проверяем, является ли текущая папка папкой первого уровня
                is_top_level = os.path.normpath(dirpath) in top_level_folders

                try:
                    # Получаем размер папки и проверяем условие
                    folder_size = self.fast_get_folder_size(dirpath)
                    if folder_size >= self.min_size_gb * (1024 ** 3):
                        size_gb = folder_size / (1024 ** 3)  # конвертируем в ГБ
                        self.folder_found.emit(dirpath, size_gb, is_top_level)
                except Exception as e:
                    self.error_occurred.emit(str(e))

                # Обновляем прогресс
                self.processed_folders += 1
                self.progress_updated.emit(self.processed_folders, self.total_folders)

            # Сканирование завершено
            self.scan_complete.emit()

        except Exception as e:
            self.error_occurred.emit(str(e))

    def count_folders(self, start_path):
        """Рекурсивно подсчитываем общее количество папок"""
        self.total_folders = 0
        for root, dirs, files in os.walk(start_path):
            if not self.running:
                return
            self.total_folders += len(dirs)

    def fast_get_folder_size(self, path):
        """Быстрое вычисление размера папки (рекурсивно)"""
        total_size = 0
        try:
            with os.scandir(path) as it:
                for entry in it:
                    if not self.running:
                        return 0
                    try:
                        if entry.is_file():
                            total_size += entry.stat().st_size  # размер файла
                        elif entry.is_dir():
                            # рекурсивно получаем размер подпапки
                            total_size += self.fast_get_folder_size(entry.path)
                    except:
                        continue  # игнорируем ошибки доступа
        except:
            return 0  # в случае ошибки возвращаем 0
        return total_size

    def stop(self):
        """Остановка сканирования"""
        self.running = False


class MainWindow(QMainWindow):
    """
    Главное окно приложения с графическим интерфейсом
    """

    def __init__(self):
        super().__init__()
        self.scanner = None  # объект сканера
        self.all_folders = []  # список всех найденных папок
        self.initUI()  # инициализация интерфейса

    def initUI(self):
        """Инициализация пользовательского интерфейса"""
        # Настройки главного окна
        self.setWindowTitle('Большие папки')
        self.setGeometry(100, 100, 1000, 700)
        self.setMinimumSize(800, 600)

        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        layout.setSpacing(10)  # расстояние между элементами

        # 1. Заголовок
        title = QLabel("🔍 Поиск больших папок")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(title)

        # 2. Выбор папки для сканирования
        path_layout = QHBoxLayout()
        path_label = QLabel("📂 Папка для анализа:")
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Укажите путь или нажмите 'Обзор'")
        self.path_edit.setStyleSheet("padding: 5px;")

        path_btn = QPushButton("🌐 Обзор...")
        path_btn.setStyleSheet("padding: 5px; background: #4CAF50; color: white;")
        path_btn.clicked.connect(self.select_folder)

        path_layout.addWidget(path_label)
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(path_btn)

        # 3. Настройки сканирования
        settings_layout = QHBoxLayout()

        # Минимальный размер
        size_layout = QHBoxLayout()
        size_label = QLabel("📏 Минимальный размер:")
        self.size_spin = QSpinBox()
        self.size_spin.setRange(1, 1000)
        self.size_spin.setValue(1)
        self.size_spin.setStyleSheet("padding: 5px; width: 80px;")
        size_unit = QLabel("ГБ")

        size_layout.addWidget(size_unit)

        # Пропуск скрытых папок
        self.skip_hidden_check = QCheckBox("👻 Пропускать скрытые папки")
        self.skip_hidden_check.setChecked(True)

        settings_layout.addWidget(size_label)
        settings_layout.addWidget(self.size_spin)
        settings_layout.addLayout(size_layout)
        settings_layout.addStretch()
        settings_layout.addWidget(self.skip_hidden_check)

        # 4. Прогресс сканирования
        self.progress = QProgressBar()
        self.progress.setAlignment(Qt.AlignCenter)
        self.progress.setValue(0)
        self.progress.setFormat("Готов к работе")
        self.progress.setStyleSheet("""
            QProgressBar {
                border: 2px solid grey;
                border-radius: 5px;
                text-align: center;
                padding: 1px;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #05B8CC;
                width: 10px;
            }
        """)

        # 5. Информация об общем размере
        self.total_size_label = QLabel("💾 Общий размер: не сканировано")
        self.total_size_label.setAlignment(Qt.AlignRight)
        self.total_size_label.setStyleSheet("font-weight: bold; color: #333;")

        # 6. Управление сканированием
        controls_layout = QHBoxLayout()

        self.scan_btn = QPushButton("🚀 Начать сканирование")
        self.scan_btn.setStyleSheet("""
            QPushButton {
                padding: 8px;
                background: #4CAF50;
                color: white;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background: #45a049;
            }
            QPushButton:disabled {
                background: #cccccc;
            }
        """)
        self.scan_btn.clicked.connect(self.start_scan)

        self.stop_btn = QPushButton("⏹ Остановить")
        self.stop_btn.setEnabled(False)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                padding: 8px;
                background: #f44336;
                color: white;
                border-radius: 5px;
            }
            QPushButton:hover {
                background: #d32f2f;
            }
            QPushButton:disabled {
                background: #cccccc;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_scan)

        controls_layout.addWidget(self.scan_btn)
        controls_layout.addWidget(self.stop_btn)
        controls_layout.addStretch()

        # 7. Фильтрация результатов
        filter_layout = QHBoxLayout()
        filter_label = QLabel("🔧 Сортировка:")
        self.filter_combo = QComboBox()
        self.filter_combo.addItems([
            "🌀 Оригинальный порядок",
            "⬇️ По размеру (убыв.)",
            "⬆️ По размеру (возр.)",
            "🔤 По алфавиту"
        ])
        self.filter_combo.setEnabled(False)
        self.filter_combo.setStyleSheet("padding: 5px;")
        self.filter_combo.currentIndexChanged.connect(self.apply_filter)

        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.filter_combo)
        filter_layout.addStretch()

        # 8. Результаты сканирования
        results_label = QLabel("📊 Результаты:")
        results_label.setStyleSheet("font-weight: bold;")

        self.results_list = QListWidget()
        self.results_list.setFont(QFont("Consolas", 10))
        self.results_list.setStyleSheet("""
            QListWidget {
                background: #f9f9f9;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 5px;
            }
            QListWidget::item {
                padding: 5px;
                border-bottom: 1px solid #eee;
            }
            QListWidget::item:hover {
                background: #e6f7ff;
            }
        """)
        self.results_list.itemDoubleClicked.connect(self.open_folder)

        # Сборка всех элементов интерфейса
        layout.addLayout(path_layout)
        layout.addLayout(settings_layout)
        layout.addWidget(self.progress)
        layout.addWidget(self.total_size_label)
        layout.addLayout(controls_layout)
        layout.addLayout(filter_layout)
        layout.addWidget(results_label)
        layout.addWidget(self.results_list)

    def select_folder(self):
        """Выбор папки для сканирования"""
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку для анализа")
        if folder:
            self.path_edit.setText(folder)

    def start_scan(self):
        """Запуск процесса сканирования"""
        if self.scanner and self.scanner.isRunning():
            return  # сканирование уже идет

        # Получаем и очищаем путь
        path = self.path_edit.text().strip()

        # Проверка на пустой путь
        if not path:
            self.show_error("Поле пути не может быть пустым!")
            return

        # Проверка существования папки
        if not os.path.isdir(path):
            self.show_error("Указанная папка не существует!")
            return

        # Подготовка интерфейса перед сканированием
        self.results_list.clear()
        self.all_folders = []
        self.progress.setValue(0)
        self.progress.setFormat("Подготовка...")
        self.total_size_label.setText("💾 Общий размер: вычисляется...")
        self.filter_combo.setEnabled(False)

        # Создаем и настраиваем сканер
        self.scanner = FolderScanner(
            path,
            self.size_spin.value(),
            self.skip_hidden_check.isChecked()
        )

        # Подключаем сигналы сканера к слотам
        self.scanner.progress_updated.connect(self.update_progress)
        self.scanner.folder_found.connect(self.add_folder_data)
        self.scanner.total_size_calculated.connect(self.show_total_size)
        self.scanner.error_occurred.connect(self.show_error)
        self.scanner.scan_complete.connect(self.on_scan_complete)
        self.scanner.finished.connect(self.scan_finished)

        # Блокируем кнопки во время сканирования
        self.scan_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)

        # Запускаем сканер в отдельном потоке
        self.scanner.start()

    def stop_scan(self):
        """Остановка сканирования"""
        if self.scanner and self.scanner.isRunning():
            self.scanner.stop()  # устанавливаем флаг остановки
            self.scanner.wait()  # ждем завершения потока
        self.scan_finished()

    def scan_finished(self):
        """Действия после завершения сканирования"""
        self.scan_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress.setFormat("Сканирование завершено")

    def on_scan_complete(self):
        """Действия после успешного завершения сканирования"""
        self.filter_combo.setEnabled(True)
        self.apply_filter(0)  # показываем результаты в оригинальном порядке

    def update_progress(self, current, total):
        """Обновление прогресс-бара"""
        self.progress.setMaximum(total)
        self.progress.setValue(current)

        # Красивое форматирование текста прогресса
        percent = int((current / total) * 100) if total > 0 else 0
        self.progress.setFormat(f"🔍 Сканирование: {current}/{total} папок ({percent}%)")

    def add_folder_data(self, path, size, is_top_level):
        """Добавление найденной папки в список результатов"""
        # Сохраняем данные папки
        self.all_folders.append((path, size, is_top_level))

        # Создаем элемент списка
        item = QListWidgetItem(f"{path} - {size:.2f} ГБ")

        # Подсветка дочерних папок серым цветом
        if not is_top_level:
            item.setForeground(QBrush(QColor(120, 120, 120)))

        self.results_list.addItem(item)

    def apply_filter(self, index):
        """Применение выбранного фильтра к результатам"""
        self.results_list.clear()

        # Разделяем родительские и дочерние папки
        parent_folders = [f for f in self.all_folders if f[2]]  # is_top_level=True
        child_folders = [f for f in self.all_folders if not f[2]]  # is_top_level=False

        # Сортируем родительские папки согласно выбранному фильтру
        if index == 1:  # По размеру (убыв.)
            parent_folders.sort(key=lambda x: -x[1])
        elif index == 2:  # По размеру (возр.)
            parent_folders.sort(key=lambda x: x[1])
        elif index == 3:  # По алфавиту
            parent_folders.sort(key=lambda x: x[0].lower())

        # Восстанавливаем иерархию папок
        for path, size, _ in parent_folders:
            # Добавляем родительскую папку
            item = QListWidgetItem(f"{path} - {size:.2f} ГБ")
            self.results_list.addItem(item)

            # Добавляем все дочерние папки
            for child_path, child_size, _ in child_folders:
                if child_path.startswith(path + os.sep):
                    child_item = QListWidgetItem(f"  ├─ {child_path} - {child_size:.2f} ГБ")
                    child_item.setForeground(QBrush(QColor(120, 120, 120)))
                    self.results_list.addItem(child_item)

    def show_total_size(self, size_gb):
        """Отображение общего размера сканируемой папки"""
        self.total_size_label.setText(f"💾 Общий размер: {size_gb:.2f} ГБ")

    def show_error(self, message):
        """Отображение ошибки в списке результатов"""
        item = QListWidgetItem(f"❌ Ошибка: {message}")
        item.setForeground(QBrush(QColor(255, 0, 0)))
        self.results_list.addItem(item)

    def open_folder(self, item):
        """Открытие папки в проводнике"""
        text = item.text().strip()
        if text.startswith("❌ Ошибка:"):
            return

        path = item.text().split(" - ")[0].strip()
        if '├─' in path:  # Фиксит открытие подпапок
            path = path.split('├─')[1].strip()
        if os.path.exists(path):
            try:
                if sys.platform == 'win32':
                    os.startfile(path)
                elif sys.platform == 'darwin':
                    subprocess.run(['open', path])
                else:
                    subprocess.run(['xdg-open', path])
            except Exception as e:
                self.show_error(f"Не удалось открыть папку: {str(e)}")
        else:
            self.show_error(f"Папка не найдена: {path}")

    def closeEvent(self, event):
        """Обработка закрытия окна"""
        self.stop_scan()  # останавливаем сканирование при закрытии
        event.accept()


if __name__ == '__main__':
    # Создаем и настраиваем приложение
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # современный стиль интерфейса

    # Создаем и показываем главное окно
    window = MainWindow()
    window.show()

    # Запускаем главный цикл приложения
    sys.exit(app.exec_())
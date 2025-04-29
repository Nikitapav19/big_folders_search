import os
import sys
import subprocess
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QProgressBar, QFileDialog,
                             QListWidget, QSpinBox, QSizePolicy, QCheckBox, QListWidgetItem)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QColor, QBrush


"""
Программа помогает очистить место с компа
Иногда где-то глубоко в папках хранятся больше файлы о которых мы даже не знаем и вот я тут чтобы помочь!
Спасибо за установку! Удачи :D
"""


class FolderScanner(QThread):
    progress_updated = pyqtSignal(int, int)
    folder_found = pyqtSignal(str, float, bool)  # path, size, is_parent
    total_size_calculated = pyqtSignal(float)
    error_occurred = pyqtSignal(str)

    def __init__(self, root_path, min_size_gb, skip_hidden=False):
        super().__init__()
        self.root_path = root_path
        self.min_size_gb = min_size_gb
        self.skip_hidden = skip_hidden
        self.running = True
        self.folder_cache = {}

    def run(self):
        try:
            # Быстрый расчет общего размера
            total_size = self.fast_get_folder_size(self.root_path)
            self.total_size_calculated.emit(total_size / (1024 ** 3))

            # Сканирование с оптимизацией
            self.scan_folders(self.root_path)

        except Exception as e:
            self.error_occurred.emit(str(e))

    def scan_folders(self, start_path):
        folder_stack = [(start_path, False)]  # (path, is_processed)
        min_size_bytes = self.min_size_gb * (1024 ** 3)
        total_folders = sum(len(dirs) for _, dirs, _ in os.walk(start_path))
        processed = 0

        while folder_stack and self.running:
            current_path, is_processed = folder_stack.pop()

            if is_processed:
                # После обработки всех подпапок вычисляем размер текущей папки
                try:
                    folder_size = self.fast_get_folder_size(current_path)
                    if folder_size >= min_size_bytes:
                        is_parent = any(p.startswith(current_path) for p, _ in self.folder_cache.items())
                        self.folder_cache[current_path] = folder_size
                        size_gb = folder_size / (1024 ** 3)
                        self.folder_found.emit(current_path, size_gb, is_parent)
                except Exception as e:
                    self.error_occurred.emit(str(e))

                processed += 1
                self.progress_updated.emit(processed, total_folders)
                continue

            # Добавляем текущую папку обратно в стек как обработанную
            folder_stack.append((current_path, True))

            # Добавляем подпапки в стек
            try:
                with os.scandir(current_path) as it:
                    for entry in it:
                        if not self.running:
                            return
                        if entry.is_dir() and not (self.skip_hidden and entry.name.startswith('.')):
                            folder_stack.append((entry.path, False))
            except Exception as e:
                self.error_occurred.emit(str(e))

    def fast_get_folder_size(self, path):
        """Быстрое вычисление размера папки с использованием кэша"""
        if path in self.folder_cache:
            return self.folder_cache[path]

        total_size = 0
        try:
            with os.scandir(path) as it:
                for entry in it:
                    if not self.running:
                        return 0
                    try:
                        if entry.is_file():
                            total_size += entry.stat().st_size
                        elif entry.is_dir():
                            total_size += self.fast_get_folder_size(entry.path)
                    except:
                        continue
        except:
            return 0

        return total_size

    def stop(self):
        self.running = False


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.scanner = None
        self.initUI()

    def initUI(self):
        self.setWindowTitle('Большие папки')
        self.setGeometry(100, 100, 900, 650)
        self.setMinimumSize(700, 500)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Path selection
        path_layout = QHBoxLayout()
        self.path_edit = QLineEdit()
        self.path_edit.setPlaceholderText("Выберите папку для анализа")
        path_btn = QPushButton("Обзор...")
        path_btn.clicked.connect(self.select_folder)
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(path_btn)

        # Settings
        settings_layout = QHBoxLayout()
        settings_layout.addWidget(QLabel("Минимальный размер (ГБ):"))
        self.size_spin = QSpinBox()
        self.size_spin.setMinimum(1)
        self.size_spin.setValue(5)
        self.size_spin.setMinimumWidth(120)
        self.size_spin.setMaximumWidth(150)

        self.skip_hidden_check = QCheckBox("Пропускать скрытые папки")
        self.skip_hidden_check.setChecked(True)

        settings_layout.addWidget(self.size_spin)
        settings_layout.addStretch()
        settings_layout.addWidget(self.skip_hidden_check)

        # Total size
        self.total_size_label = QLabel("Общий размер папки: -")
        self.total_size_label.setAlignment(Qt.AlignRight)
        self.total_size_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        # Progress
        self.progress = QProgressBar()
        self.progress.setAlignment(Qt.AlignCenter)

        # Controls
        self.scan_btn = QPushButton("Сканировать")
        self.scan_btn.clicked.connect(self.start_scan)
        self.stop_btn = QPushButton("Остановить")
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_scan)

        # Results
        self.results_list = QListWidget()
        self.results_list.itemDoubleClicked.connect(self.open_folder)
        self.results_list.setStyleSheet("""
            QListWidget {
                font-family: Consolas, monospace;
                font-size: 11px;
            }
        """)

        # Layout assembly
        layout.addLayout(path_layout)
        layout.addLayout(settings_layout)
        layout.addWidget(self.progress)
        layout.addWidget(self.total_size_label)
        layout.addWidget(self.scan_btn)
        layout.addWidget(self.stop_btn)
        layout.addWidget(QLabel("Результаты:"))
        layout.addWidget(self.results_list)

    def select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Выберите папку")
        if folder:
            self.path_edit.setText(folder)

    def start_scan(self):
        if self.scanner and self.scanner.isRunning():
            return

        path = self.path_edit.text()
        if not os.path.isdir(path):
            self.show_error("Укажите корректную папку!")
            return

        self.results_list.clear()
        self.total_size_label.setText("Общий размер папки: вычисляется...")
        self.scanner = FolderScanner(
            path,
            self.size_spin.value(),
            self.skip_hidden_check.isChecked()
        )
        self.scanner.progress_updated.connect(self.update_progress)
        self.scanner.folder_found.connect(self.add_result)
        self.scanner.total_size_calculated.connect(self.show_total_size)
        self.scanner.error_occurred.connect(self.show_error)
        self.scanner.finished.connect(self.scan_finished)

        self.scan_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.scanner.start()

    def stop_scan(self):
        if self.scanner and self.scanner.isRunning():
            self.scanner.stop()
            self.scanner.wait()
        self.scan_finished()

    def scan_finished(self):
        self.scan_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress.setValue(0)

    def update_progress(self, current, total):
        self.progress.setMaximum(total)
        self.progress.setValue(current)
        self.progress.setFormat(f"Обработано: {current}/{total} ({current / total:.1%})")

    def add_result(self, path, size, is_parent):
        item = QListWidgetItem(f"{path} - {size:.2f} ГБ")

        # Подсветка родительских папок серым цветом
        if is_parent:
            item.setForeground(QBrush(QColor(100, 100, 100)))

        self.results_list.addItem(item)

    def show_total_size(self, size_gb):
        self.total_size_label.setText(f"Общий размер папки: {size_gb:.2f} ГБ")

    def show_error(self, message):
        item = QListWidgetItem(f"ОШИБКА: {message}")
        item.setForeground(QBrush(QColor(255, 0, 0)))
        self.results_list.addItem(item)

    def open_folder(self, item):
        path = item.text().split(" - ")[0]
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
        self.stop_scan()
        event.accept()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
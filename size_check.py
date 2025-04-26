import os
import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QProgressBar, QFileDialog,
                             QListWidget, QSpinBox, QSizePolicy)
from PyQt5.QtCore import Qt, QThread, pyqtSignal


"""
Программа помогает очистить место с компа
Иногда где-то глубоко в папках хранятся больше файлы о которых мы даже не знаем
Это первая итерация программы, а значит будут баги и в будущем я буду её улучшать + добавлять новый функционал
В случае, если требуется найти папку не более 5ГБ, а более 10ГБ например, то смотрим в def find_large_folders и меняем min_size_gb на нужное кол-во ГБ
Спасибо за установку! Удачи :D
"""


class FolderScanner(QThread):
    progress_updated = pyqtSignal(int, int)  # current, total
    folder_found = pyqtSignal(str, float)  # path, size
    total_size_calculated = pyqtSignal(float)
    error_occurred = pyqtSignal(str)

    def __init__(self, root_path, min_size_gb):
        super().__init__()
        self.root_path = root_path
        self.min_size_gb = min_size_gb
        self.running = True
  # Запускаем
    def run(self):
        try:
            total_size = self.get_folder_size(self.root_path)
            self.total_size_calculated.emit(total_size / (1024 ** 3))

            all_subfolders = []
            for dirpath, dirnames, filenames in os.walk(self.root_path):
                if not self.running:
                    return
                for dirname in dirnames:
                    full_path = os.path.join(dirpath, dirname)
                    all_subfolders.append(full_path)

            total = len(all_subfolders)
            for i, folder in enumerate(all_subfolders):
                if not self.running:
                    return
                try:
                    folder_size = self.get_folder_size(folder)
                    if folder_size >= self.min_size_gb * (1024 ** 3):
                        size_gb = folder_size / (1024 ** 3)
                        self.folder_found.emit(folder, size_gb)
                except Exception as e:
                    self.error_occurred.emit(str(e))
                self.progress_updated.emit(i + 1, total)

        except Exception as e:
            self.error_occurred.emit(str(e))

    def get_folder_size(self, folder_path):
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(folder_path):
            if not self.running:
                return 0
            for filename in filenames:
                file_path = os.path.join(dirpath, filename)
                if os.path.exists(file_path):
                    try:
                        total_size += os.path.getsize(file_path)
                    except (OSError, PermissionError):
                        continue
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
        self.setGeometry(100, 100, 800, 600)
        self.setMinimumSize(600, 400)

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
        settings_layout.addWidget(self.size_spin)
        settings_layout.addStretch()

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
        self.scanner = FolderScanner(path, self.size_spin.value())
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
        self.progress.setFormat(f"Обработано: {current}/{total} ({current/total:.1%})")

    def add_result(self, path, size):
        self.results_list.addItem(f"{path} - {size:.2f} ГБ")

    def show_total_size(self, size_gb):
        self.total_size_label.setText(f"Общий размер папки: {size_gb:.2f} ГБ")

    def show_error(self, message):
        self.results_list.addItem(f"ОШИБКА: {message}")

    def closeEvent(self, event):
        self.stop_scan()
        event.accept()

#  Запуск
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
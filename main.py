import sys
import os
import importlib.util
import glob

from PyQt5.QtWidgets import (
    QApplication, QWidget, QHBoxLayout, QVBoxLayout, QSplitter,
    QPushButton, QFileDialog, QTreeView, QLabel, QTabWidget, QMenuBar, QAction
)
from PyQt5.QtCore import Qt, QDir, QSettings
from PyQt5.QtGui import QFontDatabase, QFont
from PyQt5.QtWidgets import QFileSystemModel

import json_viewer
from plugins_manager import PluginsManagerDialog

# ====== Loader pluginów (foldery z plikiem {plugin}/{plugin}.py) ======
def load_plugins(main_window, plugins_folder="Plugins"):
    enabled = set()
    enabled_file = os.path.join(plugins_folder, "plugins_enabled.txt")
    try:
        with open(enabled_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    enabled.add(line)
    except FileNotFoundError:
        print("Brak plugins_enabled.txt – żadna wtyczka nie zostanie załadowana.")
        return

    for folder_name in enabled:
        plugin_folder = os.path.join(plugins_folder, folder_name)
        plugin_file = os.path.join(plugin_folder, f"{folder_name}.py")
        if not os.path.isdir(plugin_folder) or not os.path.isfile(plugin_file):
            print(f"Folder/plugin '{folder_name}' nie istnieje lub brak {folder_name}.py")
            continue
        spec = importlib.util.spec_from_file_location(folder_name, plugin_file)
        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
            # Rozpoznawanie nagłówka
            if (getattr(module, "PLUGIN_OK", False)
                and hasattr(module, "PLUGIN_NAME")
                and hasattr(module, "PLUGIN_DESCRIPTION")
                and hasattr(module, "PLUGIN_VERSION")
                and hasattr(module, "register_plugin")):
                module.register_plugin(main_window)
                print(f"Załadowano wtyczkę: {module.PLUGIN_NAME} v{module.PLUGIN_VERSION}")
            else:
                print(f"Wtyczka {folder_name} pominięta (brak nagłówka lub register_plugin).")
        except Exception as e:
            print(f"Błąd ładowania wtyczki {folder_name}: {e}")

# ====== Główna aplikacja ======

LAST_FOLDER_KEY = "last_folder"

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("D2R JSON Language Viewer – Eksplorer + Edytor")
        self.resize(1280, 800)

        self.settings = QSettings("d2r_json_viewer", "d2r_json_viewer")

        main_layout = QHBoxLayout(self)

        # Dodaj menu
        menubar = QMenuBar(self)
        options_menu = menubar.addMenu("Opcje")
        plugins_menu = menubar.addMenu("Pluginy")  # <-- NOWE MENU
        self.plugins_menu = plugins_menu           # <-- przechowaj referencję dla pluginów
        plugins_action = QAction("Wtyczki", self)
        plugins_action.triggered.connect(self.show_plugins_manager)
        options_menu.addAction(plugins_action)
        main_layout.setMenuBar(menubar)

        self.splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(self.splitter)

        # LEWY PANEL: DRZEWO FOLDERÓW/PLIKÓW
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        self.choose_folder_btn = QPushButton("Wybierz folder")
        self.choose_folder_btn.clicked.connect(self.choose_folder)
        left_layout.addWidget(self.choose_folder_btn)

        # Label do ścieżki folderu
        self.folder_path_label = QLabel("Brak wybranego folderu")
        self.folder_path_label.setWordWrap(True)
        left_layout.addWidget(self.folder_path_label)

        self.fs_model = QFileSystemModel()
        self.fs_model.setNameFilters(["*.json"])
        self.fs_model.setNameFilterDisables(False)

        self.tree = QTreeView()
        self.tree.setModel(self.fs_model)
        self.tree.hide()
        self.tree.doubleClicked.connect(self.on_file_double_clicked)
        left_layout.addWidget(self.tree)
        self.splitter.addWidget(left_widget)
        left_widget.setMinimumWidth(300)

        # PRAWY PANEL: TABY Z EDYTORAMI
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(True)
        self.tabs.tabCloseRequested.connect(self.close_tab)
        self.splitter.addWidget(self.tabs)

        # Po starcie: próbuj wczytać ostatni folder
        last_folder = self.settings.value(LAST_FOLDER_KEY, "")
        if last_folder and os.path.isdir(last_folder):
            self.set_folder(last_folder)
        else:
            self.tree.hide()
            info = QLabel("Wybierz folder z plikami JSON")
            left_layout.addWidget(info)
            self.info_label = info

        # Załaduj pluginy po zbudowaniu GUI!
        load_plugins(self)

    def show_plugins_manager(self):
        dlg = PluginsManagerDialog(self)
        dlg.exec_()

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Wybierz folder z plikami JSON")
        if folder:
            self.set_folder(folder)
            self.settings.setValue(LAST_FOLDER_KEY, folder)

    def set_folder(self, folder):
        if hasattr(self, "info_label"):
            self.info_label.hide()
        self.fs_model.setRootPath(folder)
        self.tree.setRootIndex(self.fs_model.index(folder))
        self.tree.show()
        self.tree.header().setSectionResizeMode(0, self.tree.header().ResizeToContents)
        self.folder_path_label.setText(f"Ścieżka folderu: <b>{folder}</b>")

    def on_file_double_clicked(self, index):
        path = self.fs_model.filePath(index)
        if path.endswith(".json"):
            # Sprawdź, czy plik jest już otwarty w zakładce
            for i in range(self.tabs.count()):
                widget = self.tabs.widget(i)
                if hasattr(widget, 'json_path') and widget.json_path == path:
                    self.tabs.setCurrentIndex(i)
                    return
            # Jeśli nie - otwórz nową zakładkę
            viewer = json_viewer.JsonLangViewer()
            viewer.load_json(path)
            viewer.json_path = path
            filename = os.path.basename(path)
            self.tabs.addTab(viewer, filename)
            self.tabs.setCurrentWidget(viewer)

    def close_tab(self, index):
        self.tabs.removeTab(index)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    font_id = QFontDatabase.addApplicationFont("exocetblizzardot-medium.otf")
    if font_id != -1:
        font_family = QFontDatabase.applicationFontFamilies(font_id)[0]
        print(f"Używana czcionka: {font_family} (D2R)")
        app.setFont(QFont(font_family, 12))
        import json_viewer
        json_viewer.D2R_FONT_NAME = font_family
    else:
        print("Nie udało się załadować czcionki D2R – używana będzie czcionka systemowa.")
        json_viewer.D2R_FONT_NAME = "Sans Serif"

    window = MainWindow()
    window.show()
    # Ustaw proporcje paneli na 20% (lewy), 80% (prawy)
    window_width = window.width()
    left = int(window_width * 0.2)
    right = int(window_width * 0.8)
    window.splitter.setSizes([left, right])
    sys.exit(app.exec_())
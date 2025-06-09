PLUGIN_NAME = "Znajdź zależności"
PLUGIN_VERSION = "1.3"
PLUGIN_DESCRIPTION = "Skanuje folder moda (.mpq) i wyszukuje po ID/Key we wszystkich plikach JSON oraz TXT. Zapamiętuje ostatnio używany mod. Wyniki pokazują nr linii!"
PLUGIN_AUTHOR = "Precell i ChatGPT"
PLUGIN_OK = True

from PyQt5.QtWidgets import QMenuBar, QAction
import os
import json
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QPushButton, QLabel, QListWidget, QListWidgetItem, QHBoxLayout, QFileDialog, QMessageBox
)
from PyQt5.QtCore import Qt, QSettings

class DependencyFinderDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Znajdź zależności w modzie")
        self.setMinimumWidth(620)

        layout = QVBoxLayout(self)

        # Zapamiętywanie ostatniego folderu moda przez QSettings
        self.settings = QSettings("d2r_json_viewer", "d2r_json_viewer")
        last_mod = self.settings.value("last_mod_folder", "")
        self.mod_folder = last_mod if last_mod and os.path.isdir(last_mod) else None

        folder_row = QHBoxLayout()
        self.choose_folder_btn = QPushButton("Wybierz mod (.mpq)")
        self.choose_folder_btn.clicked.connect(self.choose_folder)
        folder_row.addWidget(self.choose_folder_btn)
        self.folder_label = QLabel()
        folder_row.addWidget(self.folder_label)
        layout.addLayout(folder_row)

        if self.mod_folder:
            self.folder_label.setText(f"Mod: <b>{os.path.basename(self.mod_folder)}</b>")
        else:
            self.folder_label.setText("Brak wybranego folderu moda")

        # Pola do wyszukiwania
        input_layout = QHBoxLayout()
        self.id_input = QLineEdit()
        self.id_input.setPlaceholderText("ID (np. 12345)")
        input_layout.addWidget(self.id_input)
        self.key_input = QLineEdit()
        self.key_input.setPlaceholderText("Key (np. someKey)")
        input_layout.addWidget(self.key_input)
        layout.addLayout(input_layout)

        self.search_btn = QPushButton("Szukaj")
        self.search_btn.clicked.connect(self.do_search)
        layout.addWidget(self.search_btn)

        self.result_label = QLabel("")
        layout.addWidget(self.result_label)

        self.results_list = QListWidget()
        self.results_list.setSelectionMode(QListWidget.ExtendedSelection)
        layout.addWidget(self.results_list)

    def choose_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Wybierz folder moda (.mpq)")
        if folder and folder.lower().endswith('.mpq'):
            self.mod_folder = folder
            self.settings.setValue("last_mod_folder", folder)
            self.folder_label.setText(f"Mod: <b>{os.path.basename(folder)}</b>")
        else:
            QMessageBox.warning(self, "Błąd", "Folder nie ma rozszerzenia .mpq!")
            self.mod_folder = None
            self.folder_label.setText("Brak wybranego folderu moda")

    def do_search(self):
        self.results_list.clear()
        self.result_label.setText("")
        search_id = self.id_input.text().strip()
        search_key = self.key_input.text().strip()
        if not self.mod_folder:
            self.result_label.setText("Najpierw wybierz folder moda (.mpq)")
            return
        if not search_id and not search_key:
            self.result_label.setText("Wpisz ID lub Key (lub oba) do wyszukania!")
            return

        found = []
        for root, dirs, files in os.walk(self.mod_folder):
            for filename in files:
                path = os.path.join(root, filename)
                rel_path = os.path.relpath(path, self.mod_folder)
                # JSON — teraz 100% pewne szukanie numeru linii!
                if filename.lower().endswith(".json"):
                    try:
                        with open(path, encoding="utf-8-sig") as f:
                            text_lines = f.readlines()
                        with open(path, encoding="utf-8-sig") as f:
                            data = json.load(f)
                        for i, entry in enumerate(data):
                            match = False
                            idstr = str(entry.get("id", ""))
                            keystr = str(entry.get("Key", ""))
                            if search_id and idstr == search_id:
                                match = True
                            if search_key and keystr == search_key:
                                match = True
                            if match:
                                # Szukaj linii zawierającej id lub key
                                line_no = "?"
                                search_terms = []
                                if search_id:
                                    search_terms.append(f'"id": {idstr}')
                                if search_key:
                                    search_terms.append(f'"Key": "{keystr}"')
                                for idx, line in enumerate(text_lines):
                                    if any(term in line for term in search_terms):
                                        line_no = idx + 1
                                        break
                                found.append(f"{rel_path} [JSON, linia {line_no}]")
                    except Exception:
                        continue

                # TXT
                if filename.lower().endswith(".txt"):
                    try:
                        with open(path, encoding="utf-8") as f:
                            for idx, line in enumerate(f, 1):
                                if (search_id and search_id in line) or (search_key and search_key in line):
                                    found.append(f"{rel_path} [TXT, linia {idx}]")
                    except Exception:
                        continue

        if not found:
            self.result_label.setText("Nie znaleziono zależności dla podanych kryteriów.")
        else:
            self.result_label.setText(f"Znaleziono {len(found)} wyników:")
            for item in found:
                self.results_list.addItem(QListWidgetItem(item))

def register_plugin(main_window):
    def open_dialog():
        dlg = DependencyFinderDialog(main_window)
        dlg.exec_()
    menubar = main_window.findChild(QMenuBar)
    if menubar:
        options_menu = None
        for action in menubar.actions():
            if action.text() == "Opcje":
                options_menu = action.menu()
        if options_menu:
            dep_action = QAction("Znajdź zależności w modzie", main_window)
            dep_action.triggered.connect(open_dialog)
            options_menu.addAction(dep_action)
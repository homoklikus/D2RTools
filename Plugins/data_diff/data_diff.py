PLUGIN_NAME = "Data Diff"
PLUGIN_VERSION = "0.8"
PLUGIN_DESCRIPTION = "Porównuje dwa foldery data – wykrywa zmiany plików i umożliwia diff TXT/JSON w tabelce (obsługa JSON: dict & lista)."
PLUGIN_AUTHOR = "Precell & ChatGPT"
PLUGIN_OK = True

import os
import json
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QFileDialog,
    QTableWidget, QTableWidgetItem, QWidget, QHeaderView, QComboBox, QLineEdit, QSpacerItem, QSizePolicy
)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QColor

ITEMS_PER_PAGE = 100

def register_plugin(main_window):
    if hasattr(main_window, "plugins_menu"):
        main_window.plugins_menu.addAction(
            PLUGIN_NAME,
            lambda: show_data_diff_dialog(main_window)
        )

def show_data_diff_dialog(parent):
    dlg = DataDiffDialog(parent)
    dlg.exec_()

def get_friendly_folder_name(folder_path):
    if not folder_path:
        return ""
    folder = os.path.normpath(folder_path)
    base = os.path.basename(folder)
    if base.lower() == "data":
        return os.path.basename(os.path.dirname(folder))
    return base

class DataDiffDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Data Diff – Porównywarka folderów data")
        self.setMinimumSize(1000, 620)
        layout = QVBoxLayout(self)

        self.settings = QSettings("d2rtools", "data_diff_plugin")
        self.org_folder = self.settings.value("org_folder", "")
        self.mod_folder = self.settings.value("mod_folder", "")

        self.label_info = QLabel(
            "Wybierz dwa foldery do porównania (np. mod/data vs oryginalny data lub dwa różne mody)."
        )
        layout.addWidget(self.label_info)

        folder_row = QHBoxLayout()
        self.btn_org = QPushButton("Wybierz folder po lewej")
        self.btn_mod = QPushButton("Wybierz folder po prawej")
        self.lbl_org = QLabel("")
        self.lbl_mod = QLabel("")
        folder_row.addWidget(self.btn_org)
        folder_row.addWidget(self.lbl_org)
        folder_row.addWidget(self.btn_mod)
        folder_row.addWidget(self.lbl_mod)
        layout.addLayout(folder_row)

        self.btn_org.clicked.connect(self.choose_org)
        self.btn_mod.clicked.connect(self.choose_mod)

        filters_row = QHBoxLayout()
        filters_row.addWidget(QLabel("Typ zmiany:"))
        self.type_filter = QComboBox()
        self.type_filter.addItems(["Wszystko", "Nowy plik", "Podmieniony"])
        filters_row.addWidget(self.type_filter)

        filters_row.addWidget(QLabel("Typ pliku:"))
        self.ext_filter = QComboBox()
        self.ext_filter.addItems(["Wszystko", ".txt", ".json", ".bin", ".d2i", ".sprite", ".png", ".webp", ".md", ".ds1"])
        filters_row.addWidget(self.ext_filter)

        filters_row.addWidget(QLabel("Szukaj:"))
        self.search_box = QLineEdit()
        filters_row.addWidget(self.search_box)

        filters_row.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        layout.addLayout(filters_row)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Typ zmiany", "Ścieżka pliku", "Szczegóły"])
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table.setSortingEnabled(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self.table)

        self.page_row = QHBoxLayout()
        self.btn_prev = QPushButton("<< Poprzednia")
        self.btn_next = QPushButton("Następna >>")
        self.lbl_page = QLabel("Strona 1/1")
        self.btn_prev.clicked.connect(self.prev_page)
        self.btn_next.clicked.connect(self.next_page)
        self.page_row.addWidget(self.btn_prev)
        self.page_row.addWidget(self.lbl_page)
        self.page_row.addWidget(self.btn_next)
        layout.addLayout(self.page_row)
        self.btn_prev.setEnabled(False)
        self.btn_next.setEnabled(False)

        self.all_changes = []
        self.filtered_changes = []
        self.current_page = 1

        self.type_filter.currentIndexChanged.connect(self.apply_filters)
        self.ext_filter.currentIndexChanged.connect(self.apply_filters)
        self.search_box.textChanged.connect(self.apply_filters)

        self.table.cellDoubleClicked.connect(self.preview_file)
        self.table.installEventFilter(self)

        self.update_folder_labels()
        if self.org_folder and self.mod_folder:
            self.try_compare()

    def eventFilter(self, obj, event):
        if obj is self.table:
            if event.type() == event.MouseButtonDblClick:
                index = self.table.indexAt(event.pos())
                row, col = index.row(), index.column()
                self.preview_file(row, col)
                return True
        return super().eventFilter(obj, event)

    def choose_org(self):
        folder = QFileDialog.getExistingDirectory(self, "Wybierz folder po lewej (baza)")
        if folder:
            self.org_folder = folder
            self.settings.setValue("org_folder", self.org_folder)
            self.update_folder_labels()
            if self.mod_folder:
                self.try_compare()

    def choose_mod(self):
        folder = QFileDialog.getExistingDirectory(self, "Wybierz folder po prawej (mod)")
        if folder:
            self.mod_folder = folder
            self.settings.setValue("mod_folder", self.mod_folder)
            self.update_folder_labels()
            if self.org_folder:
                self.try_compare()

    def update_folder_labels(self):
        org_name = get_friendly_folder_name(self.org_folder)
        mod_name = get_friendly_folder_name(self.mod_folder)
        self.lbl_org.setText(f"<b>{org_name}</b>")
        self.lbl_mod.setText(f"<b>{mod_name}</b>")

        if self.org_folder and self.mod_folder:
            self.label_info.setText(
                f"<b>Załadowane foldery:</b><br>"
                f"Lewa strona: <b>{org_name}</b> ({self.org_folder})<br>"
                f"Prawa strona: <b>{mod_name}</b> ({self.mod_folder})"
            )
        else:
            self.label_info.setText(
                "Wybierz dwa foldery do porównania (np. mod/data vs oryginalny data lub dwa różne mody)."
            )

    def try_compare(self):
        self.all_changes = compare_data_folders(self.org_folder, self.mod_folder)
        self.apply_filters()

    def apply_filters(self):
        typ = self.type_filter.currentText()
        ext = self.ext_filter.currentText()
        search = self.search_box.text().lower().strip()
        results = []
        for t, path, info in self.all_changes:
            if typ != "Wszystko" and t != typ:
                continue
            if ext != "Wszystko" and not path.lower().endswith(ext):
                continue
            if search and search not in path.lower() and search not in (info or "").lower():
                continue
            results.append((t, path, info))
        self.filtered_changes = results
        self.current_page = 1
        self.show_page()

    def show_page(self):
        total = len(self.filtered_changes)
        pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
        self.lbl_page.setText(f"Strona {self.current_page}/{pages}")
        self.btn_prev.setEnabled(self.current_page > 1)
        self.btn_next.setEnabled(self.current_page < pages)

        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        start = (self.current_page - 1) * ITEMS_PER_PAGE
        end = min(start + ITEMS_PER_PAGE, total)
        for typ, path, info in self.filtered_changes[start:end]:
            row = self.table.rowCount()
            self.table.insertRow(row)
            typ_item = QTableWidgetItem(typ)
            if typ == "Nowy plik":
                typ_item.setForeground(Qt.green)
            elif typ == "Podmieniony":
                typ_item.setForeground(Qt.darkYellow)
            self.table.setItem(row, 0, typ_item)
            self.table.setItem(row, 1, QTableWidgetItem(path))
            self.table.setItem(row, 2, QTableWidgetItem(info or ""))
        self.table.setSortingEnabled(True)

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1
            self.show_page()

    def next_page(self):
        total = len(self.filtered_changes)
        pages = max(1, (total + ITEMS_PER_PAGE - 1) // ITEMS_PER_PAGE)
        if self.current_page < pages:
            self.current_page += 1
            self.show_page()

    def preview_file(self, row, column):
        typ_item = self.table.item(row, 0)
        path_item = self.table.item(row, 1)
        if not typ_item or not path_item:
            return
        rel_path = path_item.text()
        if not (rel_path.lower().endswith('.txt') or rel_path.lower().endswith('.json')):
            return
        org_file = os.path.join(self.org_folder, rel_path)
        mod_file = os.path.join(self.mod_folder, rel_path)
        if not (os.path.isfile(org_file) and os.path.isfile(mod_file)):
            return
        DiffTablePopup(org_file, mod_file, self).exec_()

class DiffTablePopup(QDialog):
    def __init__(self, org_file, mod_file, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Porównanie plików")
        self.setMinimumSize(1000, 650)
        self.setWindowModality(Qt.ApplicationModal)  # wymusza focus nawet na sudo

        layout = QVBoxLayout(self)
        name = os.path.basename(org_file)
        layout.addWidget(QLabel(f"<b>Plik:</b> {name}"))
        table = QTableWidget(0, 2)
        table.setHorizontalHeaderLabels(["Oryginał", "Mod"])
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        table.setEditTriggers(QTableWidget.NoEditTriggers)

        if org_file.lower().endswith('.json'):
            try:
                with open(org_file, "r", encoding="utf-8-sig") as f1:
                    try:
                        org_data = json.load(f1)
                    except Exception:
                        org_data = None
                with open(mod_file, "r", encoding="utf-8-sig") as f2:
                    try:
                        mod_data = json.load(f2)
                    except Exception:
                        mod_data = None

                if isinstance(org_data, list) and isinstance(mod_data, list):
                    maxlen = max(len(org_data), len(mod_data))
                    for i in range(maxlen):
                        v1 = org_data[i] if i < len(org_data) else "<brak>"
                        v2 = mod_data[i] if i < len(mod_data) else "<brak>"
                        row = table.rowCount()
                        table.insertRow(row)
                        if isinstance(v1, dict):
                            txt1 = ", ".join(f"{k}:{v1[k]}" for k in v1)
                        else:
                            txt1 = str(v1)
                        if isinstance(v2, dict):
                            txt2 = ", ".join(f"{k}:{v2[k]}" for k in v2)
                        else:
                            txt2 = str(v2)
                        item1 = QTableWidgetItem(txt1)
                        item2 = QTableWidgetItem(txt2)
                        if v1 != v2:
                            item1.setBackground(QColor("#ffd6d6"))
                            item2.setBackground(QColor("#d6ffd6"))
                        table.setItem(row, 0, item1)
                        table.setItem(row, 1, item2)
                elif isinstance(org_data, dict) and isinstance(mod_data, dict):
                    all_keys = set(org_data.keys()) | set(mod_data.keys())
                    for key in sorted(all_keys):
                        v1 = org_data.get(key, "<brak>")
                        v2 = mod_data.get(key, "<brak>")
                        row = table.rowCount()
                        table.insertRow(row)
                        item1 = QTableWidgetItem(f"{key}: {v1}")
                        item2 = QTableWidgetItem(f"{key}: {v2}")
                        if v1 != v2:
                            item1.setBackground(QColor("#ffd6d6"))
                            item2.setBackground(QColor("#d6ffd6"))
                        table.setItem(row, 0, item1)
                        table.setItem(row, 1, item2)
                else:
                    table.setRowCount(1)
                    table.setItem(0, 0, QTableWidgetItem("JSON nie jest dict/list"))
                    table.setItem(0, 1, QTableWidgetItem("JSON nie jest dict/list"))
            except Exception as e:
                table.setRowCount(1)
                table.setItem(0, 0, QTableWidgetItem("Błąd wczytywania JSON"))
                table.setItem(0, 1, QTableWidgetItem(str(e)))
        else:
            try:
                with open(org_file, "r", encoding="utf-8-sig") as f1:
                    org_lines = f1.readlines()
                with open(mod_file, "r", encoding="utf-8-sig") as f2:
                    mod_lines = f2.readlines()
            except Exception as e:
                table.setRowCount(1)
                table.setItem(0, 0, QTableWidgetItem("Błąd wczytywania TXT"))
                table.setItem(0, 1, QTableWidgetItem(str(e)))
                layout.addWidget(table)
                btn = QPushButton("Zamknij")
                btn.clicked.connect(self.accept)
                layout.addWidget(btn)
                return
            maxlen = max(len(org_lines), len(mod_lines))
            for i in range(maxlen):
                l1 = org_lines[i].rstrip() if i < len(org_lines) else ""
                l2 = mod_lines[i].rstrip() if i < len(mod_lines) else ""
                row = table.rowCount()
                table.insertRow(row)
                item1 = QTableWidgetItem(l1)
                item2 = QTableWidgetItem(l2)
                if l1 != l2:
                    item1.setBackground(QColor("#ffd6d6"))
                    item2.setBackground(QColor("#d6ffd6"))
                table.setItem(row, 0, item1)
                table.setItem(row, 1, item2)

        layout.addWidget(table)
        btn = QPushButton("Zamknij")
        btn.clicked.connect(self.accept)
        layout.addWidget(btn)

        self.activateWindow()
        self.raise_()
        self.setFocus()

def compare_data_folders(org_folder, mod_folder):
    changes = []
    org_files = {}
    mod_files = {}
    for root, _, files in os.walk(org_folder):
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), org_folder)
            org_files[rel] = os.path.join(root, f)
    for root, _, files in os.walk(mod_folder):
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), mod_folder)
            mod_files[rel] = os.path.join(root, f)
    for rel_path, mod_path in mod_files.items():
        if rel_path not in org_files:
            changes.append(("Nowy plik", rel_path, ""))
        else:
            try:
                if not file_equals(mod_path, org_files[rel_path]):
                    changes.append(("Podmieniony", rel_path, "Zmieniona zawartość"))
            except Exception as e:
                changes.append(("Podmieniony?", rel_path, f"Błąd porównania: {e}"))
    return changes

def file_equals(f1, f2):
    with open(f1, "rb") as a, open(f2, "rb") as b:
        return a.read() == b.read()
PLUGIN_NAME = "Data Diff"
PLUGIN_VERSION = "1.8"
PLUGIN_DESCRIPTION = "Porównuje dwa foldery data: TXT (diff), JSON, sprite, filtry, popupy"
PLUGIN_AUTHOR = "Precell & ChatGPT"
PLUGIN_OK = True

import os
import struct
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QFileDialog,
    QTableWidget, QTableWidgetItem, QWidget, QHeaderView, QComboBox,
    QLineEdit, QSpacerItem, QSizePolicy, QCheckBox, QTextEdit, QFrame
)
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtGui import QColor

from diff_txt_popup import DiffTextPopup
from diff_json_popup import DiffJsonPopup
from diff_sprite_popup import SpriteDiffPopup

ITEMS_PER_PAGE = 100

DIFF_COLOR_ADDED_BG = "#26712b"
DIFF_COLOR_REMOVED_BG = "#8a2121"
DIFF_COLOR_CHANGED_BG = "#7c4700"
DIFF_COLOR_CHANGED_TXT = "#fff"
DIFF_COLOR_NUMBER = "#bbbbbb"

COLOR_ORG_DIFF = QColor("#8a2121")
COLOR_MOD_DIFF = QColor("#26712b")

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

def load_sprite(filename):
    with open(filename, "rb") as f:
        data = f.read()
    if data[0:1] != b"S" or data[3:4] != b"1":
        raise ValueError(f"{filename}: nietypowy nagłówek {data[0:4]}")
    version = struct.unpack_from("<H", data, 4)[0]
    if version != 31:
        raise NotImplementedError("Obsługiwane tylko sprite'y w wersji 31 (RGBA)")
    width = struct.unpack_from("<I", data, 8)[0]
    height = struct.unpack_from("<I", data, 12)[0]
    frame_count = struct.unpack_from("<I", data, 0x14)[0] if len(data) >= 0x18 else 1
    pixels_per_frame = width * height
    frame_size = pixels_per_frame * 4
    offset = 0x28
    if offset + frame_size > len(data):
        raise ValueError("Dane sprite'a są niekompletne")
    from PIL import Image
    img = Image.frombytes("RGBA", (width, height), data[offset:offset+frame_size])
    return img

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
                typ_item.setForeground(QColor("#26712b"))
            elif typ == "Podmieniony":
                typ_item.setForeground(QColor("#7c4700"))
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
        org_file = os.path.join(self.org_folder, rel_path)
        mod_file = os.path.join(self.mod_folder, rel_path)
        org_exists = os.path.isfile(org_file)
        mod_exists = os.path.isfile(mod_file)
        org_name = get_friendly_folder_name(self.org_folder)
        mod_name = get_friendly_folder_name(self.mod_folder)
        if not (org_exists or mod_exists):
            return
        if rel_path.lower().endswith('.sprite'):
            popup = SpriteDiffPopup(org_file if org_exists else None, mod_file if mod_exists else None, self)
            popup.exec_()
            return
        if rel_path.lower().endswith('.txt'):
            DiffTextPopup(
                org_file if org_exists else None,
                mod_file if mod_exists else None,
                self,
                filename=rel_path,
                org_label=org_name,
                mod_label=mod_name
            ).exec_()
            return
        if rel_path.lower().endswith('.json'):
            DiffJsonPopup(
                org_file if org_exists else None,
                mod_file if mod_exists else None,
                self,
                org_label=org_name,
                mod_label=mod_name
            ).exec_()
            return

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
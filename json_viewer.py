import sys
import json
from PyQt5.QtWidgets import (
    QDialog, QPlainTextEdit, QDialogButtonBox,
    QWidget, QVBoxLayout, QPushButton, QTextBrowser, QLabel,
    QScrollArea, QGroupBox, QGridLayout, QLineEdit, QHBoxLayout
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

# Mapowanie kodów kolorów D2R na kolory HTML
D2R_COLOR_MAP = {
    "0": "#FFFFFF",  # ÿc0 – White
    "1": "#FF4D4D",  # ÿc1 – Red
    "2": "#00FF00",  # ÿc2 – Green
    "3": "#6969FF",  # ÿc3 – Blue
    "4": "#C7B377",  # ÿc4 – Light Gold
    "5": "#696969",  # ÿc5 – Grey
    "6": "#000000",  # ÿc6 – Black
    "7": "#D0C27D",  # ÿc7 – Dark Gold
    "8": "#FFA800",  # ÿc8 – Orange
    "9": "#FFFF64",  # ÿc9 – Yellow
    "a": "#008000",  # ÿca – Dark Green
    "b": "#AE00FF",  # ÿcb – Purple
    "c": "#00C800",  # ÿcc – Medium Green
    "A": "#008000",  # ÿcA – Dark Green
    "B": "#AE00FF",  # ÿcB – Purple
    "C": "#00C800",  # ÿcC – Medium Green

    # Przybliżone z obrazu (custom, nieoficjalne kody):
    ";": "#B000B0",  # ÿc; – Purple
    "=": "#E0E0E0",  # ÿc= – White2
    ":": "#004400",  # ÿc: – Dark Green2
    "@": "#FF8800",  # ÿc@ – Orange1
    "D": "#FFD700",  # ÿcD – Gold2
    "E": "#FF0000",  # ÿcE – Health Potion Red
    "F": "#ADD8E6",  # ÿcF – Mana Potion Blue
    "G": "#FF77FF",  # ÿcG – Rejuvenation Pink
    "H": "#B8860B",  # ÿcH – Light Gold2
    "I": "#888888",  # ÿcI – Grey3
    "J": "#FF6600",  # ÿcJ – Orange3
    "K": "#999999",  # ÿcK – Grey2
    "L": "#FFB347",  # ÿcL – Orange4
    "M": "#FFDCA8",  # ÿcM – Light Gold
    "N": "#00FFFF",  # ÿcN – Light Blue
    "O": "#FF69B4",  # ÿcO – Pink
    "P": "#E0BBE4",  # ÿcP – Pale Violet
    "Q": "#00DD00",  # ÿcQ – Bright Green
    "R": "#FFFF00",  # ÿcR – Yellow2
    "S": "#880000",  # ÿcS – Dark Red
    "T": "#ADD8E6",  # ÿcT – Sky Blue
    "U": "#CC0000",  # ÿcU – Rich Red
    "Y": "#AAAAAA"   # ÿcY – Neutral/Quest Grey
}

D2R_FONT_NAME = ""

def format_d2r_text(text):
    if not text:
        return ""
    lines = text.split("\n")[::-1]  # odwróć kolejność linii
    result = ""
    current_color = "#FFFFFF"
    for line in lines:
        i = 0
        while i < len(line):
            if line[i:i+2] == "ÿc" and i + 2 < len(line):
                color_code = line[i+2]
                current_color = D2R_COLOR_MAP.get(color_code, current_color)
                i += 3
            else:
                segment = line[i].replace("%", "%%")
                result += f'<span style="color: {current_color};">{segment}</span>'
                i += 1
        result += "<br>"
    wrapped = f'<div style="font-family: {D2R_FONT_NAME}; font-size: 14pt; text-align: center; background-color: rgba(0, 0, 0, 0.8); padding: 5px; border-radius: 4px;">{result}</div>'
    return wrapped

class JsonLangViewer(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("D2R JSON Language Viewer")
        self.setAcceptDrops(True)
        self.resize(900, 700)

        self.page = 0
        self.entries_per_page = 100
        self.all_data = []
        self.filtered_data = []
        self.current_entries = []

        layout = QVBoxLayout(self)

        # SZUKAJKA
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Szukaj w Key, ID, enUS, plPL...")
        self.search_input.textChanged.connect(self.filter_entries)
        search_layout.addWidget(self.search_input)

        # PAGINACJA - przyciski
        self.prev_button = QPushButton("Poprzednia strona")
        self.next_button = QPushButton("Następna strona")
        self.prev_button.clicked.connect(self.prev_page)
        self.next_button.clicked.connect(self.next_page)
        search_layout.addWidget(self.prev_button)
        search_layout.addWidget(self.next_button)

        layout.addLayout(search_layout)

        self.file_label = QLabel("Brak wczytanego pliku")
        layout.addWidget(self.file_label)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll_content = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll.setWidget(self.scroll_content)
        layout.addWidget(self.scroll)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            urls = event.mimeData().urls()
            if any(url.toLocalFile().endswith(".json") for url in urls):
                event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if path.endswith(".json"):
                self.load_json(path)

    def filter_entries(self):
        query = self.search_input.text().lower()
        # Wyszukiwanie działa na ALL_DATA!
        def matches(entry):
            return any(query in str(entry.get(k, '')).lower()
                       for k in ['Key', 'id', 'enUS', 'plPL'])
        self.filtered_data = [entry for entry in self.all_data if matches(entry)] if query else self.all_data
        self.page = 0
        self.populate_view()

    def load_json(self, path=None):
        if path:
            self.json_path = path
        self.file_label.setText(f"Załadowano plik: {path}")
        try:
            with open(path, encoding="utf-8-sig") as f:
                data = json.load(f)
        except Exception as e:
            print(f"Błąd: {e}")
            return

        self.all_data = data
        self.filtered_data = data
        self.page = 0
        self.populate_view()

    def populate_view(self):
        self.current_entries = []
        for i in reversed(range(self.scroll_layout.count())):
            widget = self.scroll_layout.itemAt(i).widget()
            if widget is not None:
                widget.deleteLater()

        data = self.filtered_data
        start = self.page * self.entries_per_page
        stop = start + self.entries_per_page
        page_entries = data[start:stop]
        if not page_entries:
            l = QLabel("Brak wyników.")
            self.scroll_layout.addWidget(l)
            return

        for entry in page_entries:
            group_box = QGroupBox(f"Key: {entry.get('Key', '')} (ID: {entry.get('id', '')})")
            group_layout = QGridLayout()
            group_layout.setColumnStretch(1, 1)

            for idx, lang in enumerate(["enUS", "plPL"]):
                if lang in entry:
                    label = QLabel(f"{lang}:")
                    browser = QTextBrowser()
                    browser.setFont(QFont(D2R_FONT_NAME, 14))
                    browser.setHtml(format_d2r_text(entry[lang]))
                    browser.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                    browser.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
                    browser.setSizeAdjustPolicy(QTextBrowser.AdjustToContents)
                    browser.setMinimumHeight(10)
                    browser.setMaximumHeight(16777215)
                    browser.document().setTextWidth(browser.viewport().width())
                    doc_height = int(browser.document().size().height()) + 10
                    browser.setMinimumHeight(doc_height)
                    browser.setMaximumHeight(doc_height)

                    edit_button = QPushButton("Edytuj")
                    edit_button.setStyleSheet("color: white; background-color: #444; border: 1px solid #888; padding: 2px;")
                    edit_button.clicked.connect(lambda checked, e=entry, l=lang, b=browser: self.open_edit_dialog(e, l, b))

                    group_layout.addWidget(label, idx, 0, alignment=Qt.AlignTop)
                    group_layout.addWidget(browser, idx, 1)
                    group_layout.addWidget(edit_button, idx, 2, alignment=Qt.AlignTop)

            group_box.setLayout(group_layout)
            self.scroll_layout.addWidget(group_box)
            self.current_entries.append((entry, group_box))

        # Pokaż/ukryj przyciski paginacji zależnie od ilości wpisów
        total = len(self.filtered_data)
        self.prev_button.setEnabled(self.page > 0)
        self.next_button.setEnabled((self.page + 1) * self.entries_per_page < total)

    def next_page(self):
        if (self.page + 1) * self.entries_per_page < len(self.filtered_data):
            self.page += 1
            self.populate_view()

    def prev_page(self):
        if self.page > 0:
            self.page -= 1
            self.populate_view()

    from PyQt5.QtWidgets import QDialog, QPlainTextEdit, QDialogButtonBox

    def open_edit_dialog(self, entry, lang, browser):
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Edytuj {lang}")
        layout = QVBoxLayout(dialog)

        editor = QPlainTextEdit()
        editor.setPlainText(entry[lang])
        editor.setMinimumHeight(200)
        layout.addWidget(editor)

        MAX_LEN = 481
        footer_widget = QWidget()
        footer_layout = QVBoxLayout(footer_widget)
        footer_layout.setContentsMargins(0, 0, 0, 0)
        counter_label = QLabel()
        error_label = QLabel()
        error_label.setStyleSheet("color: red;")
        warn_label = QLabel()
        warn_label.setStyleSheet("color: #FFD600;")  # żółty
        footer_layout.addWidget(counter_label)
        footer_layout.addWidget(error_label)
        footer_layout.addWidget(warn_label)
        layout.addWidget(footer_widget)

        def update_counter():
            text = editor.toPlainText()
            count = len(text) + text.count('\n')
            counter_label.setText(f"{count}/{MAX_LEN}")
            if count > MAX_LEN:
                error_label.setText("Przekroczyłeś dozwoloną liczbę znaków")
            else:
                error_label.setText("")

            lines = text.split('\n')
            warn_lines = []
            for idx, line in enumerate(lines, 1):
                if line.strip() and not line.lstrip().startswith('ÿc'):
                    warn_lines.append(str(idx))
            if warn_lines:
                warn_label.setText(
                    f'Brak kodu koloru w linii/liniach: {", ".join(warn_lines)}'
                )
            else:
                warn_label.setText("")

        editor.textChanged.connect(update_counter)
        update_counter()

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)
        buttons.accepted.connect(lambda: self.save_edit(dialog, editor, entry, lang, browser))
        buttons.rejected.connect(dialog.reject)
        dialog.exec_()

    def save_edit(self, dialog, editor, entry, lang, browser):
        new_text = editor.toPlainText()
        try:
            with open(self.json_path, encoding="utf-8-sig") as f:
                all_data = json.load(f)
            # szukaj po ID i Key
            for obj in all_data:
                if obj.get("id") == entry.get("id") and obj.get("Key") == entry.get("Key"):
                    obj[lang] = new_text
                    break
            with open(self.json_path, "w", encoding="utf-8-sig") as f:
                json.dump(all_data, f, indent=2, ensure_ascii=False)
            self.load_json(self.json_path)  # odśwież wszystko
        except Exception as e:
            print(f"Błąd podczas zapisu: {e}")
        dialog.accept()
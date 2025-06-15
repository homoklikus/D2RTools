import json
import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QSplitter, QWidget,
    QPlainTextEdit, QTextEdit, QSizePolicy, QGridLayout, QHBoxLayout,
    QLineEdit, QPushButton
)
from PyQt5.QtCore import Qt, QRect, QSize
from PyQt5.QtGui import QColor, QPainter, QFont, QTextFormat, QTextCursor, QTextDocument

def read_json_lines(filename):
    if not filename or not os.path.isfile(filename):
        return ["(Brak pliku)"]
    try:
        with open(filename, "r", encoding="utf-8-sig") as f:
            data = json.load(f)
        text = json.dumps(data, ensure_ascii=False, indent=2)
        return text.splitlines()
    except Exception as e:
        return [f"(Błąd wczytywania JSON: {e})"]

def get_line_type(left_line, right_line):
    if left_line is None or left_line == "":
        return 'added'
    if right_line is None or right_line == "":
        return 'removed'
    if left_line != right_line:
        return 'changed'
    return 'equal'

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.code_editor = editor

    def sizeHint(self):
        return QSize(self.code_editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.code_editor.line_number_area_paint_event(event)

class CodeEdit(QPlainTextEdit):
    def __init__(self, lines, highlight_types, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        font = QFont("JetBrains Mono, Consolas, Monospace")
        font.setStyleHint(QFont.Monospace)
        font.setPointSize(10)
        self.setFont(font)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)
        self.setStyleSheet("background: #23272e; color: #d4d4d4; border:0;")
        self.setPlainText("\n".join(lines))

        self.line_number_area = LineNumberArea(self)
        self.max_line_digits = 2  # Default, will be calculated and updated

        # --- KLUCZOWA ZMIANA: inicjalizujemy oba atrybuty przed highlight_current_line ---
        self.diff_selections = []
        self.search_selections = []
        self.search_matches = []
        self.current_search_index = -1
        self.last_search = ""

        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.update_line_number_area_width(0)
        self.highlight_current_line()

        self.highlight_types = highlight_types
        self.highlight_diff_lines()

    def line_number_area_width(self):
        digits = max(self.max_line_digits, len(str(self.blockCount())))
        fm = self.fontMetrics()
        # Bardzo duży zapas: +40 pikseli i szeroki padding
        space = 40 + fm.horizontalAdvance('9') * digits
        return space

    def set_max_line_digits(self, digits):
        self.max_line_digits = digits
        self.update_line_number_area_width(0)
        self.line_number_area.update()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(
            QRect(cr.left(), cr.top(), self.line_number_area_width(), cr.height())
        )

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), self.line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def line_number_area_paint_event(self, event):
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#20232a"))
        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())
        font_metrics = self.fontMetrics()
        width = self.line_number_area.width()
        left_padding = 24
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                painter.setPen(QColor("#666"))
                painter.drawText(left_padding, top, width - left_padding - 2, font_metrics.height(),
                                 Qt.AlignRight | Qt.AlignVCenter, number)
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            blockNumber += 1

    def highlight_current_line(self):
        self.setExtraSelections(self.diff_selections + self.search_selections)

    def highlight_diff_lines(self):
        # Ustaw extraSelections dla linii typu removed/added/changed
        extraSelections = []
        color_map = {
            "removed": QColor("#8a2121"),
            "added": QColor("#26712b"),
            "changed": QColor("#7c4700"),
        }
        for i, typ in enumerate(self.highlight_types):
            if typ in color_map:
                selection = QTextEdit.ExtraSelection()
                selection.format.setBackground(color_map[typ])
                selection.format.setForeground(QColor("#fff"))
                selection.format.setProperty(QTextFormat.FullWidthSelection, True)
                cursor = QTextCursor(self.document().findBlockByLineNumber(i))
                selection.cursor = cursor
                extraSelections.append(selection)
        self.diff_selections = extraSelections
        self.highlight_current_line()

    def search_text(self, text, forward=True, from_current=True):
        # Zwraca liczbę trafień i aktualny indeks
        if not text:
            self.clear_search()
            return 0, -1
        doc = self.document()
        matches = []
        tc = QTextCursor(doc)
        flags = QTextDocument.FindFlags()
        startpos = 0
        if from_current and self.current_search_index >= 0 and len(self.search_matches) > 0:
            if forward:
                startpos = self.search_matches[self.current_search_index][0].selectionEnd()
            else:
                startpos = self.search_matches[self.current_search_index][0].selectionStart() - 1
        tc.setPosition(0)
        while True:
            match = doc.find(text, tc, flags)
            if match.isNull():
                break
            matches.append((QTextCursor(match), match.selectionStart(), match.selectionEnd()))
            tc.setPosition(match.selectionEnd())
        self.search_matches = matches
        if not matches:
            self.search_selections = []
            self.current_search_index = -1
            self.highlight_current_line()
            return 0, -1
        self.update_search_selection(0)
        return len(matches), 0

    def update_search_selection(self, active_idx):
        selections = []
        for i, (cursor, start, end) in enumerate(self.search_matches):
            sel = QTextEdit.ExtraSelection()
            if i == active_idx:
                sel.format.setBackground(QColor("#ff9800"))  # pomarańczowy
            else:
                sel.format.setBackground(QColor("#fff176"))  # żółty
            sel.cursor = cursor
            selections.append(sel)
        self.search_selections = selections
        self.current_search_index = active_idx if selections else -1
        self.highlight_current_line()
        if selections:
            self.setTextCursor(self.search_matches[active_idx][0])

    def search_next(self, text):
        if not text:
            self.clear_search()
            return
        if text != self.last_search:
            self.last_search = text
            self.search_text(text)
            return
        if not self.search_matches:
            return
        idx = (self.current_search_index + 1) % len(self.search_matches)
        self.update_search_selection(idx)

    def search_prev(self, text):
        if not text:
            self.clear_search()
            return
        if text != self.last_search:
            self.last_search = text
            self.search_text(text)
            return
        if not self.search_matches:
            return
        idx = (self.current_search_index - 1 + len(self.search_matches)) % len(self.search_matches)
        self.update_search_selection(idx)

    def clear_search(self):
        self.search_selections = []
        self.search_matches = []
        self.current_search_index = -1
        self.last_search = ""
        self.highlight_current_line()

class CodePanel(QWidget):
    def __init__(self, lines, highlight_types, title=""):
        super().__init__()
        grid = QGridLayout(self)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setSpacing(0)

        header = QLabel(f"<b>{title}</b>")
        header.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        header.setStyleSheet("background: #1e1e1e; color: #b5cea8; padding: 4px; border-bottom:1px solid #333;")
        grid.addWidget(header, 0, 0, 1, 2)

        self.editor = CodeEdit(lines, highlight_types, self)
        max_digits = len(str(max(1, len(lines))))
        self.editor.set_max_line_digits(max_digits)
        self.editor.setMinimumWidth(340)
        self.editor.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        grid.addWidget(self.editor.line_number_area, 1, 0, 1, 1)
        grid.addWidget(self.editor, 1, 1, 1, 1)
        grid.setColumnStretch(0, 0)
        grid.setColumnStretch(1, 1)
        grid.setRowStretch(1, 1)

class DiffJsonPopup(QDialog):
    def __init__(self, org_file, mod_file, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Podgląd JSON z podświetleniem różnic i wyszukiwarką")
        self.setMinimumSize(1450, 950)
        self.setWindowModality(Qt.ApplicationModal)

        layout = QVBoxLayout(self)
        name = os.path.basename(org_file) if org_file else os.path.basename(mod_file)
        layout.addWidget(QLabel(f"<b>Plik:</b> {name}"))

        # WYSZUKIWARKA
        search_row = QWidget()
        search_row_layout = QHBoxLayout(search_row)
        search_row_layout.setContentsMargins(0, 6, 0, 6)
        search_row_layout.setSpacing(4)
        search_label = QLabel("Szukaj:")
        search_label.setStyleSheet("color: #ccc; font-size: 13px;")
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Wpisz szukany tekst…")
        self.search_edit.setMinimumWidth(180)
        self.search_edit.setStyleSheet("background: #181818; color: #e0e0e0; border-radius: 4px; padding: 3px 7px; font-size: 13px;")
        self.search_next_btn = QPushButton("Szukaj dalej")
        self.search_prev_btn = QPushButton("Poprzedni")
        self.search_status = QLabel("")
        self.search_status.setStyleSheet("color: #aaa; font-size: 12px; padding-left: 10px;")

        search_row_layout.addWidget(search_label)
        search_row_layout.addWidget(self.search_edit)
        search_row_layout.addWidget(self.search_next_btn)
        search_row_layout.addWidget(self.search_prev_btn)
        search_row_layout.addWidget(self.search_status)
        search_row_layout.addStretch(1)
        layout.addWidget(search_row)

        # LEGEND
        legend = QWidget()
        legend_layout = QHBoxLayout(legend)
        legend_layout.setContentsMargins(10, 10, 10, 10)
        legend_layout.setSpacing(18)

        legend_labels = [
            ("Dodane do moda", "#26712b"),
            ("Usunięte z moda", "#8a2121"),
            ("Zmienione względem oryginału", "#7c4700"),
        ]
        for text, color in legend_labels:
            color_box = QLabel()
            color_box.setFixedSize(32, 18)
            color_box.setStyleSheet(f"background: {color}; border:1px solid #444; border-radius:3px;")
            leglabel = QLabel(text)
            leglabel.setStyleSheet("color: #ddd; font-size: 12px; padding-left:4px;")
            block = QWidget()
            block_layout = QHBoxLayout(block)
            block_layout.setContentsMargins(2, 0, 2, 0)
            block_layout.setSpacing(4)
            block_layout.addWidget(color_box)
            block_layout.addWidget(leglabel)
            legend_layout.addWidget(block)
        legend_layout.addStretch(1)
        layout.addWidget(legend)

        left_lines = read_json_lines(org_file)
        right_lines = read_json_lines(mod_file)
        max_lines = max(len(left_lines), len(right_lines))
        left_lines += [""] * (max_lines - len(left_lines))
        right_lines += [""] * (max_lines - len(right_lines))

        left_types = []
        right_types = []
        for l, r in zip(left_lines, right_lines):
            typ = get_line_type(l, r)
            left_types.append("removed" if typ == "removed" else ("changed" if typ == "changed" else None))
            right_types.append("added" if typ == "added" else ("changed" if typ == "changed" else None))

        max_digits = len(str(max_lines))

        splitter = QSplitter(Qt.Horizontal)
        self.left_panel = CodePanel(left_lines, left_types, "Oryginał")
        self.right_panel = CodePanel(right_lines, right_types, "Mod")
        self.left_panel.editor.set_max_line_digits(max_digits)
        self.right_panel.editor.set_max_line_digits(max_digits)

        splitter.addWidget(self.left_panel)
        splitter.addWidget(self.right_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter, 1)

        # Synchronizacja scrolla
        self.left_panel.editor.verticalScrollBar().valueChanged.connect(
            lambda v: self.right_panel.editor.verticalScrollBar().setValue(v)
        )
        self.right_panel.editor.verticalScrollBar().valueChanged.connect(
            lambda v: self.left_panel.editor.verticalScrollBar().setValue(v)
        )

        self.left_panel.editor.verticalScrollBar().valueChanged.connect(
            lambda v: self.left_panel.editor.line_number_area.update()
        )
        self.right_panel.editor.verticalScrollBar().valueChanged.connect(
            lambda v: self.right_panel.editor.line_number_area.update()
        )

        # Wyszukiwanie
        def do_search(next_=True):
            text = self.search_edit.text()
            l_hits, l_idx = self.left_panel.editor.search_text(text)
            r_hits, r_idx = self.right_panel.editor.search_text(text)
            self.set_search_status(l_hits, r_hits)
        def do_next():
            text = self.search_edit.text()
            self.left_panel.editor.search_next(text)
            self.right_panel.editor.search_next(text)
            l_hits = len(self.left_panel.editor.search_matches)
            r_hits = len(self.right_panel.editor.search_matches)
            self.set_search_status(l_hits, r_hits)
        def do_prev():
            text = self.search_edit.text()
            self.left_panel.editor.search_prev(text)
            self.right_panel.editor.search_prev(text)
            l_hits = len(self.left_panel.editor.search_matches)
            r_hits = len(self.right_panel.editor.search_matches)
            self.set_search_status(l_hits, r_hits)

        self.search_edit.textChanged.connect(do_search)
        self.search_next_btn.clicked.connect(do_next)
        self.search_prev_btn.clicked.connect(do_prev)

        # Obsługa Enter/Shift+Enter
        def keyPressEvent(event):
            if event.key() in (Qt.Key_Enter, Qt.Key_Return):
                if event.modifiers() & Qt.ShiftModifier:
                    do_prev()
                else:
                    do_next()
            else:
                QLineEdit.keyPressEvent(self.search_edit, event)
        self.search_edit.keyPressEvent = keyPressEvent

        self.set_search_status = lambda l, r: self.search_status.setText(
            f"Oryginał: {l} | Mod: {r} wyników"
            if l or r else "Brak wyników"
        )

        self.activateWindow()
        self.raise_()
        self.setFocus()
import os
from PyQt5.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QLabel, QSplitter, QWidget,
    QGroupBox, QTableView, QHeaderView, QAbstractItemView, QHBoxLayout, QGridLayout,
    QRadioButton, QProgressBar, QCheckBox, QLineEdit
)
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex, QTimer

DIFF_COLOR_CHANGED_BG = QColor(255, 255, 0)
DIFF_COLOR_REMOVED_BG = QColor(255, 100, 100)
DIFF_COLOR_DEFAULT_BG = QColor(255, 255, 255)
DIFF_COLOR_TEXT = QColor(0, 0, 0)
HEADER_FONT = QFont("Consolas, Courier New, Monospace", 10, QFont.Bold)
DEFAULT_FONT = QFont("Consolas, Courier New, Monospace", 10)

def load_txt_as_list(path, progress_callback=None, label_callback=None):
    data = []
    encodings = ['utf-8-sig', 'utf-8', 'cp1252', 'iso-8859-1']
    line_count = 0
    size = os.path.getsize(path)
    read_bytes = 0
    for encoding in encodings:
        try:
            with open(path, encoding=encoding) as f:
                for line in f:
                    read_bytes += len(line.encode(encoding, errors='ignore'))
                    line = line.strip()
                    if not line:
                        continue
                    row = line.split('\t')
                    data.append(row)
                    line_count += 1
                    if progress_callback and line_count % 500 == 0:
                        progress_callback(read_bytes, size)
                        if label_callback:
                            label_callback(f"Wczytywanie pliku: {os.path.basename(path)} ({line_count} linii)")
            break
        except Exception:
            continue
    if data:
        header_len = len(data[0])
        for i in range(len(data)):
            row_len = len(data[i])
            if row_len < header_len:
                data[i].extend([""] * (header_len - row_len))
            elif row_len > header_len:
                data[i] = data[i][:header_len]
    return data

def find_diff_rows(rows_a, rows_b):
    diff_rows = set()
    max_rows = max(len(rows_a), len(rows_b))
    cols = max(len(rows_a[0]) if rows_a else 0, len(rows_b[0]) if rows_b else 0)
    for i in range(max_rows):
        row_a = rows_a[i] if i < len(rows_a) else [""]*cols
        row_b = rows_b[i] if i < len(rows_b) else [""]*cols
        if row_a != row_b:
            diff_rows.add(i)
    return diff_rows

def find_search_rows(rows, search_text):
    if not search_text:
        return set(range(len(rows)))
    lowered = search_text.lower()
    return set(i for i, row in enumerate(rows)
               if any(lowered in (str(cell).lower()) for cell in row))

class LoadingDialog(QDialog):
    def __init__(self, org_file, mod_file, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Wczytywanie plików…")
        self.setModal(True)
        self.org_file = org_file
        self.mod_file = mod_file

        layout = QVBoxLayout(self)
        self.info_label = QLabel("Przygotowywanie…")
        self.info_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.info_label)
        self.progress = QProgressBar()
        self.progress.setMinimum(0)
        self.progress.setMaximum(100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.loaded_org = None
        self.loaded_mod = None

        QTimer.singleShot(100, self.load_files)

    def update_progress(self, value, total):
        percent = int(100 * value / total) if total > 0 else 0
        self.progress.setValue(percent)
        QApplication.processEvents()

    def update_label(self, txt):
        self.info_label.setText(txt)
        QApplication.processEvents()

    def load_files(self):
        self.update_label(f"Wczytywanie pliku oryginalnego: {os.path.basename(self.org_file)}")
        self.update_progress(0, 1)
        self.loaded_org = load_txt_as_list(self.org_file, self.update_progress, self.update_label)
        self.update_progress(100, 100)
        self.update_label(f"Wczytywanie pliku zmodyfikowanego: {os.path.basename(self.mod_file)}")
        self.update_progress(0, 1)
        self.loaded_mod = load_txt_as_list(self.mod_file, self.update_progress, self.update_label)
        self.update_progress(100, 100)
        self.accept()

class TableModel(QAbstractTableModel):
    def __init__(self, data_rows, headers, compare_rows=None, only_diff=False, search_text="", parent=None):
        super().__init__(parent)
        self._data_all = data_rows
        self._compare = compare_rows
        self._headers = headers
        self.only_diff = only_diff
        self.search_text = search_text
        self._rows_map = []
        self._diff_rows = set()
        self._update_filter()

    def _update_filter(self):
        if self._compare is not None:
            self._diff_rows = find_diff_rows(self._data_all, self._compare)
        else:
            self._diff_rows = set()
        search_rows = find_search_rows(self._data_all, self.search_text)
        if self.only_diff and self._compare is not None:
            visible = self._diff_rows & search_rows
        else:
            visible = search_rows
        self._rows_map = sorted(visible)

    def set_filter(self, only_diff, search_text):
        self.only_diff = only_diff
        self.search_text = search_text
        self._update_filter()
        self.layoutChanged.emit()

    def rowCount(self, parent=QModelIndex()):
        return len(self._rows_map)

    def columnCount(self, parent=QModelIndex()):
        return len(self._headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        real_row = self._rows_map[index.row()]
        col = index.column()
        cell_val = self._data_all[real_row][col] if real_row < len(self._data_all) and col < len(self._data_all[real_row]) else ""
        compare_val = None
        if self._compare is not None:
            compare_val = self._compare[real_row][col] if real_row < len(self._compare) and col < len(self._compare[real_row]) else ""
        if role == Qt.DisplayRole:
            return cell_val
        if role == Qt.ToolTipRole and self._compare is not None and cell_val != compare_val:
            return f"Oryginał: {compare_val}"
        if role == Qt.FontRole:
            return DEFAULT_FONT
        if role == Qt.BackgroundRole and self._compare is not None:
            if real_row >= len(self._compare):
                return DIFF_COLOR_REMOVED_BG
            elif cell_val != compare_val:
                return DIFF_COLOR_CHANGED_BG
            else:
                return DIFF_COLOR_DEFAULT_BG
        if role == Qt.BackgroundRole:
            return DIFF_COLOR_DEFAULT_BG
        if role == Qt.ForegroundRole:
            return DIFF_COLOR_TEXT
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                if section < len(self._headers):
                    return self._headers[section]
                return ""
            else:
                if section < len(self._data_all):
                    return str(section + 1)
                return ""
        if role == Qt.FontRole:
            return HEADER_FONT
        return None

    def get_stats(self):
        visible = len(self._rows_map)
        visible_diff = sum(1 for r in self._rows_map if r in self._diff_rows)
        total = len(self._data_all)
        total_diff = len(self._diff_rows)
        return visible, visible_diff, total, total_diff

class DiffTableModel(QAbstractTableModel):
    def __init__(self, mod_rows, org_rows, headers, only_diff=False, search_text="", parent=None):
        super().__init__(parent)
        self._mod_all = mod_rows
        self._org_all = org_rows
        self._headers = headers
        self.only_diff = only_diff
        self.search_text = search_text
        self._rows_map = []
        self._diff_rows = set()
        self._update_filter()

    def _update_filter(self):
        self._diff_rows = find_diff_rows(self._mod_all, self._org_all)
        search_rows = find_search_rows(self._mod_all, self.search_text)
        if self.only_diff:
            visible = self._diff_rows & search_rows
        else:
            visible = search_rows
        self._rows_map = sorted(visible)

    def set_filter(self, only_diff, search_text):
        self.only_diff = only_diff
        self.search_text = search_text
        self._update_filter()
        self.layoutChanged.emit()

    def rowCount(self, parent=QModelIndex()):
        return len(self._rows_map)

    def columnCount(self, parent=QModelIndex()):
        return len(self._headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        real_row = self._rows_map[index.row()]
        col = index.column()
        mod_val = self._mod_all[real_row][col] if real_row < len(self._mod_all) and col < len(self._mod_all[real_row]) else ""
        org_val = self._org_all[real_row][col] if real_row < len(self._org_all) and col < len(self._org_all[real_row]) else ""
        if role == Qt.DisplayRole:
            return mod_val
        if role == Qt.ToolTipRole and mod_val != org_val:
            return f"Oryginał: {org_val}"
        if role == Qt.FontRole:
            return DEFAULT_FONT
        if role == Qt.BackgroundRole:
            if real_row >= len(self._mod_all):
                return DIFF_COLOR_REMOVED_BG
            elif org_val != mod_val:
                return DIFF_COLOR_CHANGED_BG
            else:
                return DIFF_COLOR_DEFAULT_BG
        if role == Qt.ForegroundRole:
            return DIFF_COLOR_TEXT
        return None

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                if section < len(self._headers):
                    return self._headers[section]
                return ""
            else:
                if section < len(self._mod_all):
                    return str(section + 1)
                return ""
        if role == Qt.FontRole:
            return HEADER_FONT
        return None

    def get_stats(self):
        visible = len(self._rows_map)
        visible_diff = sum(1 for r in self._rows_map if r in self._diff_rows)
        total = len(self._mod_all)
        total_diff = len(self._diff_rows)
        return visible, visible_diff, total, total_diff

class SynchronizedTableView(QTableView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._sync_target = None
        self.verticalScrollBar().valueChanged.connect(self._sync_vertical)
        self.horizontalScrollBar().valueChanged.connect(self._sync_horizontal)
        self._block_sync = False

    def set_sync_target(self, target):
        self._sync_target = target

    def _sync_vertical(self, value):
        if self._sync_target and not self._block_sync:
            self._sync_target._block_sync = True
            self._sync_target.verticalScrollBar().setValue(value)
            self._sync_target._block_sync = False

    def _sync_horizontal(self, value):
        if self._sync_target and not self._block_sync:
            self._sync_target._block_sync = True
            self._sync_target.horizontalScrollBar().setValue(value)
            self._sync_target._block_sync = False

class StatsPanel(QWidget):
    """Panel statystyk wyświetlany pionowo, z dynamicznymi nagłówkami"""
    def __init__(self, org_label="Oryginał", mod_label="Modyfikacja"):
        super().__init__()
        self._org_label = org_label
        self._mod_label = mod_label
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(4, 4, 4, 4)
        self.grid.setSpacing(2)
        # Etykiety w pionie
        self.labels = []
        self.values = []
        for i, label in enumerate([
            "Widoczne wiersze:",
            "Widoczne różniące się:",
            "Wszystkich wierszy:",
            "Różniących się ogółem:"
        ]):
            lab = QLabel(label)
            lab.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            self.labels.append(lab)
            self.grid.addWidget(lab, i+1, 0)
        # Kolumny na wartości i nagłówki
        self.val1 = []
        self.val2 = []
        # Nagłówki kolumn (dynamiczne)
        self.col1_head = QLabel(self._org_label)
        self.col2_head = QLabel(self._mod_label)
        self.col1_head.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.col2_head.setAlignment(Qt.AlignHCenter | Qt.AlignVCenter)
        self.grid.addWidget(self.col1_head, 0, 1, 1, 1)
        self.grid.addWidget(self.col2_head, 0, 2, 1, 1)
        for i in range(4):
            v1 = QLabel("")
            v1.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.grid.addWidget(v1, i+1, 1)
            self.val1.append(v1)
            v2 = QLabel("")
            v2.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.grid.addWidget(v2, i+1, 2)
            self.val2.append(v2)
        self.set_diff_mode(False)

    def set_labels(self, org_label, mod_label):
        self._org_label = org_label
        self._mod_label = mod_label
        self.col1_head.setText(self._org_label)
        self.col2_head.setText(self._mod_label)

    def set_diff_mode(self, is_diff_tab_mode):
        for i in range(4):
            self.val2[i].setVisible(not is_diff_tab_mode)
        if is_diff_tab_mode:
            self.col1_head.setText(self._mod_label or "Wynik")
            self.col2_head.setVisible(False)
        else:
            self.col1_head.setText(self._org_label)
            self.col2_head.setText(self._mod_label)
            self.col2_head.setVisible(True)

    def set_values(self, vals1, vals2=None):
        for i, v in enumerate(vals1):
            self.val1[i].setText(str(v))
        if vals2:
            for i, v in enumerate(vals2):
                self.val2[i].setText(str(v))
        else:
            for i in range(4):
                self.val2[i].setText("")

class DiffTextPopup(QDialog):
    def __init__(self, org_file, mod_file, parent=None, filename=None, org_label="Oryginał", mod_label="Modyfikacja"):
        app = QApplication.instance() or QApplication([])
        self.loaded_org = None
        self.loaded_mod = None
        dlg = LoadingDialog(org_file, mod_file)
        if dlg.exec_() == QDialog.Accepted:
            self.loaded_org = dlg.loaded_org
            self.loaded_mod = dlg.loaded_mod
        else:
            super().__init__(parent)
            self.close()
            return

        super().__init__(parent)
        self.setWindowTitle("Porównywanie plików TXT - D2RTools")
        self.setMinimumSize(1200, 800)
        self.setWindowFlags(
            Qt.Window |
            Qt.WindowMinimizeButtonHint |
            Qt.WindowMaximizeButtonHint |
            Qt.WindowCloseButtonHint
        )
        self.setWindowModality(Qt.ApplicationModal)
        self.filename = filename

        self.org_label = org_label or "Oryginał"
        self.mod_label = mod_label or "Modyfikacja"

        self.org_data = self.loaded_org
        self.mod_data = self.loaded_mod

        self.headers = self.org_data[0] if self.org_data else (self.mod_data[0] if self.mod_data else [])
        self.org_data_rows = self.org_data[1:] if len(self.org_data) > 1 else []
        self.mod_data_rows = self.mod_data[1:] if len(self.mod_data) > 1 else []

        self.setup_ui()
        self.set_mode_side_by_side()
        self.activateWindow()
        self.raise_()
        self.setFocus()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(8)

        # Panel informacji o plikach
        info_panel = QWidget()
        info_layout = QVBoxLayout(info_panel)
        info_layout.setSpacing(2)
        info_layout.setContentsMargins(0, 0, 0, 0)

        header_box = QGroupBox("Informacje o plikach")
        header_layout = QHBoxLayout(header_box)
        header_layout.setSpacing(12)
        if self.filename:
            header_layout.addWidget(QLabel(f"<b>Plik:</b> {self.filename}"))
        header_layout.addWidget(QLabel(f"<b>{self.org_label}:</b> {len(self.org_data_rows)} wierszy"))
        header_layout.addWidget(QLabel(f"<b>{self.mod_label}:</b> {len(self.mod_data_rows)} wierszy"))
        diff_count = abs(len(self.org_data_rows) - len(self.mod_data_rows))
        if diff_count > 0:
            change_type = "więcej" if len(self.mod_data_rows) > len(self.org_data_rows) else "mniej"
            header_layout.addWidget(QLabel(f"<b>Różnica:</b> {diff_count} linii {change_type}"))
        header_layout.addStretch(1)
        info_layout.addWidget(header_box)

        # Kompaktowa legenda
        compact_legend = QWidget()
        legend_layout = QHBoxLayout(compact_legend)
        legend_layout.setContentsMargins(5, 2, 5, 2)
        legend_layout.setSpacing(20)
        def legendSwatch(color):
            sw = QLabel()
            sw.setFixedSize(18, 12)
            sw.setStyleSheet(f"background: {color.name()}; border: 1px solid #aaa; margin-right:3px;")
            return sw
        legend_layout.addWidget(legendSwatch(DIFF_COLOR_CHANGED_BG))
        legend_layout.addWidget(QLabel("zmiana komórki"))
        legend_layout.addWidget(legendSwatch(DIFF_COLOR_REMOVED_BG))
        legend_layout.addWidget(QLabel("usunięta/dodana linia"))
        legend_layout.addStretch(1)
        info_layout.addWidget(compact_legend)

        # Opcje trybu + filtry
        options_panel = QWidget()
        options_layout = QHBoxLayout(options_panel)
        options_layout.setContentsMargins(0, 0, 0, 0)
        self.radio_side_by_side = QRadioButton("Obok siebie (2 tabele)")
        self.radio_table_diff = QRadioButton("Diff tablicowy (komórki)")
        self.radio_side_by_side.setChecked(True)
        self.radio_side_by_side.toggled.connect(self.on_mode_changed)
        self.radio_table_diff.toggled.connect(self.on_mode_changed)
        options_layout.addWidget(self.radio_side_by_side)
        options_layout.addWidget(self.radio_table_diff)
        self.show_only_diff = QCheckBox("Pokaż tylko różnice")
        self.show_only_diff.stateChanged.connect(self.on_filter_changed)
        options_layout.addWidget(self.show_only_diff)
        options_layout.addWidget(QLabel("Szukaj:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Wpisz fragment tekstu...")
        self.search_edit.textChanged.connect(self.on_filter_changed)
        options_layout.addWidget(self.search_edit)
        options_layout.addStretch(1)
        info_layout.addWidget(options_panel)

        # Pionowy panel statystyk, dynamiczne nagłówki
        self.stats_panel = StatsPanel(self.org_label, self.mod_label)
        info_layout.addWidget(self.stats_panel)

        layout.addWidget(info_panel)

        # Splittery i widoki
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.org_table = SynchronizedTableView()
        self.mod_table = SynchronizedTableView()
        self.org_table.set_sync_target(self.mod_table)
        self.mod_table.set_sync_target(self.org_table)
        self.setup_table(self.org_table)
        self.setup_table(self.mod_table)
        self.splitter_side_by_side = QSplitter(Qt.Horizontal)
        self.splitter_side_by_side.addWidget(self.org_table)
        self.splitter_side_by_side.addWidget(self.mod_table)
        self.splitter_side_by_side.setSizes([600, 600])

        self.table_diff = QTableView()
        self.setup_table(self.table_diff)

        self.main_splitter.addWidget(self.splitter_side_by_side)
        self.main_splitter.addWidget(self.table_diff)
        self.table_diff.hide()
        layout.addWidget(self.main_splitter)

    def setup_table(self, table):
        table.setFont(DEFAULT_FONT)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionMode(QAbstractItemView.NoSelection)
        table.setCornerButtonEnabled(False)
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        table.verticalHeader().setSectionResizeMode(QHeaderView.Fixed)
        table.setWordWrap(False)
        table.setShowGrid(True)
        table.setStyleSheet("QTableView { color: #000; background: #fff; }")

    def on_mode_changed(self):
        if self.radio_side_by_side.isChecked():
            self.set_mode_side_by_side()
        if self.radio_table_diff.isChecked():
            self.set_mode_table_diff()
        self.update_stats()

    def on_filter_changed(self):
        only_diff = self.show_only_diff.isChecked()
        search_text = self.search_edit.text()
        if self.radio_side_by_side.isChecked():
            if hasattr(self, "org_model") and hasattr(self, "mod_model"):
                self.org_model.set_filter(only_diff, search_text)
                self.mod_model.set_filter(only_diff, search_text)
        if self.radio_table_diff.isChecked():
            if hasattr(self, "diff_model"):
                self.diff_model.set_filter(only_diff, search_text)
        self.update_stats()

    def set_mode_side_by_side(self):
        only_diff = self.show_only_diff.isChecked()
        search_text = self.search_edit.text()
        self.org_model = TableModel(self.org_data_rows, self.headers, compare_rows=self.mod_data_rows,
                                    only_diff=only_diff, search_text=search_text)
        self.mod_model = TableModel(self.mod_data_rows, self.headers, compare_rows=self.org_data_rows,
                                    only_diff=only_diff, search_text=search_text)
        self.org_table.setModel(self.org_model)
        self.mod_table.setModel(self.mod_model)
        self.splitter_side_by_side.show()
        self.table_diff.hide()
        self.stats_panel.set_labels(self.org_label, self.mod_label)
        self.stats_panel.set_diff_mode(False)
        self.update_stats()

    def set_mode_table_diff(self):
        only_diff = self.show_only_diff.isChecked()
        search_text = self.search_edit.text()
        self.diff_model = DiffTableModel(self.mod_data_rows, self.org_data_rows, self.headers,
                                         only_diff=only_diff, search_text=search_text)
        self.table_diff.setModel(self.diff_model)
        self.table_diff.show()
        self.splitter_side_by_side.hide()
        self.stats_panel.set_labels(self.mod_label, "")
        self.stats_panel.set_diff_mode(True)
        self.update_stats()

    def update_stats(self):
        if self.radio_side_by_side.isChecked() and hasattr(self, "org_model") and hasattr(self, "mod_model"):
            v1, vd1, t1, td1 = self.org_model.get_stats()
            v2, vd2, t2, td2 = self.mod_model.get_stats()
            self.stats_panel.set_diff_mode(False)
            self.stats_panel.set_labels(self.org_label, self.mod_label)
            self.stats_panel.set_values([v1, vd1, t1, td1], [v2, vd2, t2, td2])
        elif self.radio_table_diff.isChecked() and hasattr(self, "diff_model"):
            v, vd, t, td = self.diff_model.get_stats()
            self.stats_panel.set_diff_mode(True)
            self.stats_panel.set_labels(self.mod_label, "")
            self.stats_panel.set_values([v, vd, t, td])
        else:
            self.stats_panel.set_diff_mode(True)
            self.stats_panel.set_labels(self.mod_label, "")
            self.stats_panel.set_values([""]*4)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.accept()
        else:
            super().keyPressEvent(event)
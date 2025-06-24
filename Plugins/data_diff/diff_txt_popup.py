import os
from PyQt5.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QLabel, QSplitter, QWidget,
    QGroupBox, QTableView, QHeaderView, QAbstractItemView, QHBoxLayout, QGridLayout,
    QRadioButton, QProgressBar, QCheckBox, QLineEdit, QPushButton, QButtonGroup
)
from PyQt5.QtGui import QColor, QFont
from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex, QTimer, pyqtSignal, pyqtSlot
import re

DIFF_COLOR_CHANGED_BG = QColor(255, 255, 0)       # Żółty - zmiana komórki
DIFF_COLOR_REMOVED_BG = QColor(255, 100, 100)     # Czerwony - usunięta/dodana linia
DIFF_COLOR_DEFAULT_BG = QColor(255, 255, 255)     # Biały - brak zmian
DIFF_COLOR_TEXT = QColor(0, 0, 0)                 # Czarny - kolor tekstu
DIFF_COLOR_SEARCH_HIGHLIGHT = QColor(144, 238, 144)  # Jasny zielony - podświetlenie wyszukiwania
HEADER_FONT = QFont("Consolas, Courier New, Monospace", 10, QFont.Bold)
DEFAULT_FONT = QFont("Consolas, Courier New, Monospace", 10)

def load_txt_as_list(path, progress_callback=None, label_callback=None):
    """
    Wczytuje plik tekstowy do listy list.
    Każdy wiersz pliku staje się listą pól rozdzielonych tabulatorami.
    
    Args:
        path: Ścieżka do pliku lub None.
        progress_callback: Opcjonalna funkcja wywołania zwrotnego do aktualizacji paska postępu.
        label_callback: Opcjonalna funkcja wywołania zwrotnego do aktualizacji etykiety.
        
    Returns:
        Lista list zawierająca dane z pliku, lub pusta lista jeśli path jest None.
    """
    data = []
    # Dodanie zabezpieczenia przed None
    if path is None:
        return data
        
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
    """
    Znajduje różnice między dwoma zbiorami wierszy.
    
    Args:
        rows_a: Lista wierszy pierwszego pliku.
        rows_b: Lista wierszy drugiego pliku.
        
    Returns:
        Zbiór indeksów wierszy różniących się.
    """
    # Porównanie według pozycji (standardowe)
    diff_rows = set()
    max_rows = max(len(rows_a), len(rows_b))
    cols = max(len(rows_a[0]) if rows_a else 0, len(rows_b[0]) if rows_b else 0)
    for i in range(max_rows):
        row_a = rows_a[i] if i < len(rows_a) else [""]*cols
        row_b = rows_b[i] if i < len(rows_b) else [""]*cols
        if row_a != row_b:
            diff_rows.add(i)
    return diff_rows

def find_search_rows(rows, search_text, whole_words=False):
    """
    Wyszukuje wiersze zawierające podany tekst.
    
    Args:
        rows: Lista wierszy do przeszukania
        search_text: Tekst do wyszukania
        whole_words: Czy wyszukiwać tylko całe wyrazy
        
    Returns:
        Zbiór indeksów wierszy zawierających szukany tekst
    """
    if not search_text:
        return set(range(len(rows)))
    
    lowered = search_text.lower()
    
    if whole_words:
        # Przygotowanie wzorca regex do wyszukiwania całych wyrazów
        pattern = r'\b' + re.escape(lowered) + r'\b'
        regex = re.compile(pattern)
        
        # Wyszukiwanie wierszy zawierających całe słowa
        return set(i for i, row in enumerate(rows)
                  if any(regex.search(str(cell).lower()) for cell in row))
    else:
        # Standardowe wyszukiwanie ciągu znaków
        return set(i for i, row in enumerate(rows)
                  if any(lowered in str(cell).lower() for cell in row))

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

        # Dodanie przycisku anulowania
        self.cancel_button = QPushButton("Anuluj")
        self.cancel_button.clicked.connect(self.reject)
        layout.addWidget(self.cancel_button)

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
        # Wczytywanie pliku oryginalnego, jeśli istnieje
        if self.org_file is not None:
            self.update_label(f"Wczytywanie pliku oryginalnego: {os.path.basename(self.org_file)}")
            self.update_progress(0, 1)
            self.loaded_org = load_txt_as_list(self.org_file, self.update_progress, self.update_label)
            self.update_progress(100, 100)
        else:
            self.update_label("Brak pliku oryginalnego")
            self.loaded_org = []

        # Wczytywanie pliku zmodyfikowanego, jeśli istnieje
        if self.mod_file is not None:
            self.update_label(f"Wczytywanie pliku zmodyfikowanego: {os.path.basename(self.mod_file)}")
            self.update_progress(0, 1)
            self.loaded_mod = load_txt_as_list(self.mod_file, self.update_progress, self.update_label)
            self.update_progress(100, 100)
        else:
            self.update_label("Brak pliku zmodyfikowanego")
            self.loaded_mod = []
            
        self.accept()

class TableModel(QAbstractTableModel):
    def __init__(self, data_rows, headers, compare_rows=None, only_diff=False, 
                 search_text="", whole_words=False, parent=None):
        super().__init__(parent)
        self._headers = headers
        self._data_all = data_rows
        self._compare = compare_rows
        self.only_diff = only_diff
        self.search_text = search_text
        self.whole_words = whole_words
        
        self._rows_map = []
        self._diff_rows = set()
        self._search_rows = set()
        self._cell_has_match = {}  # Zoptymalizowana struktura - przechowuje tylko informację o istnieniu dopasowania
        self._update_filter()

    def _update_filter(self):
        # Znajdź różnice między wierszami, jeśli mamy z czym porównywać
        if self._compare is not None:
            self._diff_rows = find_diff_rows(self._data_all, self._compare)
        else:
            self._diff_rows = set()
        
        # Wyszukiwanie wierszy zawierających szukaną frazę
        if not self.search_text:
            self._search_rows = set(range(len(self._data_all)))
            self._cell_has_match = {}  # Brak wyszukiwania, więc brak dopasowań
        else:
            self._find_search_matches()
            
        # Filtrowanie widocznych wierszy
        if self.only_diff and self._compare is not None:
            visible = self._diff_rows & self._search_rows
        else:
            visible = self._search_rows
        
        self._rows_map = sorted(visible)

    def _find_search_matches(self):
        """Optymalizowana metoda wyszukiwania dopasowań - zapamiętuje tylko fakt istnienia dopasowania"""
        lowered_search = self.search_text.lower()
        self._search_rows = set()
        self._cell_has_match = {}
        
        if self.whole_words:
            pattern = r'\b' + re.escape(lowered_search) + r'\b'
            regex = re.compile(pattern)
            
        for row_idx, row in enumerate(self._data_all):
            has_match = False
            row_matches = {}
            
            for col_idx, cell in enumerate(row):
                cell_text = str(cell).lower()
                
                if self.whole_words:
                    if regex.search(cell_text):
                        has_match = True
                        row_matches[col_idx] = True
                else:
                    if lowered_search in cell_text:
                        has_match = True
                        row_matches[col_idx] = True
            
            if has_match:
                self._search_rows.add(row_idx)
                self._cell_has_match[row_idx] = row_matches

    def set_filter(self, only_diff, search_text, whole_words=False):
        self.only_diff = only_diff
        self.search_text = search_text
        self.whole_words = whole_words
        self._update_filter()
        self.layoutChanged.emit()

    def rowCount(self, parent=QModelIndex()):
        return len(self._rows_map)

    def columnCount(self, parent=QModelIndex()):
        return len(self._headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        
        display_row = index.row()
        col = index.column()
        real_row = self._rows_map[display_row]
        
        # Wartość komórki w bieżących danych
        cell_val = self._data_all[real_row][col] if real_row < len(self._data_all) and col < len(self._data_all[real_row]) else ""
        
        # Wartość komórki w danych porównywalnych
        compare_val = None
        if self._compare is not None:
            compare_val = self._compare[real_row][col] if real_row < len(self._compare) and col < len(self._compare[real_row]) else ""
        
        if role == Qt.DisplayRole:
            return cell_val
        
        elif role == Qt.ToolTipRole and self._compare is not None and cell_val != compare_val:
            return f"Oryginał: {compare_val}"
        
        elif role == Qt.FontRole:
            return DEFAULT_FONT
        
        elif role == Qt.BackgroundRole:
            # Sprawdzamy, czy komórka zawiera wyszukiwaną frazę (szybkie sprawdzenie)
            if (real_row in self._cell_has_match and col in self._cell_has_match[real_row]):
                return DIFF_COLOR_SEARCH_HIGHLIGHT
            
            # Jeśli nie, stosujemy standardowe kolorowanie diff
            if self._compare is not None:
                if real_row >= len(self._compare):
                    return DIFF_COLOR_REMOVED_BG
                elif real_row in self._diff_rows and cell_val != compare_val:
                    return DIFF_COLOR_CHANGED_BG
            
            return DIFF_COLOR_DEFAULT_BG
        
        elif role == Qt.ForegroundRole:
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
        
    def get_real_row(self, displayed_row):
        """Zwraca rzeczywisty indeks wiersza z mapy na podstawie indeksu wyświetlanego"""
        if 0 <= displayed_row < len(self._rows_map):
            return self._rows_map[displayed_row]
        return -1

    def find_display_row_for_real(self, real_row):
        """Znajduje indeks wyświetlany dla podanego rzeczywistego indeksu wiersza"""
        try:
            return self._rows_map.index(real_row)
        except ValueError:
            return -1  # Nie znaleziono

class DiffTableModel(QAbstractTableModel):
    def __init__(self, mod_rows, org_rows, headers, only_diff=False, 
                 search_text="", whole_words=False, parent=None):
        super().__init__(parent)
        self._headers = headers
        self._mod_all = mod_rows
        self._org_all = org_rows
        self.only_diff = only_diff
        self.search_text = search_text
        self.whole_words = whole_words
        
        self._rows_map = []
        self._diff_rows = set()
        self._search_rows = set()
        self._cell_has_match = {}  # Zoptymalizowana struktura - przechowuje tylko informację o istnieniu dopasowania
        self._update_filter()

    def _update_filter(self):
        # Znajdź różnice między wierszami
        self._diff_rows = find_diff_rows(self._mod_all, self._org_all)
        
        # Wyszukiwanie wierszy zawierających szukaną frazę
        if not self.search_text:
            self._search_rows = set(range(len(self._mod_all)))
            self._cell_has_match = {}  # Brak wyszukiwania, więc brak dopasowań
        else:
            self._find_search_matches()
            
        # Filtrowanie widocznych wierszy
        if self.only_diff:
            visible = self._diff_rows & self._search_rows
        else:
            visible = self._search_rows
        
        self._rows_map = sorted(visible)

    def _find_search_matches(self):
        """Optymalizowana metoda wyszukiwania dopasowań - zapamiętuje tylko fakt istnienia dopasowania"""
        lowered_search = self.search_text.lower()
        self._search_rows = set()
        self._cell_has_match = {}
        
        if self.whole_words:
            pattern = r'\b' + re.escape(lowered_search) + r'\b'
            regex = re.compile(pattern)
            
        for row_idx, row in enumerate(self._mod_all):
            has_match = False
            row_matches = {}
            
            for col_idx, cell in enumerate(row):
                cell_text = str(cell).lower()
                
                if self.whole_words:
                    if regex.search(cell_text):
                        has_match = True
                        row_matches[col_idx] = True
                else:
                    if lowered_search in cell_text:
                        has_match = True
                        row_matches[col_idx] = True
            
            if has_match:
                self._search_rows.add(row_idx)
                self._cell_has_match[row_idx] = row_matches

    def set_filter(self, only_diff, search_text, whole_words=False):
        self.only_diff = only_diff
        self.search_text = search_text
        self.whole_words = whole_words
        self._update_filter()
        self.layoutChanged.emit()

    def rowCount(self, parent=QModelIndex()):
        return len(self._rows_map)

    def columnCount(self, parent=QModelIndex()):
        return len(self._headers)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        
        display_row = index.row()
        col = index.column()
        real_row = self._rows_map[display_row]
        
        # Wartość komórki w bieżących danych
        mod_val = self._mod_all[real_row][col] if real_row < len(self._mod_all) and col < len(self._mod_all[real_row]) else ""
        
        # Wartość komórki w danych porównywanych
        org_val = self._org_all[real_row][col] if real_row < len(self._org_all) and col < len(self._org_all[real_row]) else ""
        
        if role == Qt.DisplayRole:
            return mod_val
        
        elif role == Qt.ToolTipRole and mod_val != org_val:
            return f"Oryginał: {org_val}"
        
        elif role == Qt.FontRole:
            return DEFAULT_FONT
        
        elif role == Qt.BackgroundRole:
            # Sprawdzamy, czy komórka zawiera wyszukiwaną frazę (szybkie sprawdzenie)
            if (real_row in self._cell_has_match and col in self._cell_has_match[real_row]):
                return DIFF_COLOR_SEARCH_HIGHLIGHT
            
            # Jeśli nie, stosujemy standardowe kolorowanie diff
            if real_row >= len(self._org_all):
                return DIFF_COLOR_REMOVED_BG
            elif real_row in self._diff_rows and mod_val != org_val:
                return DIFF_COLOR_CHANGED_BG
            
            return DIFF_COLOR_DEFAULT_BG
        
        elif role == Qt.ForegroundRole:
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

    def get_real_row(self, displayed_row):
        """Zwraca rzeczywisty indeks wiersza z mapy na podstawie indeksu wyświetlanego"""
        if 0 <= displayed_row < len(self._rows_map):
            return self._rows_map[displayed_row]
        return -1

    def find_display_row_for_real(self, real_row):
        """Znajduje indeks wyświetlany dla podanego rzeczywistego indeksu wiersza"""
        try:
            return self._rows_map.index(real_row)
        except ValueError:
            return -1  # Nie znaleziono

class SynchronizedTableView(QTableView):
    """Klasa tabeli z synchronizacją przewijania i zaznaczenia"""
    # Sygnały do synchronizacji zaznaczenia
    cell_selected = pyqtSignal(int, int)  # (rzeczywisty_wiersz, kolumna)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._sync_target = None
        self.verticalScrollBar().valueChanged.connect(self._sync_vertical)
        self.horizontalScrollBar().valueChanged.connect(self._sync_horizontal)
        self._block_sync = False
        self._block_selection_sync = False
        
        # Włączenie zaznaczania pojedynczych komórek
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectItems)
        
        # Ustawienie płynnego przewijania
        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.setHorizontalScrollMode(QAbstractItemView.ScrollPerPixel)

    def set_sync_target(self, target):
        """
        Ustawia drugą tabelę jako cel synchronizacji
        
        Args:
            target: Obiekt SynchronizedTableView do synchronizacji
        """
        self._sync_target = target
        
        # Podłączamy sygnał zaznaczenia komórki
        self.cell_selected.connect(target.sync_cell_selection)

    def _sync_vertical(self, value):
        """Synchronizacja przewijania pionowego"""
        if self._sync_target and not self._block_sync:
            self._sync_target._block_sync = True
            self._sync_target.verticalScrollBar().setValue(value)
            self._sync_target._block_sync = False

    def _sync_horizontal(self, value):
        """Synchronizacja przewijania poziomego"""
        if self._sync_target and not self._block_sync:
            self._sync_target._block_sync = True
            self._sync_target.horizontalScrollBar().setValue(value)
            self._sync_target._block_sync = False
    
    @pyqtSlot(int, int)
    def sync_cell_selection(self, real_row, column):
        """
        Slot do synchronizacji zaznaczenia komórki przez rzeczywisty indeks wiersza
        
        Args:
            real_row: Rzeczywisty indeks wiersza w danych
            column: Indeks kolumny
        """
        if not self._block_selection_sync and self.model():
            self._block_selection_sync = True
            
            # Konwersja z rzeczywistego indeksu na wyświetlany
            display_row = -1
            if hasattr(self.model(), "find_display_row_for_real"):
                display_row = self.model().find_display_row_for_real(real_row)
            
            if display_row >= 0 and display_row < self.model().rowCount() and column < self.model().columnCount():
                index = self.model().index(display_row, column)
                self.setCurrentIndex(index)
                
                # Upewniamy się, że komórka jest widoczna, używając EnsureVisible
                self.scrollTo(index, QAbstractItemView.EnsureVisible)
            
            self._block_selection_sync = False
    
    def currentChanged(self, current, previous):
        """Przechwycenie zmiany aktualnie zaznaczonej komórki"""
        super().currentChanged(current, previous)
        # Jeśli to zaznaczenie nie jest blokowane i indeks jest poprawny
        if not self._block_selection_sync and current.isValid():
            row = current.row()
            col = current.column()
            
            # Pobieramy rzeczywisty indeks wiersza
            real_row = row
            if hasattr(self.model(), "get_real_row"):
                real_row = self.model().get_real_row(row)
            
            # Emitujemy sygnał o zmianie zaznaczenia z rzeczywistym indeksem wiersza
            self.cell_selected.emit(real_row, col)

class StatsPanel(QWidget):
    """Panel statystyk wyświetlany pionowo, z nagłówkami kolumn"""
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
            self.grid.addWidget(lab, i, 0)
        
        # Kolumny na wartości
        self.val1 = []
        self.val2 = []
        
        # Tworzenie kolumn z wartościami statystyk
        for i in range(4):
            v1 = QLabel("")
            v1.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.grid.addWidget(v1, i, 1)
            self.val1.append(v1)
            
            v2 = QLabel("")
            v2.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.grid.addWidget(v2, i, 2)
            self.val2.append(v2)
        
        self.set_diff_mode(False)

    def set_labels(self, org_label, mod_label):
        self._org_label = org_label
        self._mod_label = mod_label

    def set_diff_mode(self, is_diff_tab_mode):
        for i in range(4):
            self.val2[i].setVisible(not is_diff_tab_mode)

    def set_values(self, vals1, vals2=None):
        for i, v in enumerate(vals1):
            self.val1[i].setText(str(v))
        if vals2:
            for i, v in enumerate(vals2):
                self.val2[i].setText(str(v))
        else:
            for i in range(4):
                self.val2[i].setText("")

class LabeledTableWidget(QWidget):
    """Widget zawierający etykietę i tabelę"""
    def __init__(self, label_text="", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        # Etykieta
        self.label = QLabel(f"<b>{label_text}</b>")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)
        
        # Tabela
        self.table = SynchronizedTableView()
        layout.addWidget(self.table)
    
    def set_label(self, text):
        self.label.setText(f"<b>{text}</b>")
    
    def get_table(self):
        return self.table

class SearchTimer(QTimer):
    """Timer do opóźnionego wyszukiwania"""
    search_ready = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSingleShot(True)
        self.setInterval(300)  # 300 ms opóźnienia
        self.timeout.connect(self.search_ready.emit)
        
    def restart_timer(self):
        """Restartuje timer po każdym wpisaniu znaku"""
        if self.isActive():
            self.stop()
        self.start()

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
        
        # Ustawianie dynamicznego tytułu okna zawierającego nazwę pliku
        if filename:
            self.setWindowTitle(f"Porównywanie pliku {os.path.basename(filename)} - D2RTools")
        else:
            # Jeśli filename nie jest dostępny, spróbuj użyć nazwy z org_file
            if org_file is not None:  # Dodana ochrona przed None
                self.setWindowTitle(f"Porównywanie pliku {os.path.basename(org_file)} - D2RTools")
            elif mod_file is not None:  # Dodana ochrona przed None i użycie mod_file jeśli org_file nie istnieje
                self.setWindowTitle(f"Porównywanie pliku {os.path.basename(mod_file)} - D2RTools")
            else:
                # Domyślny tytuł, gdy nie mamy nazwy pliku
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

        # Zabezpieczenie przed przypadkiem, gdy żaden plik nie został wczytany (oba są None)
        if not self.org_data and not self.mod_data:
            self.headers = []
            self.org_data_rows = []
            self.mod_data_rows = []
        else:
            self.headers = self.org_data[0] if self.org_data else (self.mod_data[0] if self.mod_data else [])
            self.org_data_rows = self.org_data[1:] if self.org_data and len(self.org_data) > 1 else []
            self.mod_data_rows = self.mod_data[1:] if self.mod_data and len(self.mod_data) > 1 else []

        # Timer do opóźnionego wyszukiwania, aby uniknąć zacięć
        self.search_timer = SearchTimer(self)
        self.search_timer.search_ready.connect(self.on_search_timer_timeout)

        self.setup_ui()
        self.set_mode_side_by_side()
        self.activateWindow()
        self.raise_()
        self.setFocus()

    def setup_ui(self):
        # Główny layout okna
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
        legend_layout.addWidget(legendSwatch(DIFF_COLOR_SEARCH_HIGHLIGHT))
        legend_layout.addWidget(QLabel("wyszukana fraza"))
        legend_layout.addStretch(1)
        info_layout.addWidget(compact_legend)

        # Opcje trybu wyświetlania + opcje porównania
        options_panel = QWidget()
        options_layout = QVBoxLayout(options_panel)
        options_layout.setContentsMargins(0, 0, 0, 0)
        options_layout.setSpacing(8)
        
        # Pierwszy wiersz opcji - tryb wyświetlania
        display_mode_layout = QHBoxLayout()
        self.radio_side_by_side = QRadioButton("Obok siebie (2 tabele)")
        self.radio_table_diff = QRadioButton("Diff tablicowy (komórki)")
        self.radio_side_by_side.setChecked(True)
        self.radio_side_by_side.toggled.connect(self.on_mode_changed)
        self.radio_table_diff.toggled.connect(self.on_mode_changed)
        
        display_mode_group = QButtonGroup(self)
        display_mode_group.addButton(self.radio_side_by_side)
        display_mode_group.addButton(self.radio_table_diff)
        
        display_mode_layout.addWidget(self.radio_side_by_side)
        display_mode_layout.addWidget(self.radio_table_diff)
        display_mode_layout.addStretch(1)
        options_layout.addLayout(display_mode_layout)
        
        # Trzeci wiersz opcji - filtry i wyszukiwanie
        filter_layout = QHBoxLayout()
        self.show_only_diff = QCheckBox("Pokaż tylko różnice")
        self.show_only_diff.stateChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.show_only_diff)
        filter_layout.addWidget(QLabel("Szukaj:"))
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Wpisz fragment tekstu...")
        self.search_edit.textChanged.connect(self.on_search_text_changed)
        filter_layout.addWidget(self.search_edit)
        
        # Dodanie checkboxa "Całe wyrazy"
        self.whole_words_checkbox = QCheckBox("Całe wyrazy")
        self.whole_words_checkbox.stateChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.whole_words_checkbox)
        
        filter_layout.addStretch(1)
        options_layout.addLayout(filter_layout)
        
        info_layout.addWidget(options_panel)

        # Pionowy panel statystyk
        self.stats_panel = StatsPanel(self.org_label, self.mod_label)
        info_layout.addWidget(self.stats_panel)

        layout.addWidget(info_panel)

        # --- TRYB OBOK SIEBIE ---
        # Container dla widoku "Obok siebie"
        self.side_by_side_widget = QWidget()
        side_by_side_layout = QHBoxLayout(self.side_by_side_widget)
        side_by_side_layout.setContentsMargins(0, 0, 0, 0)
        side_by_side_layout.setSpacing(4)
        
        # Tworzenie widgetów dla tabel z etykietami
        self.org_table_widget = LabeledTableWidget(self.org_label)
        self.mod_table_widget = LabeledTableWidget(self.mod_label)
        
        # Pobieranie referencji do tabel
        self.org_table = self.org_table_widget.get_table()
        self.mod_table = self.mod_table_widget.get_table()
        
        # Konfiguracja tabel
        self.setup_table(self.org_table)
        self.setup_table(self.mod_table)
        
        # Dodanie widgetów do layoutu
        side_by_side_layout.addWidget(self.org_table_widget)
        side_by_side_layout.addWidget(self.mod_table_widget)
        
        # --- TRYB DIFF TABLICOWY ---
        # Container dla widoku "Diff tablicowy"
        self.table_diff_widget = LabeledTableWidget(self.mod_label)
        self.table_diff = self.table_diff_widget.get_table()
        self.setup_table(self.table_diff)
        
        # Dodanie obu widoków do głównego layoutu
        layout.addWidget(self.side_by_side_widget)
        layout.addWidget(self.table_diff_widget)
        
        # Domyślnie ukrywamy widok diff
        self.table_diff_widget.hide()

    def setup_table(self, table):
        table.setFont(DEFAULT_FONT)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        # Ustawienie trybu zaznaczania na pojedynczą komórkę
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setSelectionBehavior(QAbstractItemView.SelectItems)
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

    def set_mode_side_by_side(self):
        only_diff = self.show_only_diff.isChecked()
        search_text = self.search_edit.text()
        whole_words = self.whole_words_checkbox.isChecked()
        self.org_model = TableModel(self.org_data_rows, self.headers, compare_rows=self.mod_data_rows, only_diff=only_diff, search_text=search_text, whole_words=whole_words)
        self.mod_model = TableModel(self.mod_data_rows, self.headers, compare_rows=self.org_data_rows, only_diff=only_diff, search_text=search_text, whole_words=whole_words)
        self.org_table.setModel(self.org_model)
        self.mod_table.setModel(self.mod_model)
        # Synchronizacja tabel
        self.org_table.set_sync_target(self.mod_table)
        self.mod_table.set_sync_target(self.org_table)
        self.side_by_side_widget.show()
        self.table_diff_widget.hide()

    def set_mode_table_diff(self):
        only_diff = self.show_only_diff.isChecked()
        search_text = self.search_edit.text()
        whole_words = self.whole_words_checkbox.isChecked()
        self.diff_model = DiffTableModel(self.mod_data_rows, self.org_data_rows, self.headers, only_diff=only_diff, search_text=search_text, whole_words=whole_words)
        self.table_diff.setModel(self.diff_model)
        self.side_by_side_widget.hide()
        self.table_diff_widget.show()

    def on_filter_changed(self):
        self.on_search_timer_timeout()

    def on_search_text_changed(self, text):
        self.search_timer.restart_timer()

    def on_search_timer_timeout(self):
        # Aplikuje filtr wyszukiwania i/lub różnic do obecnie wybranego widoku
        only_diff = self.show_only_diff.isChecked()
        search_text = self.search_edit.text()
        whole_words = self.whole_words_checkbox.isChecked()
        if self.radio_side_by_side.isChecked():
            if hasattr(self, "org_model") and hasattr(self, "mod_model"):
                self.org_model.set_filter(only_diff, search_text, whole_words)
                self.mod_model.set_filter(only_diff, search_text, whole_words)
        elif self.radio_table_diff.isChecked():
            if hasattr(self, "diff_model"):
                self.diff_model.set_filter(only_diff, search_text, whole_words)
        self.update_stats()

    def update_stats(self):
        if self.radio_side_by_side.isChecked():
            stats_left = self.org_model.get_stats() if hasattr(self, "org_model") else (0, 0, 0, 0)
            stats_right = self.mod_model.get_stats() if hasattr(self, "mod_model") else (0, 0, 0, 0)
            self.stats_panel.set_labels(self.org_label, self.mod_label)
            self.stats_panel.set_diff_mode(False)
            self.stats_panel.set_values(stats_left, stats_right)
        elif self.radio_table_diff.isChecked():
            stats = self.diff_model.get_stats() if hasattr(self, "diff_model") else (0, 0, 0, 0)
            self.stats_panel.set_labels(self.mod_label, "")
            self.stats_panel.set_diff_mode(True)
            self.stats_panel.set_values(stats)
        else:
            self.stats_panel.set_labels(self.mod_label, "")
            self.stats_panel.set_diff_mode(True)
            self.stats_panel.set_values((0, 0, 0, 0))

    def keyPressEvent(self, event):
        # Zamknij okno ESC
        if event.key() == Qt.Key_Escape:
            self.accept()
        else:
            super().keyPressEvent(event)
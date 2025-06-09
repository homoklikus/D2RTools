import os
import shutil
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
    QMessageBox, QWidget, QSizePolicy, QScrollArea, QGridLayout
)
from PyQt5.QtCore import Qt

PLUGINS_DIR = "Plugins"
ENABLED_FILE = os.path.join(PLUGINS_DIR, "plugins_enabled.txt")

def read_enabled_plugins():
    if not os.path.exists(ENABLED_FILE):
        return set()
    with open(ENABLED_FILE, "r") as f:
        return set(line.strip() for line in f if line.strip())

def write_enabled_plugins(enabled):
    with open(ENABLED_FILE, "w") as f:
        for plugin in sorted(enabled):
            f.write(plugin + "\n")

def load_plugin_info(plugin_folder):
    plugin_py = os.path.join(PLUGINS_DIR, plugin_folder, f"{plugin_folder}.py")
    info = {
        "name": plugin_folder,
        "version": "",
        "desc": "",
        "author": "",
    }
    try:
        with open(plugin_py, "r", encoding="utf-8") as f:
            code = f.read(4096)
        for line in code.splitlines():
            if line.startswith("PLUGIN_NAME"):
                info["name"] = line.split("=", 1)[1].strip().strip('"\'')
            if line.startswith("PLUGIN_VERSION"):
                info["version"] = line.split("=", 1)[1].strip().strip('"\'')
            if line.startswith("PLUGIN_DESCRIPTION"):
                info["desc"] = line.split("=", 1)[1].strip().strip('"\'')
            if line.startswith("PLUGIN_AUTHOR"):
                info["author"] = line.split("=", 1)[1].strip().strip('"\'')
    except Exception:
        pass
    return info

class PluginsManagerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Wtyczki")
        self.setMinimumWidth(560)

        main_layout = QVBoxLayout(self)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        grid = QGridLayout(content)
        scroll.setWidget(content)
        main_layout.addWidget(scroll)

        # Szukaj pluginów jako folderów z plikiem {plugin}/{plugin}.py
        self.plugins = [
            p for p in os.listdir(PLUGINS_DIR)
            if os.path.isdir(os.path.join(PLUGINS_DIR, p))
            and os.path.isfile(os.path.join(PLUGINS_DIR, p, f"{p}.py"))
        ]
        self.enabled = read_enabled_plugins()

        # Nagłówki tabeli
        grid.addWidget(QLabel("<b>Nazwa</b>"), 0, 0)
        grid.addWidget(QLabel("<b>Opis</b>"), 0, 1)
        grid.addWidget(QLabel("<b>Akcja</b>"), 0, 2)

        if not self.plugins:
            empty = QLabel("Brak Wtyczek")
            empty.setStyleSheet("color: #a00; font-weight: bold;")
            main_layout.addWidget(empty)
            return

        for row_num, plugin in enumerate(self.plugins, 1):
            info = load_plugin_info(plugin)

            # Nazwa + autor (w tej samej komórce, autor pod spodem, mniejszą czcionką)
            name = QLabel(
                f"<b>{info['name']}</b>"
                f"<br><span style='color:#888;font-size:10pt;'>{'Wersja: ' + info['version'] if info['version'] else ''}</span>"
                f"<br><span style='font-size:9pt;color:#1a7;'>{'Autor: ' + info['author'] if info['author'] else ''}</span>"
            )
            name.setTextFormat(Qt.RichText)
            name.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            if plugin in self.enabled:
                name.setStyleSheet("font-weight: bold; color: green;")
            else:
                name.setStyleSheet("font-weight: normal; color: #888;")
            grid.addWidget(name, row_num, 0)

            # Opis (zawijany)
            desc = QLabel(info["desc"])
            desc.setWordWrap(True)
            desc.setStyleSheet("color: #444;")
            desc.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            grid.addWidget(desc, row_num, 1)

            # Akcja: Aktywuj/Dezaktywuj, Usuń
            act_row = QHBoxLayout()
            act_btn = QPushButton("Dezaktywuj" if plugin in self.enabled else "Aktywuj")
            act_btn.clicked.connect(lambda _, p=plugin: self.toggle_plugin(p))
            act_row.addWidget(act_btn)

            del_btn = QPushButton("Usuń")
            del_btn.setStyleSheet("background: #e53935; color: white;")
            del_btn.clicked.connect(lambda _, p=plugin: self.remove_plugin(p))
            act_row.addWidget(del_btn)
            act_widget = QWidget()
            act_widget.setLayout(act_row)
            grid.addWidget(act_widget, row_num, 2)

        self.adjustSize()
        self.setMinimumHeight(min(self.height() + 60, 600))

    def toggle_plugin(self, plugin):
        if plugin in self.enabled:
            reply = QMessageBox.question(self, "Potwierdź dezaktywację",
                    f"Dezaktywować wtyczkę {plugin}?", QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.enabled.remove(plugin)
        else:
            reply = QMessageBox.question(self, "Potwierdź aktywację",
                    f"Aktywować wtyczkę {plugin}?", QMessageBox.Yes | QMessageBox.No)
            if reply == QMessageBox.Yes:
                self.enabled.add(plugin)
        write_enabled_plugins(self.enabled)
        self.close()
        dlg = PluginsManagerDialog(self.parent())
        dlg.exec_()

    def remove_plugin(self, plugin):
        reply = QMessageBox.warning(self, "Potwierdź usunięcie",
                f"Na pewno usunąć wtyczkę {plugin}?\nTego nie da się cofnąć!",
                QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            try:
                shutil.rmtree(os.path.join(PLUGINS_DIR, plugin))
                if plugin in self.enabled:
                    self.enabled.remove(plugin)
                    write_enabled_plugins(self.enabled)
            except Exception as e:
                QMessageBox.critical(self, "Błąd", f"Nie udało się usunąć wtyczki: {e}")
            self.close()
            dlg = PluginsManagerDialog(self.parent())
            dlg.exec_()
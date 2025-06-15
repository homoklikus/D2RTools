import difflib
import os
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QCheckBox, QTextEdit, QFrame, QHBoxLayout, QPushButton
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

DIFF_COLOR_ADDED_BG = "#26712b"
DIFF_COLOR_REMOVED_BG = "#8a2121"
DIFF_COLOR_CHANGED_BG = "#7c4700"
DIFF_COLOR_CHANGED_TXT = "#fff"
DIFF_COLOR_NUMBER = "#bbbbbb"

class DiffTextPopup(QDialog):
    def __init__(self, org_file, mod_file, parent=None, filename=None):
        super().__init__(parent)
        self.setWindowTitle("Porównanie plików TXT")
        self.setMinimumSize(1000, 700)
        self.setWindowModality(Qt.ApplicationModal)

        layout = QVBoxLayout(self)
        top = QLabel(
            "<b>Oryginał na górze, Mod na dole</b><br>"
            "Podświetlenie: <span style='background:#26712b;color:#fff;'>dodane</span>, "
            "<span style='background:#8a2121;color:#fff;'>usunięte</span>, "
            "<span style='background:#7c4700;color:#fff;'>zmienione fragmenty</span>"
        )
        top.setTextFormat(Qt.RichText)
        layout.addWidget(top)

        file_display_name = filename or os.path.basename(org_file or mod_file or "")
        if file_display_name:
            layout.addWidget(QLabel(f"<b>Porównywany plik:</b> {file_display_name}"))

        self.chk_only_diff = QCheckBox("Pokaż tylko zmiany")
        self.chk_only_diff.setChecked(False)
        self.chk_only_diff.stateChanged.connect(self.refresh)
        layout.addWidget(self.chk_only_diff)

        self.org_lines = self.load_lines(org_file)
        self.mod_lines = self.load_lines(mod_file)

        self.org_label = QLabel("<b>Oryginał</b>")
        layout.addWidget(self.org_label)
        self.org_text = QTextEdit()
        self.org_text.setReadOnly(True)
        self.org_text.setFont(QFont("Consolas, Courier New, Monospace", 11))
        layout.addWidget(self.org_text)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        layout.addWidget(sep)

        self.mod_label = QLabel("<b>Mod</b>")
        layout.addWidget(self.mod_label)
        self.mod_text = QTextEdit()
        self.mod_text.setReadOnly(True)
        self.mod_text.setFont(QFont("Consolas, Courier New, Monospace", 11))
        layout.addWidget(self.mod_text)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn = QPushButton("Zamknij")
        btn.clicked.connect(self.accept)
        btn_row.addWidget(btn)
        layout.addLayout(btn_row)

        self.refresh()
        self.activateWindow()
        self.raise_()
        self.setFocus()

    def load_lines(self, filename):
        if not filename:
            return []
        try:
            with open(filename, "r", encoding="utf-8-sig") as f:
                return [line.rstrip("\n\r") for line in f]
        except Exception as e:
            return [f"Błąd wczytywania pliku: {e}"]

    def refresh(self):
        only_diff = self.chk_only_diff.isChecked()
        org_html, mod_html = self.render_diff(self.org_lines, self.mod_lines, only_diff=only_diff)
        self.org_text.setHtml(org_html)
        self.mod_text.setHtml(mod_html)

    def render_diff(self, org_lines, mod_lines, only_diff=False):
        sm = difflib.SequenceMatcher(None, org_lines, mod_lines)
        org_html_lines = []
        mod_html_lines = []
        org_line_idx = 0
        mod_line_idx = 0
        diff_mask = []
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            if tag == "equal":
                for l in range(i2 - i1):
                    o_num = org_line_idx + 1
                    m_num = mod_line_idx + 1
                    line = org_lines[i1 + l]
                    org_html_lines.append(self.fmt_line(o_num, line))
                    mod_html_lines.append(self.fmt_line(m_num, line))
                    diff_mask.append(False)
                    org_line_idx += 1
                    mod_line_idx += 1
            elif tag == "replace":
                for l in range(max(i2 - i1, j2 - j1)):
                    o_num = org_line_idx + 1 if org_line_idx < len(org_lines) else ""
                    m_num = mod_line_idx + 1 if mod_line_idx < len(mod_lines) else ""
                    org_line = org_lines[i1 + l] if i1 + l < i2 else ""
                    mod_line = mod_lines[j1 + l] if j1 + l < j2 else ""
                    if org_line and mod_line:
                        o, m = self.inline_diff(org_line, mod_line)
                        org_html_lines.append(self.fmt_line(o_num, o, DIFF_COLOR_CHANGED_BG, fg=DIFF_COLOR_CHANGED_TXT))
                        mod_html_lines.append(self.fmt_line(m_num, m, DIFF_COLOR_CHANGED_BG, fg=DIFF_COLOR_CHANGED_TXT))
                        diff_mask.append(True)
                        org_line_idx += 1
                        mod_line_idx += 1
                    elif org_line:
                        org_html_lines.append(self.fmt_line(o_num, org_line, DIFF_COLOR_REMOVED_BG, fg=DIFF_COLOR_CHANGED_TXT, deleted=True))
                        mod_html_lines.append(self.fmt_line("", ""))
                        diff_mask.append(True)
                        org_line_idx += 1
                    elif mod_line:
                        org_html_lines.append(self.fmt_line("", ""))
                        mod_html_lines.append(self.fmt_line(m_num, mod_line, DIFF_COLOR_ADDED_BG, fg=DIFF_COLOR_CHANGED_TXT, added=True))
                        diff_mask.append(True)
                        mod_line_idx += 1
            elif tag == "delete":
                for l in range(i2 - i1):
                    o_num = org_line_idx + 1
                    line = org_lines[i1 + l]
                    org_html_lines.append(self.fmt_line(o_num, line, DIFF_COLOR_REMOVED_BG, fg=DIFF_COLOR_CHANGED_TXT, deleted=True))
                    mod_html_lines.append(self.fmt_line("", ""))
                    diff_mask.append(True)
                    org_line_idx += 1
            elif tag == "insert":
                for l in range(j2 - j1):
                    m_num = mod_line_idx + 1
                    line = mod_lines[j1 + l]
                    org_html_lines.append(self.fmt_line("", ""))
                    mod_html_lines.append(self.fmt_line(m_num, line, DIFF_COLOR_ADDED_BG, fg=DIFF_COLOR_CHANGED_TXT, added=True))
                    diff_mask.append(True)
                    mod_line_idx += 1

        if only_diff:
            org_html_lines = [l for l, d in zip(org_html_lines, diff_mask) if d]
            mod_html_lines = [l for l, d in zip(mod_html_lines, diff_mask) if d]

        org_html = "<pre style='font-family:monospace;font-size:12px;margin:0'>" + "\n".join(org_html_lines) + "</pre>"
        mod_html = "<pre style='font-family:monospace;font-size:12px;margin:0'>" + "\n".join(mod_html_lines) + "</pre>"
        return org_html, mod_html

    def inline_diff(self, a, b):
        sm = difflib.SequenceMatcher(None, a, b)
        a_frag = []
        b_frag = []
        for tag, i1, i2, j1, j2 in sm.get_opcodes():
            a_sub = a[i1:i2].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            b_sub = b[j1:j2].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            if tag == "equal":
                a_frag.append(a_sub)
                b_frag.append(b_sub)
            else:
                if a_sub:
                    a_frag.append(f"<span style='background:{DIFF_COLOR_CHANGED_BG};color:{DIFF_COLOR_CHANGED_TXT};font-weight:bold'>{a_sub}</span>")
                if b_sub:
                    b_frag.append(f"<span style='background:{DIFF_COLOR_CHANGED_BG};color:{DIFF_COLOR_CHANGED_TXT};font-weight:bold'>{b_sub}</span>")
        return "".join(a_frag), "".join(b_frag)

    def fmt_line(self, lineno, text, bgcolor=None, fg=None, added=False, deleted=False, border=False):
        num = f"{lineno:>4}" if lineno != "" else "    "
        style = ""
        if bgcolor:
            style += f"background:{bgcolor};"
        if fg:
            style += f"color:{fg};"
        if deleted:
            style += "text-decoration:line-through;"
        if added:
            style += "font-weight:bold;"
        return f"<span style='color:{DIFF_COLOR_NUMBER};'>{num}</span> <span style='{style}'>{text}</span>"
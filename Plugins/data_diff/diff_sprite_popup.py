import os
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt5.QtCore import Qt

def load_sprite(filename):
    import struct
    from PIL import Image
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
    raw = data[offset : offset + frame_size]
    img = Image.frombytes("RGBA", (width, height), raw)
    return img

class SpriteDiffPopup(QDialog):
    def __init__(self, org_file, mod_file, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Porównanie plików .sprite")
        self.setMinimumSize(960, 600)
        self.setWindowModality(Qt.ApplicationModal)

        main = QVBoxLayout(self)
        layout = QHBoxLayout()
        self.org_label = QLabel()
        self.org_label.setAlignment(Qt.AlignCenter)
        self.mod_label = QLabel()
        self.mod_label.setAlignment(Qt.AlignCenter)

        org_info = self._sprite_to_pixmap(org_file, self.org_label, "oryginału")
        mod_info = self._sprite_to_pixmap(mod_file, self.mod_label, "moda")

        vleft = QVBoxLayout()
        vleft.addWidget(QLabel("<b>Oryginał</b>", alignment=Qt.AlignCenter))
        vleft.addWidget(self.org_label)
        vright = QVBoxLayout()
        vright.addWidget(QLabel("<b>Mod</b>", alignment=Qt.AlignCenter))
        vright.addWidget(self.mod_label)
        layout.addLayout(vleft)
        layout.addLayout(vright)
        main.addLayout(layout)

        if org_info or mod_info:
            dim_label = QLabel(f"<i>{org_info or ''}   {mod_info or ''}</i>")
            dim_label.setAlignment(Qt.AlignCenter)
            main.addWidget(dim_label)

        btn = QPushButton("Zamknij")
        btn.clicked.connect(self.accept)
        main.addWidget(btn)
        self.setLayout(main)

        self.activateWindow()
        self.raise_()
        self.setFocus()

    def _sprite_to_pixmap(self, sprite_path, label, label_side):
        from PyQt5.QtGui import QImage, QPixmap
        if not sprite_path or not os.path.isfile(sprite_path):
            label.setText("Brak pliku")
            return None
        try:
            img = load_sprite(sprite_path)
            width, height = img.size
            qimg = self.pil_to_qimage(img)
            label.setPixmap(qimg.scaled(400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            return f"{label_side.capitalize()}: {width}x{height}px"
        except Exception as e:
            label.setText(f"Błąd ładowania sprite:\n{e}")
            return None

    def pil_to_qimage(self, pil_img):
        from PyQt5.QtGui import QImage, QPixmap
        if pil_img.mode != "RGBA":
            pil_img = pil_img.convert("RGBA")
        data = pil_img.tobytes("raw", "RGBA")
        qimg = QImage(data, pil_img.width, pil_img.height, QImage.Format_RGBA8888)
        return QPixmap.fromImage(qimg)
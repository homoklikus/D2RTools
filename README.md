# D2RTools – Edytor TXT/JSON z systemem wtyczek do modowania Diablo II: Resurrected

**Autorzy:** Precell & ChatGPT  
**Repozytorium:** [https://github.com/homoklikus/D2RTools](https://github.com/homoklikus/D2RTools)

---

## 🔥 Co to jest?

**D2RTools** to nowoczesny, multiplatformowy edytor plików TXT (wkrótce) i JSON używanych w modowaniu Diablo II: Resurrected (D2R),  
stworzony z myślą o społeczności modderów.  
Program działa na systemach Windows oraz Linux, pozwala na wygodną edycję, wizualizację i wyszukiwanie zależności w plikach moda.

---

## 🏆 Główne funkcje

- **Czytelny GUI** – szybki podgląd i edycja plików JSON oraz TXT (wkrótce) w stylu D2R
- **System zakładek** – otwieraj wiele plików na raz
- **Paginacja i wyszukiwarka** – płynna praca z dużymi plikami
- **System wtyczek (Plugins)** – łatwo rozszerzaj funkcjonalność o własne pluginy
- **Manager wtyczek** – aktywuj, dezaktywuj i usuwaj pluginy przez wygodne menu
- **Plugin „Znajdź zależności”** – przeszukuj cały folder moda (.mpq) po ID/Key w JSON i TXT (z numerami linii!)
- **Własna czcionka D2R** – pełna kompatybilność z ikonami i kolorami gry
- **Wieloplatformowość** – testowane na Linux (Debian 12 z KDE Plasma), Windows 10/11

---

## 🖥️ Instalacja i uruchamianie

1. **Wymagania:**
    - Python 3.8+  
    - PyQt5 (`pip install PyQt5`)
2. **Klonowanie repozytorium:**
    ```bash
    git clone https://github.com/homoklikus/D2RTools.git
    cd D2RTools
    ```
3. **Uruchamianie:**
    - **Linux:**  
      ```bash
      python3 main.py
      ```
    - **Windows:**  
      Otwórz `main.py` w Pythonie lub użyj pliku .bat

---

## 🔌 System wtyczek (Plugins)

- **Wszystkie pluginy wrzucasz do folderu `Plugins/`**
- Każdy plugin to plik `.py` z nagłówkiem:
    ```python
    PLUGIN_NAME = "..."
    PLUGIN_VERSION = "..."
    PLUGIN_DESCRIPTION = "..."
    PLUGIN_AUTHOR = "..."
    PLUGIN_OK = True

    def register_plugin(main_window):
        # integracja z głównym GUI
    ```
- Aktywacja wtyczek przez menadżer (menu Opcje → Wtyczki)
- Przykładowy plugin: **Znajdź zależności** (szuka ID/Key w całym modzie, podaje numery linii i ścieżki do plików)

---

## 📚 FAQ

**Q: Jak dodać własny plugin?**  
A: Skopiuj przykładową wtyczkę, uzupełnij nagłówek oraz kod wtyczki, wrzuć do `Plugins/`, aktywuj przez menu.

**Q: Czy program działa na Steam Deck, Mac, etc.?**  
A: PyQt5 i Python są multiplatformowe – wystarczy doinstalować wymagane biblioteki.

**Q: Mam pomysł/błąd/feature request!**  
A: Śmiało wrzuć issue albo skontaktuj się na Discordzie społeczności D2R.

---

## 🛡️ Licencja

Open source, MIT.  
Możesz korzystać, rozwijać, forkujesz na własne potrzeby.

---

## 🏅 Kontakt / Społeczność

- **Repozytorium:** [https://github.com/homoklikus/D2RTools](https://github.com/homoklikus/D2RTools)
- **Autorzy:** Precell & ChatGPT
- **Discord społeczności Diablo 2 Resurrected:** *https://discord.com/channels/837488572838838292/1369381899260133527*

---

*Szczęśliwego Modowania :-)!*

# D2RTools – TXT/JSON Editor with Plugin System for Diablo II: Resurrected Modding

**Authors:** Precell & ChatGPT  
**Repository:** [https://github.com/homoklikus/D2RTools](https://github.com/homoklikus/D2RTools)

---

## 🔥 What is it?

**D2RTools** is a modern, multiplatform editor for TXT (coming soon) and JSON files used in Diablo II: Resurrected (D2R) modding,  
created with the modding community in mind.  
The program works on Windows and Linux, allowing convenient editing, visualization, and searching for dependencies in mod files.

---

## 🏆 Main Features

- **User-friendly GUI** – quick preview and editing of JSON and TXT files (TXT editing – coming soon!) in D2R style
- **Tab system** – open and work with multiple files at once
- **Pagination and search** – smooth handling of large files
- **Plugin system (Plugins)** – easily extend the functionality with your own plugins
- **Plugin manager** – activate, deactivate, and remove plugins via a convenient menu
- **"Find Dependencies" plugin** – search the entire mod folder (.mpq) for ID/Key in JSON and TXT (with line numbers!)
- **Custom D2R font** – full compatibility with in-game icons and colors
- **Cross-platform** – tested on Linux (Debian 12 with KDE Plasma), Windows 10/11

---

## 🖥️ Installation and Running

1. **Requirements:**
    - Python 3.8+  
    - PyQt5 (`pip install PyQt5`)
2. **Clone the repository:**
    ```bash
    git clone https://github.com/homoklikus/D2RTools.git
    cd D2RTools
    ```
3. **Run:**
    - **Linux:**  
      ```bash
      python3 main.py
      ```
    - **Windows:**  
      Open `main.py` with Python or use a .bat file

---

## 🔌 Plugin System (Plugins)

- **Put all plugins into the `Plugins/` folder**
- Each plugin is a `.py` file with a header:
    ```python
    PLUGIN_NAME = "..."
    PLUGIN_VERSION = "..."
    PLUGIN_DESCRIPTION = "..."
    PLUGIN_AUTHOR = "..."
    PLUGIN_OK = True

    def register_plugin(main_window):
        # integration with the main GUI
    ```
- Activate plugins through the manager (menu Options → Plugins)
- Example plugin: **Find Dependencies** (searches for ID/Key throughout the mod, shows line numbers and file paths)

---

## 📚 FAQ

**Q: How do I add my own plugin?**  
A: Copy the example plugin, fill in the header and the code, put it into `Plugins/`, and activate it through the menu.

**Q: Does the program work on Steam Deck, Mac, etc.?**  
A: PyQt5 and Python are cross-platform – just install the required libraries.

**Q: I have an idea/bug/feature request!**  
A: Feel free to open an issue or contact us on the D2R community Discord.

---

## 🛡️ License

Open source, MIT.  
You can use, develop, and fork it for your own needs.

---

## 🏅 Contact / Community

- **Repository:** [https://github.com/homoklikus/D2RTools](https://github.com/homoklikus/D2RTools)
- **Authors:** Precell & ChatGPT
- **Diablo 2 Resurrected community Discord:** *https://discord.com/channels/837488572838838292/1369381899260133527*

---

*Happy Modding! :-)*


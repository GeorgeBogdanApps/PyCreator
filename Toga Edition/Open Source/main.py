import toga
from toga.style.pack import COLUMN, ROW, CENTER, BOLD, HIDDEN, VISIBLE, Pack
import threading
import subprocess
import os
import sys
import io
import pathlib

# Define constants for a refined, dark, and elegant theme
COLOR_BACKGROUND = '#0A0A0A'
COLOR_PANEL = '#1F1F1F'
COLOR_ACCENT = '#00C4FF'
COLOR_TEXT_PRIMARY = '#EFEFEF'
COLOR_ERROR = '#FF6347'
COLOR_WARNING = '#FFD700'


class FileView(toga.Box):
    """
    Represents a single file in the tabbed editor.
    """

    def __init__(self, app, filepath=None, **kwargs):
        super().__init__(style=Pack(direction=COLUMN, flex=1, margin=10), **kwargs)
        self.app = app
        self.filepath = filepath
        self.editor = toga.MultilineTextInput(
            placeholder="Introduceți codul aici...",
            style=Pack(flex=1, margin=10, padding=10, background_color=COLOR_PANEL, color=COLOR_TEXT_PRIMARY,
                       font_family='monospace', font_size=14)
        )
        self.add(self.editor)
        if filepath and isinstance(filepath, pathlib.Path) and filepath.exists():
            try:
                with filepath.open("r", encoding="utf-8") as f:
                    self.editor.value = f.read()
            except Exception as e:
                self.app.update_console(f"Eroare la deschiderea fișierului {filepath}: {e}")

        self.update_title()

    def update_title(self):
        """
        Update the parent app title based on the file path.
        """
        if self.filepath:
            self.app.main_window.title = f'BeeWare IDE - {self.filepath.name}'
        else:
            self.app.main_window.title = 'BeeWare IDE - Untitled'


class IDEApp(toga.App):
    """
    Main application class for the Toga IDE.
    Manages the overall application state, windows, and core UI.
    """

    def startup(self):
        """
        Creates the main window and UI components for the IDE.
        """
        self.tabs_list = []
        self.current_tab_index = -1

        self.main_box, self.content_container, self.tabs_container, \
            self.console_output, self.command_input, self.package_input, self.splitter = self._create_ui()

        self.main_window = toga.MainWindow(title='BeeWare IDE', size=(800, 600))
        self.main_window.content = self.main_box
        self.main_window.show()

        self.new_file(None)

    def _create_ui(self):
        """
        Creates the main UI layout for the application.
        """
        main_box = toga.Box(style=Pack(direction=COLUMN, background_color=COLOR_BACKGROUND))

        # --- Top Bar with Tabs ---
        tabs_bar = toga.Box(
            style=Pack(direction=ROW, height=50, background_color=COLOR_PANEL, margin_top=5))
        tabs_container = toga.Box(style=Pack(direction=ROW, flex=1))
        tabs_bar.add(tabs_container)
        main_box.add(tabs_bar)

        # --- Main UI Layout with Splitter ---
        splitter = toga.SplitContainer(style=Pack(flex=1, direction=COLUMN))

        # Top pane: Code Editor
        content_container = toga.Box(style=Pack(direction=COLUMN, flex=1))

        # Bottom pane: Console and Problems
        bottom_panel = toga.Box(
            style=Pack(direction=COLUMN, background_color=COLOR_PANEL, margin=5))

        # Command input
        command_input = toga.TextInput(placeholder="Introduceți comenzi aici (ex: 'run', 'save')",
                                       style=Pack(height=40, background_color=COLOR_PANEL,
                                                  color=COLOR_TEXT_PRIMARY, margin=5))
        command_input.on_confirm = self.process_command

        # Console output
        console_output = toga.MultilineTextInput(
            readonly=True,
            style=Pack(flex=1, margin=5, padding=5, background_color=COLOR_PANEL, color=COLOR_TEXT_PRIMARY))

        bottom_panel.add(console_output)
        bottom_panel.add(command_input)

        splitter.content = [content_container, bottom_panel]
        main_box.add(splitter)

        # --- Bottom Buttons ---
        btn_layout = toga.Box(style=Pack(direction=ROW, margin=10, align_items=CENTER))

        new_btn = toga.Button("Fișier nou", on_press=self.new_file,
                              style=Pack(flex=1, background_color=COLOR_PANEL, color=COLOR_TEXT_PRIMARY))
        open_btn = toga.Button("Deschide", on_press=self.open_file,
                               style=Pack(flex=1, background_color=COLOR_PANEL, color=COLOR_TEXT_PRIMARY))
        save_btn = toga.Button("Salvează", on_press=self.save_file,
                               style=Pack(flex=1, background_color=COLOR_PANEL, color=COLOR_TEXT_PRIMARY))
        close_btn = toga.Button("Închide", on_press=self.close_file,
                                style=Pack(flex=1, background_color=COLOR_PANEL, color=COLOR_TEXT_PRIMARY))
        run_btn = toga.Button("Rulează", on_press=self.run_code,
                              style=Pack(flex=1, background_color=COLOR_ACCENT, color=COLOR_PANEL))

        # New input for packages
        package_input = toga.TextInput(placeholder="Pachete de instalat (ex: 'requests numpy')",
                                       style=Pack(flex=1, background_color=COLOR_PANEL, color=COLOR_TEXT_PRIMARY))

        install_btn = toga.Button("Instalează", on_press=self.install_dependencies,
                                  style=Pack(width=120, background_color=COLOR_ACCENT, color=COLOR_PANEL))

        btn_layout.add(new_btn)
        btn_layout.add(toga.Box(style=Pack(width=10)))
        btn_layout.add(open_btn)
        btn_layout.add(toga.Box(style=Pack(width=10)))
        btn_layout.add(save_btn)
        btn_layout.add(toga.Box(style=Pack(width=10)))
        btn_layout.add(close_btn)
        btn_layout.add(toga.Box(style=Pack(width=10)))
        btn_layout.add(run_btn)
        btn_layout.add(toga.Box(style=Pack(width=10)))
        btn_layout.add(package_input)
        btn_layout.add(toga.Box(style=Pack(width=10)))
        btn_layout.add(install_btn)

        main_box.add(btn_layout)

        return main_box, content_container, tabs_container, console_output, command_input, package_input, splitter

    def get_current_tab(self):
        """
        Returns the currently active FileView instance.
        """
        if 0 <= self.current_tab_index < len(self.tabs_list):
            return self.tabs_list[self.current_tab_index]
        return None

    def process_command(self, widget):
        """
        Processes a command from the command input field.
        """
        command = widget.value.strip().lower()
        widget.value = ""
        self.update_console(f"> {command}", append=True)

        if command == "run":
            self.run_code(None)
        elif command == "save":
            self.save_file(None)
        elif command == "new":
            self.new_file(None)
        elif command == "close":
            self.close_file(None)
        elif command == "install":
            self.install_dependencies(None)
        elif command.startswith("save as "):
            filepath = command.split(" ", 2)[-1].strip()
            self.save_file(filepath)
        elif command.startswith("open "):
            filepath = command.split(" ", 1)[-1].strip()
            self.open_file(filepath)
        elif command == "help":
            self.update_console(
                "Comenzi disponibile:\n  - new\n  - save\n  - save as <cale>\n  - open <cale>\n  - run\n  - close\n  - install",
                append=True)
        else:
            self.update_console(f"Eroare: Comandă necunoscută '{command}'.", append=True)
            self.update_console(f"Tastați 'help' pentru o listă de comenzi.")

    def new_file(self, widget):
        """
        Creates a new empty tab.
        """
        new_tab = FileView(self)
        self.tabs_list.append(new_tab)
        self.content_container.add(new_tab)
        self.switch_tab(len(self.tabs_list) - 1)
        self.update_console("Fișier nou creat.")

    async def open_file(self, widget):
        """
        Opens a file using a native file dialog.
        """
        try:
            file_paths = await self.main_window.open_file_dialog("Deschide fișier")
            if file_paths:
                file_path = file_paths[0]
                new_tab = FileView(self, filepath=file_path)
                self.tabs_list.append(new_tab)
                self.content_container.add(new_tab)
                self.switch_tab(len(self.tabs_list) - 1)
                self.update_console(f"Fișier deschis: {file_path}")
        except Exception as e:
            self.update_console(f"Eroare la deschiderea fișierului: {e}")

    async def save_file(self, widget):
        """
        Saves the current file, prompting for a path if needed.
        """
        current_tab = self.get_current_tab()
        if not current_tab:
            return

        try:
            if not current_tab.filepath:
                filepath = await self.main_window.save_file_dialog(
                    title="Salvează fișier",
                    suggested_filename="untitled.py"
                )
                if not filepath:
                    return
                current_tab.filepath = filepath

            if current_tab.filepath:
                with open(current_tab.filepath, "w", encoding="utf-8") as f:
                    f.write(current_tab.editor.value)
                self.update_console(f"Fișier salvat: {current_tab.filepath}")
                current_tab.update_title()
                self.update_tabs_bar()

        except Exception as e:
            self.update_console(f"Eroare la salvarea fișierului: {e}")

    def close_file(self, widget):
        """
        Closes the current file tab.
        """
        current_view = self.get_current_tab()
        if not current_view:
            return

        if len(self.tabs_list) > 1:
            self.content_container.remove(current_view)
            del self.tabs_list[self.current_tab_index]
            self.current_tab_index = min(self.current_tab_index, len(self.tabs_list) - 1)
            self.switch_tab(self.current_tab_index)
            self.update_console(f"Fișier închis.")
        elif len(self.tabs_list) == 1:
            self.update_console("Nu se poate închide ultima filă. Creați un fișier nou.")

    def run_code(self, widget):
        """
        Runs the Python code by executing it in the current process.
        """
        current_tab = self.get_current_tab()
        if not current_tab:
            return

        self.update_console("Se rulează codul...", append=True)

        def worker():
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            redirected_stdout = io.StringIO()
            redirected_stderr = io.StringIO()

            try:
                sys.stdout = redirected_stdout
                sys.stderr = redirected_stderr
                exec(current_tab.editor.value, {})
                output = redirected_stdout.getvalue()
                error_output = redirected_stderr.getvalue()
            except Exception as e:
                error_output = f"Eroare: {e}\n"
            finally:
                sys.stdout = old_stdout
                sys.stderr = old_stderr

            final_output = output + error_output
            self.app.loop.call_soon_threadsafe(lambda: self.update_console(final_output, append=True))

        threading.Thread(target=worker, daemon=True).start()

    def install_dependencies(self, widget):
        """
        Installs dependencies using pip from the package input field.
        """
        packages_string = self.package_input.value.strip()
        if not packages_string:
            self.update_console("Eroare: Nu s-au introdus pachete de instalat.", append=True)
            return

        packages = packages_string.split()
        self.update_console(f"Se instalează pachetele: {', '.join(packages)}...", append=True)

        def worker():
            try:
                command = [sys.executable, "-m", "pip", "install"] + packages
                process = subprocess.Popen(
                    command,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8"
                )
                stdout, stderr = process.communicate()

                if process.returncode == 0:
                    self.app.loop.call_soon_threadsafe(
                        lambda: self.update_console(f"Instalare reușită:\n{stdout}", append=True))
                else:
                    self.app.loop.call_soon_threadsafe(
                        lambda: self.update_console(f"Instalare eșuată:\n{stderr}", append=True))

            except Exception as e:
                self.app.loop.call_soon_threadsafe(
                    lambda: self.update_console(f"Eroare în timpul instalării: {e}", append=True))

        threading.Thread(target=worker, daemon=True).start()

    def switch_tab(self, index):
        """
        Switches the currently visible tab.
        """
        if 0 <= index < len(self.tabs_list):
            self.current_tab_index = index
            for i, tab_view in enumerate(self.tabs_list):
                tab_view.style.visibility = VISIBLE if i == index else HIDDEN

            self.content_container.clear()
            for tab_view in self.tabs_list:
                self.content_container.add(tab_view)

            current_view = self.tabs_list[self.current_tab_index]
            current_view.update_title()
            self.update_tabs_bar()

    def update_tabs_bar(self):
        """
        Updates the visual representation of the tabs in the top bar.
        """
        self.tabs_container.clear()
        for i, tab_view in enumerate(self.tabs_list):
            tab_name = tab_view.filepath.name if tab_view.filepath else f"Untitled {i + 1}"
            tab_button = toga.Button(tab_name, on_press=lambda w, i=i: self.switch_tab(i))
            if i == self.current_tab_index:
                tab_button.style.background_color = COLOR_ACCENT
                tab_button.style.color = COLOR_PANEL
            else:
                tab_button.style.background_color = COLOR_PANEL
                tab_button.style.color = COLOR_TEXT_PRIMARY
            self.tabs_container.add(tab_button)

    def update_console(self, text, append=False):
        """
        Updates the console output text.
        """
        if append:
            self.console_output.value += "\n" + text
        else:
            self.console_output.value = text


def main():
    return IDEApp('My IDE', 'org.beeware.myide')


if __name__ == '__main__':
    main().main_loop()

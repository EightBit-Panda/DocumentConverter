
import customtkinter as ctk

from tkinter import filedialog, messagebox
from tkinterdnd2 import TkinterDnD, DND_FILES

import os
import sys
from pathlib import Path
from queue import Queue, Empty

from core.conversion_worker import ConversionWorker


# ==================================================
# APPLICATION CONFIGURATION
# ==================================================

APP_NAME = "DocumentConverter"
APP_VERSION = "1.0.0"


def resource_path(relative_path):
    """Return an asset path that works both in development and PyInstaller builds."""
    base_path = Path(
        getattr(sys, "_MEIPASS", Path(__file__).resolve().parent)
    )
    return base_path / relative_path


WINDOW_WIDTH = 1000
WINDOW_HEIGHT = 760

SUPPORTED_EXTENSIONS = {
    ".docx", ".doc",
    ".odt", ".rtf", ".txt",
    ".xlsx", ".xls", ".ods", ".csv",
    ".pptx", ".ppt", ".odp",
    ".pdf",
    ".html", ".htm"
}


# Output formats supported for each input document category.
# The GUI displays only formats compatible with every selected file.
INPUT_CATEGORIES = {
    "word": {
        ".docx", ".doc", ".odt", ".rtf", ".txt"
    },
    "spreadsheet": {
        ".xlsx", ".xls", ".ods", ".csv"
    },
    "presentation": {
        ".pptx", ".ppt", ".odp"
    },
    "web": {
        ".html", ".htm"
    }
}

OUTPUT_FORMATS_BY_CATEGORY = {
    "word": ["PDF", "DOCX", "ODT", "RTF", "TXT", "HTML"],
    "spreadsheet": ["PDF", "XLSX", "ODS", "CSV", "HTML"],
    "presentation": ["PDF", "PPTX", "ODP"],
    "web": ["PDF", "HTML"]
}

OUTPUT_FORMAT_ORDER = [
    "PDF", "DOCX", "ODT", "RTF", "TXT",
    "HTML", "XLSX", "ODS", "CSV", "PPTX", "ODP"
]


# ==================================================
# MAIN APPLICATION
# ==================================================

class DocumentConverterApp(TkinterDnD.Tk):

    def __init__(self):

        super().__init__()

        self.title(f"{APP_NAME} v{APP_VERSION}")
        self.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.minsize(850, 650)
        self.configure(bg="#242424")

        # Application icon (also works when packaged with PyInstaller).
        icon_path = resource_path(Path("assets") / "icons" / "documentconverter.ico")
        if icon_path.is_file():
            try:
                self.iconbitmap(str(icon_path))
            except Exception as error:
                print(f"Could not load application icon: {error}")

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.files = []
        self.file_rows = {}
        self.file_status_labels = {}
        self.file_status = {}
        self.converted_outputs = {}
        self.file_output_formats = {}
        self.file_output_menus = {}

        self.selected_file = None

        self.output_dir = Path.cwd() / "converted"

        self.worker = None
        self.event_queue = Queue()
        self.is_converting = False

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.create_header()
        self.create_main_area()
        self.create_footer()

        self.drop_target_register(DND_FILES)
        self.dnd_bind("<<Drop>>", self.handle_drop)

        self.refresh_file_list()

    # ==================================================
    # HEADER
    # ==================================================

    def create_header(self):

        header = ctk.CTkFrame(self, corner_radius=0)
        header.grid(row=0, column=0, sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="DocumentConverter",
            font=ctk.CTkFont(size=26, weight="bold")
        ).grid(
            row=0, column=0,
            padx=25, pady=(20, 5),
            sticky="w"
        )

        ctk.CTkLabel(
            header,
            text="Convert your documents easily",
            text_color="gray"
        ).grid(
            row=1, column=0,
            padx=27, pady=(0, 20),
            sticky="w"
        )

    # ==================================================
    # MAIN AREA
    # ==================================================

    def create_main_area(self):

        main = ctk.CTkFrame(self, fg_color="transparent")

        main.grid(
            row=1, column=0,
            padx=25, pady=15,
            sticky="nsew"
        )

        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=1)

        # ----------------------------------------------
        # DROP AREA
        # ----------------------------------------------

        self.drop_area = ctk.CTkFrame(
            main,
            height=125,
            border_width=2,
            border_color="#3478C8",
            corner_radius=12
        )

        self.drop_area.grid(
            row=0, column=0,
            sticky="ew", pady=(0, 12)
        )

        self.drop_area.grid_propagate(False)

        ctk.CTkLabel(
            self.drop_area,
            text="Drag and drop documents here",
            font=ctk.CTkFont(size=20, weight="bold")
        ).place(
            relx=0.5, rely=0.32,
            anchor="center"
        )

        ctk.CTkLabel(
            self.drop_area,
            text="DOCX • DOC • XLSX • ODS • PPTX • ODP • ODT • RTF • PDF",
            text_color="gray"
        ).place(
            relx=0.5, rely=0.53,
            anchor="center"
        )

        self.add_button = ctk.CTkButton(
            self.drop_area,
            text="Add files",
            width=130,
            command=self.add_files
        )

        self.add_button.place(
            relx=0.5, rely=0.79,
            anchor="center"
        )

        # ----------------------------------------------
        # FILE LIST
        # ----------------------------------------------

        self.file_frame = ctk.CTkFrame(
            main,
            corner_radius=10
        )

        self.file_frame.grid(
            row=1, column=0,
            sticky="nsew", pady=(0, 12)
        )

        self.file_frame.grid_columnconfigure(0, weight=1)
        self.file_frame.grid_rowconfigure(1, weight=1)

        toolbar = ctk.CTkFrame(
            self.file_frame,
            fg_color="transparent"
        )

        toolbar.grid(
            row=0, column=0,
            padx=15, pady=10,
            sticky="ew"
        )

        toolbar.grid_columnconfigure(0, weight=1)

        self.file_title = ctk.CTkLabel(
            toolbar,
            text="Files to convert (0)",
            font=ctk.CTkFont(size=16, weight="bold")
        )

        self.file_title.grid(
            row=0, column=0,
            sticky="w"
        )

        self.remove_button = ctk.CTkButton(
            toolbar,
            text="Remove",
            width=90,
            fg_color="transparent",
            border_width=1,
            command=self.remove_selected
        )

        self.remove_button.grid(
            row=0, column=1,
            padx=5
        )

        self.clear_button = ctk.CTkButton(
            toolbar,
            text="Clear all",
            width=90,
            fg_color="transparent",
            border_width=1,
            command=self.clear_files
        )

        self.clear_button.grid(
            row=0, column=2
        )

        self.file_list = ctk.CTkScrollableFrame(
            self.file_frame,
            fg_color="transparent"
        )

        self.file_list.grid(
            row=1, column=0,
            padx=10, pady=(0, 10),
            sticky="nsew"
        )

        # ----------------------------------------------
        # OUTPUT SETTINGS
        # ----------------------------------------------

        settings = ctk.CTkFrame(
            main,
            corner_radius=10
        )

        settings.grid(
            row=2, column=0,
            sticky="ew", pady=(0, 12)
        )

        settings.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            settings,
            text="Output folder:",
            font=ctk.CTkFont(weight="bold")
        ).grid(
            row=0, column=0,
            padx=12, pady=12
        )

        self.output_label = ctk.CTkLabel(
            settings,
            text=str(self.output_dir),
            anchor="w",
            text_color="gray"
        )

        self.output_label.grid(
            row=0, column=1,
            padx=8, sticky="ew"
        )

        self.browse_button = ctk.CTkButton(
            settings,
            text="Browse",
            width=90,
            command=self.select_output_folder
        )

        self.browse_button.grid(
            row=0, column=2,
            padx=(8, 5), pady=12
        )

        self.open_output_button = ctk.CTkButton(
            settings,
            text="Open folder",
            width=110,
            fg_color="transparent",
            border_width=1,
            command=self.open_output_folder
        )

        self.open_output_button.grid(
            row=0, column=3,
            padx=(5, 5), pady=12
        )

        self.open_converted_button = ctk.CTkButton(
            settings,
            text="Open converted file",
            width=155,
            fg_color="transparent",
            border_width=1,
            state="disabled",
            command=self.open_converted_file
        )

        self.open_converted_button.grid(
            row=0, column=4,
            padx=(5, 12), pady=12
        )

        # ----------------------------------------------
        # FORMAT AND CONVERSION CONTROLS
        # ----------------------------------------------

        controls = ctk.CTkFrame(
            main,
            corner_radius=10
        )

        controls.grid(
            row=3, column=0,
            sticky="ew", pady=(0, 12)
        )

        controls.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(
            controls,
            text="Apply to all:",
            font=ctk.CTkFont(weight="bold")
        ).grid(
            row=0, column=0,
            padx=(15, 5), pady=12
        )

        self.output_format = ctk.CTkOptionMenu(
            controls,
            values=["PDF"],
            width=115
        )
        self.output_format.grid(
            row=0, column=1,
            padx=5, pady=(12, 4),
            sticky="w"
        )

        self.apply_all_button = ctk.CTkButton(
            controls,
            text="Apply",
            width=75,
            command=self.apply_format_to_all
        )
        self.apply_all_button.grid(
            row=0, column=2,
            padx=5, pady=12
        )

        self.format_notice = ctk.CTkLabel(
            controls,
            text="Add documents to see compatible output formats.",
            text_color="gray",
            anchor="w",
            justify="left",
            wraplength=850
        )

        self.format_notice.grid(
            row=1, column=0,
            columnspan=4,
            padx=15, pady=(0, 10),
            sticky="ew"
        )

        self.cancel_button = ctk.CTkButton(
            controls,
            text="Cancel",
            width=100,
            fg_color="#A94442",
            hover_color="#853532",
            state="disabled",
            command=self.cancel_conversion
        )

        self.cancel_button.grid(
            row=0, column=3,
            padx=5, pady=12
        )

        self.convert_button = ctk.CTkButton(
            controls,
            text="Convert",
            width=140,
            height=38,
            command=self.start_conversion
        )

        self.convert_button.grid(
            row=0, column=4,
            padx=15, pady=12
        )

        # ----------------------------------------------
        # PROGRESS AREA
        # ----------------------------------------------

        progress_frame = ctk.CTkFrame(
            main,
            corner_radius=10
        )

        progress_frame.grid(
            row=4, column=0,
            sticky="ew"
        )

        progress_frame.grid_columnconfigure(0, weight=1)

        progress_header = ctk.CTkFrame(
            progress_frame,
            fg_color="transparent"
        )

        progress_header.grid(
            row=0, column=0,
            padx=15, pady=(12, 5),
            sticky="ew"
        )

        progress_header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            progress_header,
            text="Conversion progress",
            font=ctk.CTkFont(size=15, weight="bold")
        ).grid(
            row=0, column=0,
            sticky="w"
        )

        self.progress_percent_label = ctk.CTkLabel(
            progress_header,
            text="0%"
        )

        self.progress_percent_label.grid(
            row=0, column=1,
            sticky="e"
        )

        self.progress_bar = ctk.CTkProgressBar(
            progress_frame,
            height=12
        )

        self.progress_bar.grid(
            row=1, column=0,
            padx=15, pady=5,
            sticky="ew"
        )

        self.progress_bar.set(0)

        self.progress_status_label = ctk.CTkLabel(
            progress_frame,
            text="Ready to convert",
            text_color="gray"
        )

        self.progress_status_label.grid(
            row=2, column=0,
            padx=15, pady=(5, 12),
            sticky="w"
        )

    # ==================================================
    # FOOTER
    # ==================================================

    def create_footer(self):

        ctk.CTkLabel(
            self,
            text=f"{APP_NAME} v{APP_VERSION}",
            text_color="gray",
            font=ctk.CTkFont(size=11)
        ).grid(
            row=2, column=0,
            padx=20, pady=(0, 10),
            sticky="e"
        )

    # ==================================================
    # FILE HANDLING
    # ==================================================

    def add_files(self):

        if self.is_converting:
            return

        selected = filedialog.askopenfilenames(
            title="Select documents",
            filetypes=[
                (
                    "Supported documents",
                    "*.docx *.doc *.odt *.rtf *.txt "
                    "*.xlsx *.xls *.ods *.csv *.pptx *.ppt *.odp "
                    "*.pdf *.html *.htm"
                ),
                ("All files", "*.*")
            ]
        )

        self.process_files(selected)

    def handle_drop(self, event):

        if self.is_converting:
            return

        dropped_files = self.tk.splitlist(event.data)

        self.process_files(dropped_files)

    def process_files(self, file_paths):

        added = 0
        unsupported = []

        for file_path in file_paths:

            try:

                path = Path(file_path).resolve()

                if not path.is_file():
                    continue

                if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                    unsupported.append(path.name)
                    continue

                if path not in self.files:

                    self.files.append(path)
                    self.file_status[path] = "Waiting"

                    category = self.get_input_category(path)
                    if category:
                        supported = OUTPUT_FORMATS_BY_CATEGORY[category]
                        self.file_output_formats[path] = (
                            "PDF" if "PDF" in supported else supported[0]
                        )
                    else:
                        self.file_output_formats[path] = "Unavailable"

                    added += 1

            except (OSError, ValueError):
                continue

        self.refresh_file_list()

        if unsupported:

            messagebox.showwarning(
                "Unsupported files",
                "These file types are not supported:\n\n"
                + "\n".join(unsupported[:10])
            )

        if added:
            self.progress_status_label.configure(
                text=f"{added} document(s) added."
            )

    # ==================================================
    # OUTPUT FORMAT COMPATIBILITY
    # ==================================================

    @staticmethod
    def get_input_category(path):
        extension = Path(path).suffix.lower()

        for category, extensions in INPUT_CATEGORIES.items():
            if extension in extensions:
                return category

        # PDF files are accepted into the list for clear user feedback,
        # but this app does not currently convert PDF files to other types.
        return None

    def update_output_formats(self):

        if not hasattr(self, "output_format"):
            return

        if not self.files:
            available_formats = ["PDF"]
            notice = (
                "Choose a format for each file in its row. "
                "Use Apply to all to set one format for every file."
            )
        else:
            categories = [self.get_input_category(path) for path in self.files]

            if any(category is None for category in categories):
                available_formats = []
                notice = (
                    "PDF files are already in PDF format and cannot be "
                    "converted. Remove PDF files to enable conversion."
                )
            else:
                compatible_sets = [
                    set(OUTPUT_FORMATS_BY_CATEGORY[category])
                    for category in categories
                ]
                common_formats = set.intersection(*compatible_sets)
                available_formats = [
                    fmt for fmt in OUTPUT_FORMAT_ORDER if fmt in common_formats
                ]
                notice = (
                    "Choose an output format separately for each file, "
                    "or select a common format above and click Apply."
                )

        previous_format = self.output_format.get()
        self.available_output_formats = available_formats
        menu_values = available_formats if available_formats else ["Unavailable"]
        self.output_format.configure(values=menu_values)

        if previous_format in available_formats:
            self.output_format.set(previous_format)
        elif "PDF" in available_formats:
            self.output_format.set("PDF")
        elif available_formats:
            self.output_format.set(available_formats[0])
        else:
            self.output_format.set("Unavailable")

        self.format_notice.configure(text=notice)
        state = "normal" if available_formats and not self.is_converting else "disabled"
        self.output_format.configure(state=state)

        if hasattr(self, "apply_all_button"):
            self.apply_all_button.configure(state=state)

        self.update_apply_all_state()

    def update_apply_all_state(self):

        # The global selector is only meaningful while every file uses
        # the same output format. Once formats differ, disable both controls.
        selected_formats = {
            self.file_output_formats.get(path, "PDF")
            for path in self.files
        }

        formats_are_mixed = len(selected_formats) > 1
        has_files = bool(self.files)
        can_apply_all = (
            has_files
            and not formats_are_mixed
            and bool(self.available_output_formats)
            and not self.is_converting
        )

        # When every file has the same format, keep the global selector
        # synchronized with that shared choice (rather than leaving PDF
        # selected from its initial default).
        if can_apply_all:
            shared_format = next(iter(selected_formats))
            if shared_format in self.available_output_formats:
                self.output_format.set(shared_format)

        state = "normal" if can_apply_all else "disabled"

        if hasattr(self, "output_format"):
            self.output_format.configure(state=state)

        if hasattr(self, "apply_all_button"):
            self.apply_all_button.configure(state=state)

    def apply_format_to_all(self):

        selected_format = self.output_format.get()
        if selected_format not in self.available_output_formats:
            return

        for path in self.files:
            category = self.get_input_category(path)
            if category and selected_format in OUTPUT_FORMATS_BY_CATEGORY[category]:
                self.file_output_formats[path] = selected_format

        self.refresh_file_list()

    # ==================================================
    # REFRESH FILE LIST
    # ==================================================

    def refresh_file_list(self):

        for widget in self.file_list.winfo_children():
            widget.destroy()

        self.file_rows.clear()
        self.file_status_labels.clear()
        self.file_output_menus.clear()
        self.selected_file = None

        self.file_title.configure(text=f"Files to convert ({len(self.files)})")

        if not self.files:
            ctk.CTkLabel(
                self.file_list,
                text="No documents added yet",
                text_color="gray"
            ).pack(pady=25)
        else:
            for path in self.files:
                self.create_file_row(path)

        self.update_output_formats()
        self.update_controls()

    # ==================================================
    # CREATE FILE ROW
    # ==================================================

    def create_file_row(self, path):

        row = ctk.CTkFrame(self.file_list, corner_radius=6)
        row.pack(fill="x", padx=5, pady=3)
        row.grid_columnconfigure(0, weight=1)

        name = ctk.CTkLabel(
            row,
            text=path.name,
            anchor="w",
            font=ctk.CTkFont(weight="bold")
        )
        name.grid(
            row=0, column=0,
            padx=(12, 8), pady=(7, 0),
            sticky="ew"
        )

        status = self.file_status.get(path, "Waiting")
        status_label = ctk.CTkLabel(
            row,
            text=status,
            width=105,
            text_color=self.get_status_color(status)
        )
        status_label.grid(
            row=0, column=2,
            padx=(8, 12), pady=(7, 0),
            sticky="e"
        )

        original_extension = path.suffix.lower() or "(none)"
        output_format = self.file_output_formats.get(path, "PDF")
        details = ctk.CTkLabel(
            row,
            text=f"Original: {original_extension}    Output:",
            anchor="w",
            text_color="gray"
        )
        details.grid(
            row=1, column=0,
            padx=(12, 4), pady=(0, 7),
            sticky="w"
        )

        category = self.get_input_category(path)
        if category:
            available_for_file = OUTPUT_FORMATS_BY_CATEGORY[category]
            if output_format not in available_for_file:
                output_format = "PDF" if "PDF" in available_for_file else available_for_file[0]
                self.file_output_formats[path] = output_format
        else:
            available_for_file = []

        output_menu_values = (
            [fmt for fmt in OUTPUT_FORMAT_ORDER if fmt in available_for_file]
            if available_for_file else ["Unavailable"]
        )

        output_menu = ctk.CTkOptionMenu(
            row,
            values=output_menu_values,
            width=105,
            command=lambda value, file_path=path: self.change_file_output_format(
                file_path, value
            ),
            state="normal" if available_for_file and not self.is_converting else "disabled"
        )
        output_menu.set(output_format if available_for_file else "Unavailable")
        output_menu.grid(
            row=1, column=1,
            padx=4, pady=(0, 7),
            sticky="e"
        )

        self.file_rows[path] = row
        self.file_status_labels[path] = status_label
        self.file_output_menus[path] = output_menu

        for widget in (row, name, status_label, details):
            widget.bind(
                "<Button-1>",
                lambda event, p=path: self.select_file(p)
            )

    def change_file_output_format(self, path, selected_format):

        if self.is_converting:
            return

        category = self.get_input_category(path)
        if not category:
            return

        if selected_format in OUTPUT_FORMATS_BY_CATEGORY[category]:
            self.file_output_formats[path] = selected_format
            self.update_apply_all_state()

    # ==================================================
    # STATUS COLORS
    # ==================================================

    @staticmethod
    def get_status_color(status):

        colors = {
            "Waiting": "gray",
            "Converting": "#3498DB",
            "Completed": "#2ECC71",
            "Failed": "#E74C3C",
            "Cancelled": "#E0A040"
        }

        return colors.get(status, "gray")

    # ==================================================
    # UPDATE FILE STATUS
    # ==================================================

    def update_file_status(self, file_path, status):

        path = Path(file_path)

        self.file_status[path] = status

        if path in self.file_status_labels:

            self.file_status_labels[path].configure(
                text=status,
                text_color=self.get_status_color(status)
            )

        self.update_controls()

    # ==================================================
    # OPEN CONVERTED FILE
    # ==================================================

    def open_converted_file(self):

        if self.selected_file is None:
            messagebox.showinfo(
                "No document selected",
                "Select a completed document in the file list first."
            )
            return

        source = Path(self.selected_file)
        output_path = self.converted_outputs.get(source)

        if not output_path:
            messagebox.showinfo(
                "Converted file not available",
                "The selected document has not been converted successfully yet."
            )
            return

        output_path = Path(output_path)

        if not output_path.is_file():
            messagebox.showerror(
                "Converted file not found",
                "The converted PDF could not be found at its saved location:\n\n"
                f"{output_path}"
            )
            return

        try:
            os.startfile(str(output_path.resolve()))

        except OSError as error:
            messagebox.showerror(
                "Could not open converted file",
                f"Windows could not open the PDF file.\n\n{error}"
            )

    # ==================================================
    # SELECT FILE
    # ==================================================

    def select_file(self, path):

        if self.is_converting:
            return

        self.selected_file = path

        for file_path, row in self.file_rows.items():

            row.configure(
                fg_color=(
                    "#245A91"
                    if file_path == path
                    else "transparent"
                )
            )

        self.update_controls()

    # ==================================================
    # REMOVE SELECTED
    # ==================================================

    def remove_selected(self):

        if self.is_converting:
            return

        if self.selected_file in self.files:

            self.files.remove(self.selected_file)
            self.file_status.pop(self.selected_file, None)
            self.converted_outputs.pop(self.selected_file, None)
            self.file_output_formats.pop(self.selected_file, None)

            self.refresh_file_list()

    # ==================================================
    # CLEAR ALL
    # ==================================================

    def clear_files(self):

        if self.is_converting:
            return

        self.files.clear()
        self.file_status.clear()
        self.converted_outputs.clear()
        self.file_output_formats.clear()

        self.refresh_file_list()

        self.progress_bar.set(0)
        self.progress_percent_label.configure(text="0%")
        self.progress_status_label.configure(
            text="Ready to convert"
        )

    # ==================================================
    # SELECT OUTPUT FOLDER
    # ==================================================

    def select_output_folder(self):

        if self.is_converting:
            return

        selected = filedialog.askdirectory(
            title="Select output folder",
            initialdir=str(self.output_dir)
        )

        if selected:

            self.output_dir = Path(selected)

            self.output_label.configure(
                text=str(self.output_dir)
            )

    def open_output_folder(self):

        try:
            self.output_dir.mkdir(
                parents=True,
                exist_ok=True
            )

            os.startfile(str(self.output_dir.resolve()))

        except OSError as error:
            messagebox.showerror(
                "Could not open folder",
                f"Windows could not open the output folder.\\n\\n{error}"
            )

    # ==================================================
    # START CONVERSION
    # ==================================================

    def start_conversion(self):

        if self.is_converting:
            return

        if not self.files:
            messagebox.showwarning(
                "No files",
                "Please add documents first."
            )
            return

        output_formats = {
            str(path): self.file_output_formats.get(path, "PDF")
            for path in self.files
        }

        invalid_files = [
            path for path in self.files
            if output_formats[str(path)] in ("Unavailable", "")
        ]
        if invalid_files:
            messagebox.showwarning(
                "Unsupported input files",
                "Remove files that do not have a supported output format:\n\n"
                + "\n".join(path.name for path in invalid_files)
            )
            return

        try:

            self.output_dir.mkdir(
                parents=True,
                exist_ok=True
            )

        except OSError as error:

            messagebox.showerror(
                "Output folder error",
                str(error)
            )
            return

        # Check all destination files before starting the conversion queue.
        existing_outputs = []
        for path in self.files:
            selected_format = output_formats[str(path)]
            expected_output = self.output_dir / f"{path.stem}.{selected_format.lower()}"
            if expected_output.exists():
                existing_outputs.append(expected_output)

        overwrite_existing = False

        if existing_outputs:
            file_list = "\n".join(
                f"• {path.name}" for path in existing_outputs[:12]
            )
            if len(existing_outputs) > 12:
                file_list += (
                    f"\n... and {len(existing_outputs) - 12} more file(s)"
                )

            replace_confirmed = messagebox.askyesno(
                "Existing output files found",
                "The following output file(s) already exist:\n\n"
                f"{file_list}\n\n"
                "Do you want to replace them with the newly converted files?"
            )

            if not replace_confirmed:
                self.progress_status_label.configure(
                    text="Conversion cancelled. Existing files were left unchanged."
                )
                return

            overwrite_existing = True

        # Reset previous status
        for path in self.files:
            self.file_status[path] = "Waiting"
            self.converted_outputs.pop(path, None)

        self.refresh_file_list()

        self.progress_bar.set(0)
        self.progress_percent_label.configure(text="0%")

        self.progress_status_label.configure(
            text="Starting conversion..."
        )

        self.event_queue = Queue()

        self.worker = ConversionWorker(
            files=self.files.copy(),
            output_dir=self.output_dir,
            event_queue=self.event_queue,
            overwrite_existing=overwrite_existing,
            output_formats=output_formats
        )

        self.is_converting = True
        self.update_controls()

        self.worker.start()

        self.after(
            100,
            self.process_worker_events
        )

    # ==================================================
    # CANCEL CONVERSION
    # ==================================================

    def cancel_conversion(self):

        if not self.is_converting or not self.worker:
            return

        self.worker.cancel()

        self.cancel_button.configure(
            state="disabled",
            text="Cancelling..."
        )

        self.progress_status_label.configure(
            text="Cancellation requested. Finishing current file..."
        )

    # ==================================================
    # PROCESS WORKER EVENTS
    # ==================================================

    def process_worker_events(self):

        try:

            while True:

                event = self.event_queue.get_nowait()

                event_type = event.get("type")

                if event_type == "started":

                    self.progress_status_label.configure(
                        text=f"Converting {event['total']} documents..."
                    )

                elif event_type == "file_started":

                    self.update_file_status(
                        event["file"],
                        "Converting"
                    )

                    self.progress_status_label.configure(
                        text=f"Converting: {Path(event['file']).name}"
                    )

                elif event_type == "file_completed":

                    source_path = Path(event["file"])
                    self.converted_outputs[source_path] = Path(event["output"])

                    self.update_file_status(
                        event["file"],
                        "Completed"
                    )

                elif event_type == "file_failed":

                    self.update_file_status(
                        event["file"],
                        "Failed"
                    )

                    print(
                        f"Conversion failed: {event['file']}"
                    )
                    print(event["error"])

                elif event_type == "file_cancelled":

                    self.update_file_status(
                        event["file"],
                        "Cancelled"
                    )

                elif event_type == "progress":

                    percent = event["progress_percent"]

                    self.progress_bar.set(percent / 100)

                    self.progress_percent_label.configure(
                        text=f"{percent:.1f}%"
                    )

                    self.progress_status_label.configure(
                        text=(
                            f"Completed: {event['completed']} | "
                            f"Failed: {event['failed']} | "
                            f"Remaining: {event['remaining']}"
                        )
                    )

                elif event_type == "cancel_requested":

                    self.progress_status_label.configure(
                        text="Cancellation requested..."
                    )

                elif event_type == "worker_error":

                    self.finish_worker_error(
                        event["error"]
                    )
                    return

                elif event_type == "finished":

                    self.finish_conversion(event)
                    return

        except Empty:
            pass

        if self.is_converting:

            self.after(
                100,
                self.process_worker_events
            )

    # ==================================================
    # FINISH CONVERSION
    # ==================================================

    def finish_conversion(self, result):

        self.is_converting = False
        self.worker = None

        self.update_controls()

        percent = result["progress"]

        self.progress_bar.set(percent / 100)

        self.progress_percent_label.configure(
            text=f"{percent:.1f}%"
        )

        if result["was_cancelled"]:

            self.progress_status_label.configure(
                text="Conversion queue cancelled."
            )

        else:

            self.progress_status_label.configure(
                text="All conversion jobs finished."
            )

        summary = (
            f"Conversion summary\n\n"
            f"Total: {result['total']}\n"
            f"Completed: {result['successful']}\n"
            f"Failed: {result['failed']}\n"
            f"Cancelled: {result['cancelled']}\n\n"
            f"Output folder:\n{self.output_dir}"
        )

        if result["failed"] > 0:

            messagebox.showwarning(
                "Conversion finished",
                summary
            )

        else:

            messagebox.showinfo(
                "Conversion finished",
                summary
            )

    # ==================================================
    # WORKER ERROR
    # ==================================================

    def finish_worker_error(self, error):

        self.is_converting = False
        self.worker = None

        self.update_controls()

        self.progress_status_label.configure(
            text="Conversion stopped due to an error."
        )

        messagebox.showerror(
            "Conversion error",
            str(error)
        )

    # ==================================================
    # UPDATE CONTROLS
    # ==================================================

    def update_controls(self):

        running = self.is_converting
        has_files = bool(self.files)

        self.add_button.configure(
            state="disabled" if running else "normal"
        )

        self.remove_button.configure(
            state="disabled" if running or not has_files else "normal"
        )

        self.clear_button.configure(
            state="disabled" if running or not has_files else "normal"
        )

        self.browse_button.configure(
            state="disabled" if running else "normal"
        )

        has_compatible_format = bool(
            getattr(self, "available_output_formats", [])
        )

        self.convert_button.configure(
            state=(
                "disabled"
                if running or not has_files or not has_compatible_format
                else "normal"
            )
        )

        if hasattr(self, "output_format"):
            self.output_format.configure(
                state=(
                    "disabled"
                    if running or not has_compatible_format
                    else "normal"
                )
            )

        if hasattr(self, "apply_all_button"):
            self.apply_all_button.configure(
                state="disabled" if running or not has_compatible_format else "normal"
            )

        for menu in getattr(self, "file_output_menus", {}).values():
            menu.configure(state="disabled" if running else "normal")

        if hasattr(self, "apply_all_button"):
            self.update_apply_all_state()

        self.cancel_button.configure(
            state="normal" if running else "disabled",
            text="Cancel"
        )

        selected_output = (
            self.converted_outputs.get(self.selected_file)
            if self.selected_file is not None
            else None
        )

        converted_file_available = (
            selected_output is not None
            and Path(selected_output).is_file()
        )

        self.open_converted_button.configure(
            state=(
                "normal"
                if not running and converted_file_available
                else "disabled"
            )
        )


# ==================================================
# START APPLICATION
# ==================================================

if __name__ == "__main__":

    app = DocumentConverterApp()
    app.mainloop()

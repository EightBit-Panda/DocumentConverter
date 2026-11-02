
import shutil
import subprocess
import sys
import uuid
from pathlib import Path


class ConversionError(Exception):
    """Raised when document conversion fails."""
    pass


class ConversionEngine:
    """Convert supported office documents using bundled or installed LibreOffice."""

    OUTPUT_EXTENSIONS = {
        "PDF": "pdf",
        "DOCX": "docx",
        "ODT": "odt",
        "RTF": "rtf",
        "TXT": "txt",
        "HTML": "html",
        "XLSX": "xlsx",
        "ODS": "ods",
        "CSV": "csv",
        "PPTX": "pptx",
        "ODP": "odp"
    }

    INPUT_CATEGORIES = {
        "word": {".docx", ".doc", ".odt", ".rtf", ".txt"},
        "spreadsheet": {".xlsx", ".xls", ".ods", ".csv"},
        "presentation": {".pptx", ".ppt", ".odp"},
        "web": {".html", ".htm"}
    }

    OUTPUT_FORMATS_BY_CATEGORY = {
        "word": {"PDF", "DOCX", "ODT", "RTF", "TXT", "HTML"},
        "spreadsheet": {"PDF", "XLSX", "ODS", "CSV", "HTML"},
        "presentation": {"PDF", "PPTX", "ODP"},
        "web": {"PDF", "HTML"}
    }

    def __init__(self, libreoffice_path=None):
        self.libreoffice_path = (
            Path(libreoffice_path)
            if libreoffice_path
            else self.find_libreoffice()
        )

        if not self.libreoffice_path.is_file():
            raise FileNotFoundError(
                f"LibreOffice was not found: {self.libreoffice_path}"
            )

    @staticmethod
    def find_libreoffice():
        candidates = []

        # 1. Look inside the packaged DocumentConverter application.
        if getattr(sys, "frozen", False):
            application_dir = Path(sys.executable).resolve().parent
            bundle_dir = Path(getattr(sys, "_MEIPASS", application_dir))

            candidates.extend([
                application_dir / "LibreOffice" / "program" / "soffice.exe",
                bundle_dir / "LibreOffice" / "program" / "soffice.exe",
                application_dir / "program" / "soffice.exe",
            ])

        else:
            # Development environment.
            project_dir = Path(__file__).resolve().parent.parent

            candidates.extend([
                project_dir / "LibreOffice" / "program" / "soffice.exe",
                project_dir / "runtime" / "LibreOffice" / "program" / "soffice.exe",
                project_dir / "installer" / "lo_runtime" / "program" / "soffice.exe",
            ])

        # 2. Fall back to a normal Windows installation.
        candidates.extend([
            Path(r"C:\Program Files\LibreOffice\program\soffice.exe"),
            Path(r"C:\Program Files (x86)\LibreOffice\program\soffice.exe")
        ])

        for candidate in candidates:
            if candidate.is_file():
                return candidate

        raise FileNotFoundError(
            "LibreOffice was not found. "
            "No bundled or installed LibreOffice installation could be located."
        )

    @classmethod
    def get_input_category(cls, source):
        extension = Path(source).suffix.lower()

        for category, extensions in cls.INPUT_CATEGORIES.items():
            if extension in extensions:
                return category

        return None

    def convert(
        self,
        source_file,
        output_dir,
        output_format="PDF",
        overwrite=False
    ):
        source = Path(source_file).resolve()
        destination = Path(output_dir).resolve()
        output_format = str(output_format).upper()

        if not source.is_file():
            raise ConversionError(f"Source file does not exist: {source}")

        if source.suffix.lower() == ".pdf":
            raise ConversionError(
                "PDF files are already in PDF format and are not converted."
            )

        category = self.get_input_category(source)

        if category is None:
            raise ConversionError(
                f"Unsupported input file type: "
                f"{source.suffix or '(no extension)'}"
            )

        if output_format not in self.OUTPUT_EXTENSIONS:
            raise ConversionError(
                f"Unsupported output format: {output_format}"
            )

        if output_format not in self.OUTPUT_FORMATS_BY_CATEGORY[category]:
            raise ConversionError(
                f"{output_format} output is not supported for "
                f"{category} documents."
            )

        destination.mkdir(parents=True, exist_ok=True)

        output_extension = self.OUTPUT_EXTENSIONS[output_format]
        expected_output = destination / f"{source.stem}.{output_extension}"

        if expected_output.exists() and not overwrite:
            raise ConversionError(
                f"Output file already exists: {expected_output}"
            )

        temporary_output_dir = (
            destination / f".documentconverter_{uuid.uuid4().hex}"
        )
        temporary_output_dir.mkdir(parents=True, exist_ok=False)

        profile_dir = (
            Path.home()
            / ".documentconverter"
            / "profiles"
            / uuid.uuid4().hex
        )
        profile_dir.mkdir(parents=True, exist_ok=True)

        profile_uri = profile_dir.as_uri()
        temporary_output = temporary_output_dir / expected_output.name

        command = [
            str(self.libreoffice_path),
            "--headless",
            "--nologo",
            "--nodefault",
            "--nofirststartwizard",
            f"-env:UserInstallation={profile_uri}",
            "--convert-to",
            output_extension,
            "--outdir",
            str(temporary_output_dir),
            str(source)
        ]

        try:
            try:
                result = subprocess.run(
                    command,
                    capture_output=True,
                    text=True,
                    timeout=180,
                    check=False,
                    creationflags=getattr(
                        subprocess,
                        "CREATE_NO_WINDOW",
                        0
                    )
                )

            except subprocess.TimeoutExpired:
                raise ConversionError(
                    "Conversion timed out after 180 seconds."
                )

            except OSError as error:
                raise ConversionError(
                    f"Could not start LibreOffice: {error}"
                )

            if result.returncode != 0:
                raise ConversionError(
                    result.stderr.strip()
                    or result.stdout.strip()
                    or "LibreOffice returned an error."
                )

            if not temporary_output.is_file():
                details = result.stderr.strip() or result.stdout.strip()
                raise ConversionError(
                    "LibreOffice finished, but the output file was not created."
                    + (f"\n\nLibreOffice message: {details}" if details else "")
                )

            if temporary_output.stat().st_size == 0:
                raise ConversionError("The generated output file is empty.")

            if expected_output.exists() and not overwrite:
                raise ConversionError(
                    f"Output file already exists: {expected_output}"
                )

            temporary_output.replace(expected_output)
            return expected_output

        finally:
            shutil.rmtree(temporary_output_dir, ignore_errors=True)
            shutil.rmtree(profile_dir, ignore_errors=True)

    def convert_to_pdf(self, source_file, output_dir, overwrite=False):
        return self.convert(
            source_file,
            output_dir,
            output_format="PDF",
            overwrite=overwrite
        )

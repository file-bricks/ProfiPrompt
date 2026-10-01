import html
import os
import stat
import uuid
from pathlib import Path
from typing import Iterable, List, Optional
from PySide6.QtCore import QMarginsF
from PySide6.QtGui import QFont, QPageLayout, QPageSize, QPdfWriter, QTextDocument
from PySide6.QtWidgets import QMessageBox

from atomic_io import atomic_publish_file, is_protected_path

def _format_tags(tags) -> str:
    """Formatiert Tags robust als kommagetrennte Liste (filtert None/Leereintraege)."""
    if not tags:
        return ""
    return ", ".join(
        str(t).strip()
        for t in tags
        if t is not None and str(t).strip()
    )

def _init_printer(path: str) -> QPdfWriter:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    writer = QPdfWriter(path)
    writer.setResolution(300)
    writer.setPageSize(QPageSize(QPageSize.A4))
    writer.setPageMargins(QMarginsF(12, 12, 12, 12), QPageLayout.Millimeter)
    return writer

def _render_html_for_prompt(prompt, settings) -> str:
    title = html.escape(getattr(prompt, "title", "") or "")
    purpose = html.escape(getattr(prompt, "purpose", "") or "")
    tags_str = html.escape(_format_tags(getattr(prompt, "tags", [])))
    text = html.escape(getattr(prompt, "text", "") or "")

    parts = [f"<h1>{title}</h1>"]
    parts.append(
        f"<p><b>Zweck:</b> {purpose}"
        f"<br><b>Tags:</b> {tags_str}</p>"
    )
    parts.append(f"<pre>{text}</pre>")
    include_result = getattr(settings, 'get_include_metadata', lambda: False)()
    last_res = getattr(prompt, "last_result", "") or ""
    if include_result and last_res.strip():
        parts.append("<hr><pre>" + html.escape(last_res) + "</pre>")
    return "".join(parts)

def _render_html_for_version(version, settings) -> str:
    v_title = html.escape(getattr(version, "title", "") or "")
    v_num = getattr(version, "version_number", None) or "?"
    tags_str = html.escape(_format_tags(getattr(version, "tags", [])))
    v_text = html.escape(getattr(version, "text", "") or "")

    parts = [
        f"<h2>{v_title} <small>(v{v_num})</small></h2>",
        f"<p><b>Tags:</b> {tags_str}</p>",
        f"<pre>{v_text}</pre>",
    ]
    include_result = getattr(settings, 'get_include_metadata', lambda: False)()
    res = getattr(version, "result", "") or ""
    if include_result and res.strip():
        parts.append("<hr><pre>" + html.escape(res) + "</pre>")
    return "".join(parts)

def _safe_export_html_to_pdf(html: str, path: str, parent=None, protected_paths: Optional[Iterable[str | Path]] = None) -> bool:
    try:
        return _export_html_to_pdf(html, path, parent=parent, protected_paths=protected_paths)
    except TypeError:
        return _export_html_to_pdf(html, path, parent=parent)

def export_single_prompt(prompt, settings, path: str, parent=None, protected_paths: Optional[Iterable[str | Path]] = None):
    html = "<html><body>" + _render_html_for_prompt(prompt, settings) + "</body></html>"
    return _safe_export_html_to_pdf(html, path, parent, protected_paths=protected_paths)

def export_single_version(version, path: str, parent=None, settings=None, protected_paths: Optional[Iterable[str | Path]] = None):
    html = "<html><body>" + _render_html_for_version(version, settings) + "</body></html>"
    return _safe_export_html_to_pdf(html, path, parent, protected_paths=protected_paths)

def export_all_prompts(storage, settings, path: str, parent=None, protected_paths: Optional[Iterable[str | Path]] = None):
    if protected_paths is None:
        protected = []
        if hasattr(storage, "prompts_file"):
            protected.append(storage.prompts_file)
        if hasattr(storage, "boards_file"):
            protected.append(storage.boards_file)
        protected_paths = protected

    if callable(getattr(storage, "load_library", None)):
        prompts, _ = storage.load_library()
    else:
        prompts = storage.load_prompts()
    html = ["<html><body>"]
    for p in prompts or []:
        if not p:
            continue
        html.append(_render_html_for_prompt(p, settings))
        html.append("<hr>")
    html.append("</body></html>")
    return _safe_export_html_to_pdf("".join(html), path, parent, protected_paths=protected_paths)

def export_single_prompt_with_versions(prompt, settings, path: str, parent=None, protected_paths: Optional[Iterable[str | Path]] = None):
    """
    Exportiert einen Prompt + alle Versionen als PDF.
    """
    parts = []
    parts.append(_render_html_for_prompt(prompt, settings))
    parts.append("<hr>")
    versions = [v for v in (getattr(prompt, "versions", []) or []) if v is not None]
    for v in sorted(versions, key=lambda x: getattr(x, "version_number", 0) or 0):
        parts.append(_render_html_for_version(v, settings))
        parts.append("<hr>")
    html = "<html><body>" + "".join(parts) + "</body></html>"
    return _safe_export_html_to_pdf(html, path, parent, protected_paths=protected_paths)

def _export_html_to_pdf(html: str, path: str, parent=None, protected_paths: Optional[Iterable[str | Path]] = None) -> bool:
    target_path = Path(path)
    if is_protected_path(target_path, protected_paths):
        msg = f"Zielpfad '{target_path}' darf keine geschützte Bibliotheksdatei überschreiben."
        if parent:
            QMessageBox.critical(parent, "Fehler", f"PDF-Export fehlgeschlagen:\n{msg}")
        return False

    target_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target_path.with_name(f".{target_path.name}.tmp.{os.getpid()}_{uuid.uuid4().hex[:8]}.pdf")
    doc = QTextDocument()
    doc.setHtml(html)
    doc.setDefaultFont(QFont("Arial", 10))
    printer = None
    try:
        printer = _init_printer(str(tmp_path))
        doc.print_(printer)
        del printer

        if not tmp_path.exists():
            raise FileNotFoundError(f"PDF-Datei wurde nicht erzeugt: {tmp_path}")
        size = tmp_path.stat().st_size
        if size == 0:
            raise ValueError("Erzeugte PDF-Datei ist leer (0 Bytes).")
        with open(tmp_path, "rb") as f:
            header = f.read(5)
            if header != b"%PDF-":
                raise ValueError(f"Ungültiges PDF-Format (Header: {header!r})")

        atomic_publish_file(tmp_path, target_path, protected_paths=protected_paths)
        if parent:
            QMessageBox.information(parent, "Export", "PDF erfolgreich gespeichert.")
        return True
    except Exception as e:
        if parent:
            QMessageBox.critical(parent, "Fehler", f"PDF-Export fehlgeschlagen:\n{e}")
        return False
    finally:
        if tmp_path.exists():
            try:
                os.chmod(tmp_path, stat.S_IWRITE | stat.S_IREAD)
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass

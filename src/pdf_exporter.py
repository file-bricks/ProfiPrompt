# pdf_exporter.py

from PySide6.QtGui import QTextDocument, QFont
from PySide6.QtPrintSupport import QPrinter
from PySide6.QtWidgets import QMessageBox
from typing import List

def _init_printer(path: str) -> QPrinter:
    printer = QPrinter(QPrinter.HighResolution)
    printer.setOutputFormat(QPrinter.PdfFormat)
    printer.setOutputFileName(path)
    printer.setPageMargins(12, 12, 12, 12, QPrinter.Millimeter)
    return printer

def _render_html_for_prompt(prompt, settings) -> str:
    html = [f"<h1>{prompt.title}</h1>"]
    html.append(f"<p><b>Zweck:</b> {prompt.purpose}<br><b>Tags:</b> {', '.join(prompt.tags)}</p>")
    html.append(f"<pre>{prompt.text}</pre>")
    include_result = getattr(settings, 'get_include_metadata', lambda: False)()
    if include_result and getattr(prompt, "last_result", "").strip():
        html.append("<hr><pre>" + prompt.last_result + "</pre>")
    return "".join(html)

def _render_html_for_version(version, settings) -> str:
    html = [
        f"<h2>{version.title} <small>(v{version.version_number})</small></h2>",
        f"<p><b>Tags:</b> {', '.join(version.tags)}</p>",
        f"<pre>{version.text}</pre>"
    ]
    include_result = getattr(settings, 'get_include_metadata', lambda: False)()
    if include_result and getattr(version, "result", "").strip():
        html.append("<hr><pre>" + version.result + "</pre>")
    return "".join(html)

def export_single_prompt(prompt, settings, path: str, parent=None):
    html = "<html><body>" + _render_html_for_prompt(prompt, settings) + "</body></html>"
    _export_html_to_pdf(html, path, parent)

def export_single_version(version, path: str, parent=None, settings=None):
    html_parts = [
        f"<h2>{version.title} <small>(v{version.version_number})</small></h2>",
        f"<p><b>Tags:</b> {', '.join(version.tags)}</p>",
        f"<pre>{version.text}</pre>"
    ]
    if getattr(version, "result", "").strip():
        html_parts.append("<hr><pre>" + version.result + "</pre>")
    html = "<html><body>" + "".join(html_parts) + "</body></html>"
    _export_html_to_pdf(html, path, parent)

def export_all_prompts(storage, settings, path: str, parent=None):
    prompts = storage.load_prompts()
    html = ["<html><body>"]
    for p in prompts:
        html.append(_render_html_for_prompt(p, settings))
        html.append("<hr>")
    html.append("</body></html>")
    _export_html_to_pdf("".join(html), path, parent)

def export_single_prompt_with_versions(prompt, settings, path: str, parent=None):
    """
    Exportiert einen Prompt + alle Versionen als PDF.
    """
    parts = []
    parts.append(_render_html_for_prompt(prompt, settings))
    parts.append("<hr>")
    for v in sorted(prompt.versions, key=lambda x: x.version_number):
        parts.append(_render_html_for_version(v, settings))
        parts.append("<hr>")
    html = "<html><body>" + "".join(parts) + "</body></html>"
    _export_html_to_pdf(html, path, parent)

def _export_html_to_pdf(html: str, path: str, parent=None):
    doc = QTextDocument()
    doc.setHtml(html)
    doc.setDefaultFont(QFont("Arial", 10))
    try:
        doc.print_(_init_printer(path))
        if parent:
            QMessageBox.information(parent, "Export", "PDF erfolgreich gespeichert.")
    except Exception as e:
        if parent:
            QMessageBox.critical(parent, "Fehler", f"PDF-Export fehlgeschlagen:\n{e}")

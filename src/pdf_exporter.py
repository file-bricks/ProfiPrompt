import html
from pathlib import Path
from typing import List, Optional
from PySide6.QtCore import QMarginsF
from PySide6.QtGui import QTextDocument, QFont, QPageLayout, QPageSize, QPdfWriter
from PySide6.QtWidgets import QMessageBox

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

def export_single_prompt(prompt, settings, path: str, parent=None):
    html = "<html><body>" + _render_html_for_prompt(prompt, settings) + "</body></html>"
    return _export_html_to_pdf(html, path, parent)

def export_single_version(version, path: str, parent=None, settings=None):
    html = "<html><body>" + _render_html_for_version(version, settings) + "</body></html>"
    return _export_html_to_pdf(html, path, parent)

def export_all_prompts(storage, settings, path: str, parent=None):
    prompts = storage.load_prompts()
    html = ["<html><body>"]
    for p in prompts or []:
        if not p:
            continue
        html.append(_render_html_for_prompt(p, settings))
        html.append("<hr>")
    html.append("</body></html>")
    return _export_html_to_pdf("".join(html), path, parent)

def export_single_prompt_with_versions(prompt, settings, path: str, parent=None):
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
    return _export_html_to_pdf(html, path, parent)

def _export_html_to_pdf(html: str, path: str, parent=None) -> bool:
    doc = QTextDocument()
    doc.setHtml(html)
    doc.setDefaultFont(QFont("Arial", 10))
    try:
        doc.print_(_init_printer(path))
        if parent:
            QMessageBox.information(parent, "Export", "PDF erfolgreich gespeichert.")
        return True
    except Exception as e:
        if parent:
            QMessageBox.critical(parent, "Fehler", f"PDF-Export fehlgeschlagen:\n{e}")
        return False

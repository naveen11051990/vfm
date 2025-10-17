"""
Generate a PDF summary for device system information.

The script consumes a serial number either from CLI arguments or stdin,
renders a concise PDF using the MinimalPDF helper, and saves it locally.
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import sys
from datetime import datetime, timezone
from typing import Any, Iterable, Optional

from pathlib import Path

if __package__ in (None, ""):
    sys.path.append(str(Path(__file__).resolve().parent.parent))

from reporting.modules.minimalpdf import MinimalPDF

SERIAL_KEYS: tuple[str, ...] = (
    "serial",
    "serial_number",
    "net_serial",
    "msg",
    "stdout",
    "stdout_lines",
)

SERIAL_PATTERN = re.compile(
    r"(?:serial(?:\s*(?:number|no))?|msg)\s*[:=]\s*[\"']?(?P<serial>[A-Za-z0-9\-._]+)",
    re.IGNORECASE,
)


class SerialExtractionError(RuntimeError):
    """Raised when a serial number cannot be located in the input."""


def parse_args(argv: Optional[Iterable[str]] = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a PDF report containing the device serial number."
    )
    parser.add_argument(
        "--serial", dest="serial", help="Device serial number. Overrides stdin input."
    )
    parser.add_argument(
        "--host",
        dest="host",
        help="Optional hostname to include in the report.",
    )
    parser.add_argument(
        "--title",
        dest="title",
        default="System Information Report",
        help="Title text for the PDF header.",
    )
    parser.add_argument(
        "--output",
        dest="output",
        default="system-info-report.pdf",
        help="Target filename for the generated PDF.",
    )
    return parser.parse_args(argv)


def read_stdin() -> str:
    """Read all data from stdin."""
    if sys.stdin is None or sys.stdin.closed:
        return ""
    return sys.stdin.read()


def _coerce_text(value: Any) -> Optional[str]:
    if isinstance(value, str):
        candidate = value.strip()
        return candidate or None
    if isinstance(value, (list, tuple)):
        for item in value:
            text = _coerce_text(item)
            if text:
                return text
    return None


def _search_mapping(mapping: dict[str, Any]) -> Optional[str]:
    for key, value in mapping.items():
        lowered = key.lower()
        if lowered in SERIAL_KEYS:
            extracted = _coerce_text(value)
            if extracted:
                return extracted
        if isinstance(value, dict):
            nested = _search_mapping(value)
            if nested:
                return nested
        elif isinstance(value, (list, tuple)):
            for item in value:
                if isinstance(item, dict):
                    nested = _search_mapping(item)
                    if nested:
                        return nested
                else:
                    result = _coerce_text(item)
                    if result:
                        return result
    return None


def extract_serial(raw_input: str) -> str:
    """
    Attempt to locate a serial number within the provided text blob.

    The function prefers structured data (JSON or Python-literal dict/list), falling
    back to regex matching when necessary.
    """
    stripped = raw_input.strip()
    if not stripped:
        raise SerialExtractionError("No data received to parse.")

    for parser in (json.loads, ast.literal_eval):
        try:
            parsed = parser(stripped)
        except Exception:  # pragma: no cover - best-effort parsing
            continue
        if isinstance(parsed, dict):
            serial = _search_mapping(parsed)
            if serial:
                return serial
        elif isinstance(parsed, list):
            for item in parsed:
                if isinstance(item, dict):
                    serial = _search_mapping(item)
                    if serial:
                        return serial
                else:
                    serial = _coerce_text(item)
                    if serial:
                        return serial

    match = SERIAL_PATTERN.search(stripped)
    if match:
        return match.group("serial").strip()

    serial_candidate = _coerce_text(stripped)
    if serial_candidate:
        return serial_candidate
    raise SerialExtractionError(
        "Unable to locate a serial number in the provided input."
    )


def ensure_parent_dir(path: str) -> None:
    directory = os.path.dirname(os.path.abspath(path))
    if directory and not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)


def build_pdf(serial: str, title: str, host: Optional[str]) -> bytes:
    """
    Create the PDF content containing the supplied serial number.
    """
    pdf = MinimalPDF("system-info-report.pdf",
                     page_size=(595, 842), font="Courier")
    pdf.margin = 36
    pdf.add_header(title, font_size=15, bold=True)
    pdf.draw_page_border()

    left = pdf.margin + 12
    pdf.set_font(12)
    pdf.text(left, pdf.y, f"Serial Number: {serial}", {"bold": True})
    pdf.y -= pdf.leading * 1.5

    if host:
        pdf.text(left, pdf.y, f"Device Host: {host}")
        pdf.y -= pdf.leading * 1.5

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    pdf.text(left, pdf.y, f"Generated: {timestamp}")

    pdf.set_metadata("Title", title)
    pdf.set_metadata("Author", "Ansible Automation Platform")
    pdf.set_metadata("Producer", "sys_info_report.py")
    pdf.set_metadata("CustomMetadata", "Yes")
    page_count = len(pdf.pages) + (1 if pdf.current_content else 0)
    pdf.set_metadata("PageCount", str(page_count))

    pdf_stream = pdf.output()
    pdf_stream.seek(0)
    return pdf_stream.read()


def resolve_serial(args: argparse.Namespace) -> str:
    if args.serial:
        return args.serial.strip()
    stdin_data = read_stdin()
    if not stdin_data.strip():
        raise SerialExtractionError(
            "Expected a serial number via --serial or stdin input."
        )
    return extract_serial(stdin_data)


def write_pdf(output_path: str, payload: bytes) -> None:
    ensure_parent_dir(output_path)
    with open(output_path, "wb") as handle:
        handle.write(payload)


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = parse_args(argv)
    try:
        serial = resolve_serial(args)
    except SerialExtractionError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    pdf_payload = build_pdf(serial, args.title, args.host)
    try:
        write_pdf(args.output, pdf_payload)
    except OSError as exc:
        print(f"Failed to write PDF: {exc}", file=sys.stderr)
        return 1

    print(f"Saved report: {args.output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

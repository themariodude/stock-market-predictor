
"""
US-37 - Export Stock Analysis Report as PDF.

Renders a Jinja2 HTML template and converts it to PDF
using WeasyPrint.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import CSS, HTML

APP_DIR = Path(__file__).resolve().parents[1]

TEMPLATE_DIR = APP_DIR / "templates"
CSS_FILE = APP_DIR / "static" / "report.css"

template_env = Environment(
    loader=FileSystemLoader(str(TEMPLATE_DIR)),
    autoescape=select_autoescape(["html", "xml"]),
)


def generate_stock_report_pdf(
    ticker: str,
    company_name: str,
    stock: dict[str, Any],
    prediction: dict[str, Any],
) -> bytes:
    """Generate a PDF report from already retrieved stock data."""

    template = template_env.get_template("stock_analysis.html")

    generated_at = datetime.now(timezone.utc).strftime(
        "%Y-%m-%d %H:%M UTC"
    )

    html_content = template.render(
        ticker=ticker,
        company_name=company_name,
        stock=stock,
        prediction=prediction,
        generated_at=generated_at,
    )

    pdf_bytes = HTML(string=html_content).write_pdf(
        stylesheets=[CSS(filename=str(CSS_FILE))]
    )

    return pdf_bytes

"""DashboardRenderer: Jinja2 + autoescape -> coverage.html."""

from __future__ import annotations

from pathlib import Path

from jinja2 import Environment, PackageLoader, select_autoescape

from tools.branch_coverage.models import CoverageReport


class DashboardRenderer:
    def __init__(self) -> None:
        self._env = Environment(
            loader=PackageLoader("tools.branch_coverage", "templates"),
            autoescape=select_autoescape(["html", "j2"]),
            trim_blocks=False,
            lstrip_blocks=False,
        )

    def render(self, report: CoverageReport, output_path: Path) -> None:
        template = self._env.get_template("base.html.j2")
        html = template.render(report=report)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html)

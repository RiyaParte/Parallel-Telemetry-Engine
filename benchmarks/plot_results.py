"""Create a dependency-free SVG processing-time chart from benchmark CSV files."""

from __future__ import annotations

import argparse
import csv
from html import escape
import math
from pathlib import Path


WIDTH = 960
HEIGHT = 560
COLORS = ("#2563eb", "#dc2626", "#059669", "#9333ea")


def _load_rows(paths: list[Path]) -> dict[str, list[tuple[int, float]]]:
    series: dict[str, list[tuple[int, float]]] = {}
    for path in paths:
        with path.open(newline="", encoding="utf-8") as source:
            for row in csv.DictReader(source):
                mode = row["mode"]
                records = int(row["records"])
                elapsed_seconds = float(row["median_seconds"])
                if records <= 0 or not math.isfinite(elapsed_seconds) or elapsed_seconds < 0:
                    raise ValueError(f"invalid benchmark row in {path}: {row}")
                series.setdefault(mode, []).append((records, elapsed_seconds))

    for points in series.values():
        points.sort()
    return series


def _svg_chart(series: dict[str, list[tuple[int, float]]]) -> str:
    if not series:
        raise ValueError("no benchmark rows found")

    left, top, right, bottom = 95, 65, 235, 80
    plot_width = WIDTH - left - right
    plot_height = HEIGHT - top - bottom
    all_points = [point for points in series.values() for point in points]
    minimum_size = min(size for size, _ in all_points)
    maximum_size = max(size for size, _ in all_points)
    maximum_seconds = max(value for _, value in all_points)
    y_max = maximum_seconds * 1.1 if maximum_seconds else 1.0
    log_min, log_max = math.log10(minimum_size), math.log10(maximum_size)

    def x_position(size: int) -> float:
        if log_min == log_max:
            return left + plot_width / 2
        return left + (math.log10(size) - log_min) / (log_max - log_min) * plot_width

    def y_position(value: float) -> float:
        return top + plot_height - value / y_max * plot_height

    def label_size(size: int) -> str:
        return f"{size // 1_000}k" if size >= 1_000 and size % 1_000 == 0 else f"{size:,}"

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}">',
        '<rect width="100%" height="100%" fill="white"/>',
        '<text x="95" y="32" font-family="sans-serif" font-size="21" font-weight="bold">Processing time by dataset size</text>',
        '<text x="480" y="540" text-anchor="middle" font-family="sans-serif" font-size="14">Records processed (log scale)</text>',
        f'<text x="24" y="{top + plot_height / 2}" transform="rotate(-90 24 {top + plot_height / 2})" text-anchor="middle" font-family="sans-serif" font-size="14">Median elapsed time (seconds)</text>',
    ]

    tick_count = 5
    for index in range(tick_count + 1):
        value = y_max * index / tick_count
        y = y_position(value)
        parts.append(f'<line x1="{left}" y1="{y:.1f}" x2="{left + plot_width}" y2="{y:.1f}" stroke="#e5e7eb"/>')
        tick_label = f"{value:.3f}" if y_max < 1 else f"{value:,.1f}"
        parts.append(f'<text x="{left - 10}" y="{y + 5:.1f}" text-anchor="end" font-family="sans-serif" font-size="12" fill="#374151">{tick_label}</text>')

    sizes = sorted({size for size, _ in all_points})
    for size in sizes:
        x = x_position(size)
        parts.append(f'<line x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{top + plot_height}" stroke="#f3f4f6"/>')
        parts.append(f'<text x="{x:.1f}" y="{top + plot_height + 24}" text-anchor="middle" font-family="sans-serif" font-size="12" fill="#374151">{label_size(size)}</text>')

    for index, (mode, points) in enumerate(sorted(series.items())):
        color = COLORS[index % len(COLORS)]
        coords = " ".join(f"{x_position(size):.1f},{y_position(value):.1f}" for size, value in points)
        parts.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="3"/>')
        for size, value in points:
            x, y = x_position(size), y_position(value)
            parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{color}"/>')
        legend_y = top + 20 + index * 26
        parts.append(f'<line x1="{left + plot_width + 28}" y1="{legend_y}" x2="{left + plot_width + 52}" y2="{legend_y}" stroke="{color}" stroke-width="3"/>')
        parts.append(f'<text x="{left + plot_width + 60}" y="{legend_y + 5}" font-family="sans-serif" font-size="13" fill="#111827">{escape(mode)}</text>')

    parts.append("</svg>")
    return "\n".join(parts)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("csv_files", nargs="+", type=Path, help="benchmark result CSV files to compare")
    parser.add_argument("--output", type=Path, required=True, help="output SVG file path")
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(_svg_chart(_load_rows(args.csv_files)), encoding="utf-8")


if __name__ == "__main__":
    main()

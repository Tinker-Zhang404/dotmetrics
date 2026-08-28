from __future__ import annotations

import sys
from pathlib import Path
from typing import Sequence

import matplotlib

matplotlib.use("Agg")

import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import numpy as np
from scipy.stats import norm

from .logging_utils import logger



def setup_matplotlib_font() -> str:
    candidates: Sequence[str]
    if sys.platform.startswith("win"):
        candidates = (
            "Segoe UI",
            "Arial",
            "DejaVu Sans",
        )
    else:
        candidates = (
            "DejaVu Sans",
            "Arial",
        )

    for font_name in candidates:
        try:
            font_path = fm.findfont(fm.FontProperties(family=font_name))
            if font_path:
                matplotlib.rcParams["font.sans-serif"] = [font_name]
                matplotlib.rcParams["axes.unicode_minus"] = False
                return font_name
        except Exception:
            continue

    matplotlib.rcParams["font.sans-serif"] = ["Arial"]
    matplotlib.rcParams["axes.unicode_minus"] = False
    return "Arial"


UI_FONT = setup_matplotlib_font()


class Visualizer:
    @staticmethod
    def create_histogram(measurements: list[float], output_path: str | Path) -> bool:
        output = str(output_path)
        try:
            plt.rcParams["font.sans-serif"] = [UI_FONT]
            plt.rcParams["axes.unicode_minus"] = False

            if not measurements:
                plt.figure(figsize=(6, 4), dpi=100)
                plt.text(0.5, 0.5, "No measurements", ha="center", va="center", fontsize=14)
                plt.title("Particle Size Distribution", fontsize=14, fontweight="bold")
                plt.tight_layout()
                plt.savefig(output, dpi=150, bbox_inches="tight")
                return False

            mean_value = float(np.mean(measurements))
            std_value = float(np.std(measurements))

            plt.figure(figsize=(6, 4), dpi=100)
            counts, bins, _ = plt.hist(
                measurements,
                bins=10,
                color="skyblue",
                edgecolor="red",
                alpha=0.8,
                density=True,
            )
            x_axis = np.linspace(min(bins), max(bins), 200)
            y_axis = norm.pdf(x_axis, mean_value, std_value if std_value > 0 else 1e-6)
            plt.plot(x_axis, y_axis, "r-", linewidth=2)
            plt.xlabel("Particle diameter (nm)", fontsize=12)
            plt.ylabel("Probability density", fontsize=12)
            plt.title("Particle Size Distribution", fontsize=14, fontweight="bold")
            plt.grid(alpha=0.4)
            plt.tight_layout()
            plt.text(
                0.02,
                0.98,
                f"Mean: {mean_value:.2f} nm\nSD: {std_value:.2f} nm\nCount: {len(measurements)}",
                transform=plt.gca().transAxes,
                verticalalignment="top",
                fontsize=9,
                bbox={"boxstyle": "round", "facecolor": "wheat", "alpha": 0.5},
            )
            plt.savefig(output, dpi=150, bbox_inches="tight")
            return bool(counts.size)
        except Exception as exc:
            logger.error("Failed to create histogram: %s", exc)
            return False
        finally:
            try:
                plt.close()
            except Exception:
                pass

    @staticmethod
    def create_stats_table(measurements: list[float], output_path: str | Path) -> bool:
        output = str(output_path)
        try:
            plt.rcParams["font.sans-serif"] = [UI_FONT]
            plt.rcParams["axes.unicode_minus"] = False

            if not measurements:
                stats = [
                    ["Mean diameter (nm)", "N/A"],
                    ["Standard deviation (nm)", "N/A"],
                    ["Median diameter (nm)", "N/A"],
                    ["Minimum diameter (nm)", "N/A"],
                    ["Maximum diameter (nm)", "N/A"],
                    ["Particle count", "0"],
                    ["Coefficient of variation (%)", "N/A"],
                ]
            else:
                mean_value = float(np.mean(measurements))
                std_value = float(np.std(measurements))
                stats = [
                    ["Mean diameter (nm)", f"{mean_value:.2f}"],
                    ["Standard deviation (nm)", f"{std_value:.2f}"],
                    ["Median diameter (nm)", f"{np.median(measurements):.2f}"],
                    ["Minimum diameter (nm)", f"{np.min(measurements):.2f}"],
                    ["Maximum diameter (nm)", f"{np.max(measurements):.2f}"],
                    ["Particle count", f"{len(measurements)}"],
                    ["Coefficient of variation (%)", f"{std_value / mean_value * 100:.2f}" if mean_value > 0 else "N/A"],
                ]

            fig, ax = plt.subplots(figsize=(6, 2), dpi=100)
            ax.axis("off")
            table = ax.table(
                cellText=stats,
                colLabels=["Statistic", "Value"],
                cellLoc="center",
                loc="center",
            )
            table.auto_set_font_size(False)
            table.set_fontsize(10)
            table.scale(1.1, 1.4)

            for (row, _column), cell in table.get_celld().items():
                cell.set_edgecolor("gray")
                cell.set_linewidth(0.7)
                if row == 0:
                    cell.set_facecolor("#BFDFFF")
                    cell._text.set_weight("bold")

            plt.tight_layout()
            plt.savefig(output, dpi=150, bbox_inches="tight")
            return True
        except Exception as exc:
            logger.error("Failed to create stats table: %s", exc)
            return False
        finally:
            try:
                plt.close()
            except Exception:
                pass

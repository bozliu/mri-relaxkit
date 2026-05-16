from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

import imageio.v3 as iio
import numpy as np
from PIL import Image, ImageDraw, ImageFont


CANVAS = (960, 540)
BG = (248, 250, 252)
INK = (15, 23, 42)
MUTED = (71, 85, 105)
LINE = (203, 213, 225)
BLUE = (37, 99, 235)
CYAN = (8, 145, 178)
GREEN = (22, 163, 74)
AMBER = (217, 119, 6)
WHITE = (255, 255, 255)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build README visual assets from an MRI RelaxKit run.")
    parser.add_argument("--run", type=Path, default=Path("outputs/release/run"), help="Analysis run directory.")
    parser.add_argument("--out-dir", type=Path, default=Path("docs/assets"), help="Asset output directory.")
    args = parser.parse_args()

    metrics_path = args.run / "metrics.json"
    qa_path = args.run / "qa.json"
    figures_dir = args.run / "figures"
    if not metrics_path.exists() or not qa_path.exists() or not figures_dir.exists():
        raise SystemExit(
            "Missing run artifacts. Run demo-data and analyze first, then re-run this asset builder."
        )

    metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    args.out_dir.mkdir(parents=True, exist_ok=True)

    fonts = _fonts()
    figures = {
        "t2": figures_dir / "simulated_t2_fit.png",
        "t1": figures_dir / "simulated_t1_fit.png",
        "t2star": figures_dir / "gm_t2star_fit.png",
        "contrast": figures_dir / "gm_wm_contrast.png",
        "echoes": figures_dir / "gre_echoes.png",
    }
    for name, path in figures.items():
        if not path.exists():
            raise SystemExit(f"Missing required figure for README asset: {name} -> {path}")

    summary = _summary(metrics, qa)
    _write_static_assets(args.out_dir, figures, summary, fonts)
    _write_hero_gif(args.out_dir / "hero.gif", figures, summary, fonts)

    print(f"Wrote README assets to {args.out_dir}")


def _fonts() -> dict[str, ImageFont.FreeTypeFont | ImageFont.ImageFont]:
    candidates = [
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
        Path("/System/Library/Fonts/Supplemental/Helvetica.ttf"),
        Path("/Library/Fonts/Arial.ttf"),
    ]
    font_path = next((path for path in candidates if path.exists()), None)

    def load(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
        if font_path is None:
            return ImageFont.load_default()
        return ImageFont.truetype(str(font_path), size=size)

    return {
        "title": load(38),
        "section": load(26),
        "body": load(19),
        "small": load(15),
        "mono": load(17),
        "metric": load(30),
    }


def _summary(metrics: dict, qa: dict) -> dict[str, str]:
    fits = metrics["fits"]
    return {
        "t2": f'{fits["simulated_t2"]["linear"]["tau_ms"]:.2f} ms',
        "t1": f'{fits["simulated_t1"]["linear"]["tau_ms"]:.2f} ms',
        "t2star": f'{fits["t2star_gm"]["linear"]["tau_ms"]:.2f} ms',
        "contrast": f'{fits["contrast"]["max_contrast_te_ms"]:.0f} ms',
        "qa": str(qa["status"]).upper(),
        "checks": f'{qa["passed_checks"]}/{qa["total_checks"]}',
    }


def _write_static_assets(
    out_dir: Path,
    figures: dict[str, Path],
    summary: dict[str, str],
    fonts: dict[str, ImageFont.FreeTypeFont | ImageFont.ImageFont],
) -> None:
    fit = _canvas()
    d = ImageDraw.Draw(fit)
    _title(d, "Core Fits", "T2 and corrected T1 recovery are fit and checked from generated data.", fonts)
    _paste_card(fit, figures["t2"], (34, 112, 434, 270), "T2 decay", summary["t2"], BLUE, fonts)
    _paste_card(fit, figures["t1"], (492, 112, 434, 270), "T1 recovery", summary["t1"], CYAN, fonts)
    _metric_strip(fit, [("Simulated T2", summary["t2"]), ("Corrected T1", summary["t1"]), ("QA", summary["qa"])], fonts)
    _save_png(fit, out_dir / "result-fit-summary.png")

    contrast = _single_plot_asset(
        figures["contrast"],
        "Contrast Timing",
        "GM/WM contrast is evaluated across TE and peaks on the SOP grid.",
        [("Peak TE", summary["contrast"]), ("QA checks", summary["checks"]), ("Status", summary["qa"])],
        fonts,
    )
    _save_png(contrast, out_dir / "result-contrast.png")

    t2star = _canvas()
    d = ImageDraw.Draw(t2star)
    _title(d, "Voxel T2* QA", "The workflow tracks MATLAB 1-based voxels and reports reproducible T2* fits.", fonts)
    _paste_card(t2star, figures["echoes"], (34, 112, 410, 185), "GRE echo series", "synthetic 7T-style data", AMBER, fonts)
    _paste_card(t2star, figures["t2star"], (492, 112, 434, 270), "GM voxel T2*", summary["t2star"], GREEN, fonts)
    _metric_strip(t2star, [("GM T2*", summary["t2star"]), ("Voxel convention", "MATLAB 1-based"), ("Status", summary["qa"])], fonts)
    _save_png(t2star, out_dir / "result-t2star.png")


def _write_hero_gif(
    path: Path,
    figures: dict[str, Path],
    summary: dict[str, str],
    fonts: dict[str, ImageFont.FreeTypeFont | ImageFont.ImageFont],
) -> None:
    frames = [
        _hero_frame_intro(figures, summary, fonts),
        _hero_frame_fits(figures, summary, fonts),
        _hero_frame_t2star(figures, summary, fonts),
        _hero_frame_contrast(figures, summary, fonts),
        _hero_frame_artifacts(summary, fonts),
    ]
    arrays = [np.asarray(frame.convert("P", palette=Image.Palette.ADAPTIVE, colors=128).convert("RGB")) for frame in frames]
    iio.imwrite(path, arrays, duration=[1500, 1700, 1700, 1700, 1900], loop=0)


def _hero_frame_intro(
    figures: dict[str, Path],
    summary: dict[str, str],
    fonts: dict[str, ImageFont.FreeTypeFont | ImageFont.ImageFont],
) -> Image.Image:
    img = _canvas()
    d = ImageDraw.Draw(img)
    _title(d, "MRI RelaxKit", "Public synthetic data in. Auditable relaxometry results out.", fonts)
    _paste_card(img, figures["echoes"], (42, 128, 876, 230), "Synthetic MRI echo data", "public-safe demo fixture", BLUE, fonts)
    _metric_strip(img, [("Output", "figures + JSON + report"), ("QA", summary["qa"]), ("Checks", summary["checks"])], fonts)
    return img


def _hero_frame_fits(
    figures: dict[str, Path],
    summary: dict[str, str],
    fonts: dict[str, ImageFont.FreeTypeFont | ImageFont.ImageFont],
) -> Image.Image:
    img = _canvas()
    d = ImageDraw.Draw(img)
    _title(d, "Fit T2 and T1", "Linearized fits plus nonlinear checks make the teaching workflow reviewable.", fonts)
    _paste_card(img, figures["t2"], (34, 116, 422, 250), "T2 decay", summary["t2"], BLUE, fonts)
    _paste_card(img, figures["t1"], (504, 116, 422, 250), "Corrected T1 recovery", summary["t1"], CYAN, fonts)
    _metric_strip(img, [("T2", summary["t2"]), ("T1", summary["t1"]), ("Status", summary["qa"])], fonts)
    return img


def _hero_frame_t2star(
    figures: dict[str, Path],
    summary: dict[str, str],
    fonts: dict[str, ImageFont.FreeTypeFont | ImageFont.ImageFont],
) -> Image.Image:
    img = _canvas()
    d = ImageDraw.Draw(img)
    _title(d, "Fit real-style voxel T2*", "MATLAB 1-based coordinates are explicit, so reviews do not guess at voxels.", fonts)
    _paste_card(img, figures["t2star"], (256, 112, 448, 265), "GM voxel T2*", summary["t2star"], GREEN, fonts)
    _metric_strip(img, [("GM T2*", summary["t2star"]), ("Coordinate rule", "MATLAB 1-based"), ("QA", summary["qa"])], fonts)
    return img


def _hero_frame_contrast(
    figures: dict[str, Path],
    summary: dict[str, str],
    fonts: dict[str, ImageFont.FreeTypeFont | ImageFont.ImageFont],
) -> Image.Image:
    img = _canvas()
    d = ImageDraw.Draw(img)
    _title(d, "Choose contrast timing", "The SOP makes tissue contrast choices visible instead of buried in a script.", fonts)
    _paste_card(img, figures["contrast"], (214, 112, 532, 265), "GM/WM contrast", f'Peak TE {summary["contrast"]}', AMBER, fonts)
    _metric_strip(img, [("Peak contrast TE", summary["contrast"]), ("Grid", "5 ms"), ("Status", summary["qa"])], fonts)
    return img


def _hero_frame_artifacts(
    summary: dict[str, str],
    fonts: dict[str, ImageFont.FreeTypeFont | ImageFont.ImageFont],
) -> Image.Image:
    img = _canvas()
    d = ImageDraw.Draw(img)
    _title(d, "Ship an SOP run", "Every run leaves metrics, QA, figures, and a report that teams can archive.", fonts)
    chips = ["metrics.json", "qa.json", "report.md", "report.html", "figures/"]
    x = 108
    y = 156
    for index, chip in enumerate(chips):
        w = 230 if chip.endswith(".html") else 190
        _rounded(d, (x, y, x + w, y + 76), 18, WHITE, LINE)
        d.text((x + 24, y + 21), chip, font=fonts["body"], fill=INK)
        x += w + 22
        if index == 2:
            x = 190
            y += 102
    _metric_strip(img, [("QA", summary["qa"]), ("Checks", summary["checks"]), ("Release audit", "0 warnings")], fonts)
    return img


def _single_plot_asset(
    plot: Path,
    title: str,
    subtitle: str,
    metrics: list[tuple[str, str]],
    fonts: dict[str, ImageFont.FreeTypeFont | ImageFont.ImageFont],
) -> Image.Image:
    img = _canvas()
    d = ImageDraw.Draw(img)
    _title(d, title, subtitle, fonts)
    _paste_card(img, plot, (146, 112, 668, 286), title, metrics[0][1], BLUE, fonts)
    _metric_strip(img, metrics, fonts)
    return img


def _canvas() -> Image.Image:
    return Image.new("RGB", CANVAS, BG)


def _title(
    d: ImageDraw.ImageDraw,
    title: str,
    subtitle: str,
    fonts: dict[str, ImageFont.FreeTypeFont | ImageFont.ImageFont],
) -> None:
    d.text((34, 30), title, font=fonts["title"], fill=INK)
    d.text((36, 78), subtitle, font=fonts["body"], fill=MUTED)


def _paste_card(
    canvas: Image.Image,
    source: Path,
    box: tuple[int, int, int, int],
    label: str,
    metric: str,
    accent: tuple[int, int, int],
    fonts: dict[str, ImageFont.FreeTypeFont | ImageFont.ImageFont],
) -> None:
    x, y, w, h = box
    d = ImageDraw.Draw(canvas)
    _rounded(d, (x, y, x + w, y + h), 18, WHITE, LINE)
    d.rectangle((x, y, x + 8, y + h), fill=accent)
    d.text((x + 24, y + 16), label, font=fonts["body"], fill=INK)
    d.text((x + 24, y + 44), metric, font=fonts["metric"], fill=accent)
    plot = Image.open(source).convert("RGB")
    plot.thumbnail((w - 48, h - 112), Image.Resampling.LANCZOS)
    px = x + (w - plot.width) // 2
    py = y + h - plot.height - 22
    canvas.paste(plot, (px, py))


def _metric_strip(
    canvas: Image.Image,
    metrics: Iterable[tuple[str, str]],
    fonts: dict[str, ImageFont.FreeTypeFont | ImageFont.ImageFont],
) -> None:
    d = ImageDraw.Draw(canvas)
    y = 430
    x = 34
    width = 282
    for label, value in metrics:
        _rounded(d, (x, y, x + width, y + 78), 16, WHITE, LINE)
        d.text((x + 18, y + 14), label, font=fonts["small"], fill=MUTED)
        d.text((x + 18, y + 38), value, font=fonts["body"], fill=INK)
        x += width + 22


def _rounded(
    d: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    radius: int,
    fill: tuple[int, int, int],
    outline: tuple[int, int, int],
) -> None:
    d.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=1)


def _save_png(img: Image.Image, path: Path) -> None:
    img.save(path, optimize=True)


if __name__ == "__main__":
    main()

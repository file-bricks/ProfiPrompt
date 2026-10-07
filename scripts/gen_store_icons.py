"""Generate Store and runtime variants from the approved ProfiPrompt artwork."""
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
STORE = ROOT / "store_assets"
SIZES = (16, 20, 24, 30, 32, 36, 40, 48, 60, 64, 72, 80, 96, 256)


def resized(master, size):
    if size[0] == size[1]:
        return master.resize(size, Image.Resampling.LANCZOS)
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    side = min(size)
    image = master.resize((side, side), Image.Resampling.LANCZOS)
    canvas.alpha_composite(image, ((size[0] - side) // 2, (size[1] - side) // 2))
    return canvas


def main():
    # This approved source is immutable input. Never derive branding from a
    # previously published Store tile: that tile may still contain old artwork.
    master = Image.open(ROOT / "assets" / "icon-master.png").convert("RGBA")
    STORE.mkdir(parents=True, exist_ok=True)
    # Refresh existing Store logo variants as well as canonical manifest names.
    for path in STORE.glob("*.png"):
        if ".targetsize-" in path.name:
            continue
        with Image.open(path) as image:
            size = image.size
        resized(master, size).save(path)
    canonical = {
        "Square44x44Logo.png": (44, 44),
        "Square150x150Logo.png": (150, 150),
        "Square310x310Logo.png": (310, 310),
        "Wide310x150Logo.png": (310, 150),
        "StoreLogo.png": (50, 50),
        "icon_50x50.png": (50, 50),
    }
    for name, size in canonical.items():
        resized(master, size).save(STORE / name)
    for directory in (ROOT, ROOT / "assets"):
        for path in directory.glob("*.ico"):
            sizes = (16, 24, 32, 48) if path.stem == "favicon" else (16, 24, 32, 48, 64, 128, 256)
            master.save(path, format="ICO", sizes=[(s, s) for s in sizes])
    for relative in ("DesktopIcon.ico", "assets/app_icon.ico", "assets/profiprompt.ico"):
        target = ROOT / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        master.save(target, format="ICO", sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
    for relative, size in (("DesktopIcon.png", 1024), ("ProfiPrompt.png", 1024), ("icon.png", 1024),
                           ("assets/icon.png", 1024), ("assets/favicon.png", 32)):
        resized(master, (size, size)).save(ROOT / relative)
    for size in SIZES:
        image = resized(master, (size, size))
        for form in ("", "_altform-unplated", "_altform-lightunplated"):
            image.save(STORE / f"Square44x44Logo.targetsize-{size}{form}.png")


if __name__ == "__main__":
    main()

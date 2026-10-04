"""shot3 (1280x769): the real CLI run next to the exported spreadsheet, dark."""
import sys
from pathlib import Path
from PIL import Image

raw, out = Path(sys.argv[1]), Path(sys.argv[2])
W, H = 1280, 769
bg = Image.new("RGB", (W, H), (21, 23, 27))
term = Image.open(raw / "terminal_dark.png").convert("RGB")
csv = Image.open(raw / "csv_dark.png").convert("RGB")
t = term.resize((470, int(term.height * 470 / term.width)), Image.LANCZOS)
c = csv.resize((690, int(csv.height * 690 / csv.width)), Image.LANCZOS)
top = (H - max(t.height, c.height)) // 2
bg.paste(t, (40, top))
bg.paste(c, (550, top))
bg.save(out / "shot3.png")
print("shot3", bg.size, "terminal", t.size, "csv", c.size)

"""
flyer_images の画像から、Instagram向けのコピーを ig/ フォルダに作る。

🌸2026-10-01 追加
- 日本語のファイル名のままだと、Instagramが画像を取りに行くときに失敗することがあるため、
  英数字だけの名前（画像の中身から作るハッシュ値）のJPEGコピーを作る。
- 元のファイル名は ig/index.json に残し、SNS自動投稿側はそれを見て
  「どんな画像か」をAIに伝える（ファイル名にタイトルを入れる運用はそのまま使える）。
- Instagramの決まりに合わせて整える:
    ・形式はJPEG（透過PNGは白背景にする）
    ・縦横比は 4:5（0.8）〜 1.91:1 の範囲に収める（はみ出す分は白い余白を足す。切り取らない）
    ・長い辺は最大1440ピクセル
- 元の画像を消したら、対応するコピーも ig/ から消える。
- 中身が同じなら名前を変えてもコピーのURLは変わらない（予約済みの投稿が壊れにくい）。
"""

import hashlib
import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = ROOT / "ig"
IMAGE_EXTENSIONS = (".png", ".jpg", ".jpeg")
MAX_SIDE = 1440
MIN_RATIO = 0.8    # 縦長の限界（4:5）
MAX_RATIO = 1.91   # 横長の限界（1.91:1）
PAD_COLOR = (255, 255, 255)


def to_instagram_jpeg(src: Path, dst: Path) -> None:
    with Image.open(src) as im:
        im.load()
        # 透過のある画像は白背景に重ねる
        if im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info):
            im = im.convert("RGBA")
            bg = Image.new("RGB", im.size, PAD_COLOR)
            bg.paste(im, mask=im.split()[-1])
            im = bg
        else:
            im = im.convert("RGB")

        # 縦横比を範囲内に収める（余白を足す）
        w, h = im.size
        ratio = w / h
        if ratio > MAX_RATIO:
            new_h = int(round(w / MAX_RATIO))
            canvas = Image.new("RGB", (w, new_h), PAD_COLOR)
            canvas.paste(im, (0, (new_h - h) // 2))
            im = canvas
        elif ratio < MIN_RATIO:
            new_w = int(round(h * MIN_RATIO))
            canvas = Image.new("RGB", (new_w, h), PAD_COLOR)
            canvas.paste(im, ((new_w - w) // 2, 0))
            im = canvas

        # 大きすぎる画像は縮小
        if max(im.size) > MAX_SIDE:
            im.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)

        im.save(dst, "JPEG", quality=90, optimize=True)


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    sources = sorted(
        p for p in ROOT.iterdir()
        if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
    )

    index = []
    keep = set()
    for src in sources:
        digest = hashlib.sha1(src.read_bytes()).hexdigest()[:16]
        dst_name = f"{digest}.jpg"
        dst = OUT_DIR / dst_name
        keep.add(dst_name)
        if not dst.exists():
            try:
                to_instagram_jpeg(src, dst)
                print(f"作成: {src.name} → ig/{dst_name}")
            except Exception as e:
                print(f"【スキップ】{src.name} を変換できませんでした: {e}")
                keep.discard(dst_name)
                continue
        index.append({"file": f"ig/{dst_name}", "name": src.name})

    # 元画像が消えたコピーを片付ける
    for old in OUT_DIR.glob("*.jpg"):
        if old.name not in keep:
            old.unlink()
            print(f"削除: ig/{old.name}（元の画像がなくなったため）")

    (OUT_DIR / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"ig/index.json に {len(index)} 枚を登録しました。")


if __name__ == "__main__":
    main()

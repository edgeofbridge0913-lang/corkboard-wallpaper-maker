import math
import random
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFilter, ImageOps
from pillow_heif import register_heif_opener


register_heif_opener()


RESOLUTIONS = {
    "1920 x 1080": (1920, 1080),
    "2560 x 1440": (2560, 1440),
    "3840 x 2160": (3840, 2160),
}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".heif"}


class WallpaperMaker:
    def __init__(self, root):
        self.root = root
        self.root.title("Corkboard Wallpaper Maker")
        self.root.geometry("1120x780")
        self.root.minsize(900, 650)

        self.folder = None
        self.corkboard_path = None
        self.preview_image = None
        self.last_image = None

        self._build_ui()

    def _build_ui(self):
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(1, weight=1)

        header = ctk.CTkFrame(self.root, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", padx=28, pady=(24, 16))
        header.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            header,
            text="CORKBOARD / WALLPAPER",
            text_color="#d8895b",
            font=ctk.CTkFont(size=13, weight="bold"),
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            header,
            text="壁紙メーカー",
            font=ctk.CTkFont(size=28, weight="bold"),
        ).grid(row=1, column=0, sticky="w", pady=(2, 8))
        self.folder_label = ctk.CTkLabel(
            header, text="写真フォルダが選択されていません", text_color="#a5a7ad"
        )
        self.folder_label.grid(row=2, column=0, sticky="w")

        controls = ctk.CTkFrame(header, fg_color="transparent")
        controls.grid(row=0, column=1, rowspan=3, sticky="e")
        ctk.CTkButton(
            controls, text="写真フォルダ", width=128, command=self.choose_folder
        ).grid(row=0, column=0, padx=(0, 8))
        ctk.CTkButton(
            controls,
            text="コルク背景",
            width=112,
            fg_color="#6d4935",
            hover_color="#875b40",
            command=self.choose_corkboard,
        ).grid(row=0, column=1, padx=(0, 16))
        ctk.CTkLabel(controls, text="解像度", text_color="#a5a7ad").grid(
            row=0, column=2, padx=(0, 8)
        )
        self.resolution = tk.StringVar(value="1920 x 1080")
        ctk.CTkComboBox(
            controls,
            variable=self.resolution,
            values=list(RESOLUTIONS),
            width=132,
            state="readonly",
        ).grid(row=0, column=3)

        self.corkboard_label = ctk.CTkLabel(
            header, text="背景: 自動生成のコルクテクスチャ", text_color="#777b85"
        )
        self.corkboard_label.grid(row=3, column=0, sticky="w", pady=(4, 0))

        preview_frame = ctk.CTkFrame(self.root, corner_radius=14, fg_color="#24252a")
        preview_frame.grid(row=1, column=0, sticky="nsew", padx=28, pady=(0, 16))
        preview_frame.grid_columnconfigure(0, weight=1)
        preview_frame.grid_rowconfigure(0, weight=1)
        self.preview = ctk.CTkLabel(
            preview_frame,
            text="写真フォルダを選択して生成してください",
            text_color="#777b85",
            font=ctk.CTkFont(size=15),
        )
        self.preview.grid(row=0, column=0, sticky="nsew", padx=18, pady=18)

        footer = ctk.CTkFrame(self.root, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", padx=28, pady=(0, 24))
        footer.grid_columnconfigure(0, weight=1)
        self.status = ctk.CTkLabel(
            footer, text="JPG / PNG / HEIC に対応", text_color="#8d9099"
        )
        self.status.grid(row=0, column=0, sticky="w")
        self.generate_button = ctk.CTkButton(
            footer, text="生成", width=110, command=self.generate_wallpaper
        )
        self.generate_button.grid(row=0, column=1, padx=(8, 0))
        self.shuffle_button = ctk.CTkButton(
            footer,
            text="再生成",
            width=110,
            fg_color="#3f424a",
            hover_color="#555963",
            command=self.regenerate,
            state="disabled",
        )
        self.shuffle_button.grid(row=0, column=2, padx=(8, 0))
        self.save_button = ctk.CTkButton(
            footer,
            text="壁紙を保存",
            width=126,
            fg_color="#c76845",
            hover_color="#df7952",
            command=self.save_current,
            state="disabled",
        )
        self.save_button.grid(row=0, column=3, padx=(8, 0))

    def choose_folder(self):
        selected = filedialog.askdirectory(title="写真フォルダを選択")
        if selected:
            self.folder = Path(selected)
            count = sum(
                1
                for path in self.folder.iterdir()
                if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
            )
            self.folder_label.configure(text=f"選択中: {self.folder} ({count}枚)")
            self.status.configure(text="準備完了。壁紙を生成できます")

    def generate_wallpaper(self):
        if self.folder is None:
            messagebox.showinfo("フォルダ未選択", "先に写真フォルダを選択してください。")
            return

        width, height = RESOLUTIONS[self.resolution.get()]
        self._start_generation(width, height)

    def regenerate(self):
        if self.folder is None:
            return
        width, height = RESOLUTIONS[self.resolution.get()]
        self._start_generation(width, height)

    def _start_generation(self, width, height):
        self.generate_button.configure(state="disabled")
        self.shuffle_button.configure(state="disabled")
        self.save_button.configure(state="disabled")
        self.status.configure(text="写真をグリッドに配置しています...")
        threading.Thread(
            target=self._generate_in_background,
            args=(width, height, self.corkboard_path),
            daemon=True,
        ).start()

    def choose_corkboard(self):
        selected = filedialog.askopenfilename(
            title="コルク背景画像を選択",
            filetypes=[
                ("画像ファイル", "*.jpg *.jpeg *.png *.heic *.heif"),
                ("すべてのファイル", "*.*"),
            ],
        )
        if selected:
            self.corkboard_path = Path(selected)
            self.corkboard_label.configure(text=f"背景: {self.corkboard_path.name}")
            self.status.configure(text="コルク背景を設定しました")

    def _generate_in_background(self, width, height, corkboard_path):
        try:
            image = create_wallpaper(self.folder, width, height, corkboard_path)
        except Exception as error:
            error_message = str(error)
            self.root.after(0, lambda: self._generation_failed(error_message))
            return
        self.root.after(0, lambda: self._show_generated_image(image))

    def _show_generated_image(self, image):
        self.last_image = image
        self._update_preview(image)
        self.generate_button.configure(state="normal")
        self.shuffle_button.configure(state="normal")
        self.save_button.configure(state="normal")
        self.status.configure(text="生成完了。再生成または保存ができます")

    def save_current(self):
        if self.last_image is None:
            return
        output_path = filedialog.asksaveasfilename(
            title="壁紙を保存",
            defaultextension=".jpg",
            filetypes=[("JPEG画像", "*.jpg"), ("PNG画像", "*.png")],
            initialfile="corkboard_wallpaper.jpg",
        )
        if output_path:
            save_image = (
                self.last_image.convert("RGB")
                if output_path.lower().endswith(".jpg")
                else self.last_image
            )
            save_image.save(output_path, quality=95)
            self.status.configure(text=f"保存しました: {output_path}")

    def _generation_failed(self, error):
        self.generate_button.configure(state="normal")
        self.status.configure(text="生成に失敗しました")
        messagebox.showerror("生成エラー", error)

    def _update_preview(self, image):
        preview = image.copy()
        preview.thumbnail((820, 520), Image.Resampling.LANCZOS)
        self.preview_image = ctk.CTkImage(
            light_image=preview, dark_image=preview, size=preview.size
        )
        self.preview.configure(image=self.preview_image, text="")


def create_corkboard(size, texture_path=None):
    width, height = size
    if texture_path is not None:
        with Image.open(texture_path) as source:
            texture = ImageOps.exif_transpose(source).convert("RGB")
            scale = min(width / texture.width, height / texture.height, 1.0)
            if scale < 1.0:
                texture = texture.resize(
                    (max(1, int(texture.width * scale)), max(1, int(texture.height * scale))),
                    Image.Resampling.LANCZOS,
                )

        board = Image.new("RGB", size)
        for x in range(0, width, texture.width):
            for y in range(0, height, texture.height):
                board.paste(texture, (x, y))
        return board

    base_color = (139, 83, 48)
    board = Image.new("RGB", size, base_color)

    # 小さなノイズ画像を拡大して、低コストでコルクの粒感を作る。
    texture = Image.effect_noise((max(1, width // 8), max(1, height // 8)), 28)
    texture = texture.resize(size, Image.Resampling.BILINEAR).convert("RGB")
    texture = ImageOps.colorize(texture.convert("L"), (93, 48, 26), (190, 126, 76))
    board = Image.blend(board, texture, 0.28)

    draw = ImageDraw.Draw(board, "RGBA")
    for _ in range(max(80, width // 12)):
        x = random.randrange(width)
        y = random.randrange(height)
        radius = random.choice((1, 1, 2, 3))
        color = random.choice(((70, 35, 20, 35), (235, 170, 105, 25)))
        draw.ellipse((x - radius, y - radius, x + radius, y + radius), fill=color)
    return board


def make_polaroid(photo_path, board_width, max_width=None, max_height=None):
    with Image.open(photo_path) as source:
        photo = ImageOps.exif_transpose(source).convert("RGB")
        default_min = max(220, board_width // 8)
        default_max = max(280, board_width // 5)
        if max_width is None:
            min_width, max_card_width = default_min, default_max
        else:
            max_card_width = max(160, int(max_width))
            min_width = max(150, int(max_card_width * 0.92))
        card_width = random.randint(min_width, max(min_width, max_card_width))
        photo_width = card_width - 36
        photo_height = int(photo_width * random.uniform(0.68, 0.82))
        if max_height is not None:
            photo_height = min(photo_height, max(40, int(max_height) - 76))
        photo = ImageOps.fit(photo, (photo_width, photo_height), method=Image.Resampling.LANCZOS)

    card_height = photo_height + 76
    card = Image.new("RGBA", (card_width, card_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)
    draw.rectangle((4, 5, card_width - 2, card_height - 1), fill=(255, 255, 252, 255))
    card.paste(photo, (18, 19))

    # ピンは写真と一緒に回転するため、カード上に描画する。
    pin_x = card_width // 2
    pin_y = 13
    draw.ellipse((pin_x - 16, pin_y - 12, pin_x + 16, pin_y + 18), fill=(70, 34, 22, 120))
    pin_color = random.choice(((207, 48, 44, 255), (236, 177, 35, 255), (43, 116, 172, 255)))
    draw.ellipse((pin_x - 13, pin_y - 13, pin_x + 13, pin_y + 13), fill=pin_color)
    draw.ellipse((pin_x - 7, pin_y - 8, pin_x + 1, pin_y), fill=(255, 255, 255, 130))
    draw.line((pin_x, pin_y + 12, pin_x, pin_y + 28), fill=(70, 70, 70, 220), width=3)

    angle = random.uniform(-15, 15)
    rotated = card.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
    shadow = Image.new("RGBA", rotated.size, (0, 0, 0, 0))
    shadow.paste((22, 12, 8, 105), (10, 12), rotated.getchannel("A"))
    shadow = shadow.filter(ImageFilter.GaussianBlur(9))
    result = Image.new("RGBA", rotated.size, (0, 0, 0, 0))
    result.alpha_composite(shadow)
    result.alpha_composite(rotated)
    return result


def create_wallpaper(folder, width, height, texture_path=None):
    paths = [
        path
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    ]
    if not paths:
        raise ValueError("選択したフォルダに JPG / PNG / HEIC 画像がありません。")

    random.shuffle(paths)
    photo_count = min(len(paths), random.randint(8, 15))
    board = create_corkboard((width, height), texture_path).convert("RGBA")
    margin = max(30, width // 50)

    selected_paths = paths[:photo_count]
    aspect_ratio = width / height
    columns = min(
        range(1, photo_count + 1),
        key=lambda candidate: (
            abs(math.log((candidate / math.ceil(photo_count / candidate)) / aspect_ratio))
            + (candidate * math.ceil(photo_count / candidate) - photo_count) / photo_count,
            candidate,
        ),
    )
    rows = math.ceil(photo_count / columns)
    cell_width = (width - margin * 2) / columns
    cell_height = (height - margin * 2) / rows
    slots = list(range(columns * rows))
    random.shuffle(slots)

    for photo_path, slot in zip(selected_paths, slots):
        column = slot % columns
        row = slot // columns
        card = make_polaroid(
            photo_path,
            width,
            max_width=cell_width * 0.80,
            max_height=cell_height * 0.80,
        )
        center_x = margin + (column + 0.5) * cell_width
        center_y = margin + (row + 0.5) * cell_height
        jitter_x = random.uniform(-cell_width * 0.025, cell_width * 0.025)
        jitter_y = random.uniform(-cell_height * 0.025, cell_height * 0.025)
        x = int(center_x + jitter_x - card.width / 2)
        y = int(center_y + jitter_y - card.height / 2)
        x = max(margin, min(x, width - card.width - margin))
        y = max(margin, min(y, height - card.height - margin))
        board.alpha_composite(card, (x, y))

    return board.convert("RGB")


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    root = ctk.CTk()
    WallpaperMaker(root)
    root.mainloop()
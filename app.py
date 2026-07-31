import math
import random
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image, ImageDraw, ImageFilter, ImageOps
from pillow_heif import register_heif_opener
from tkinterdnd2 import DND_FILES, TkinterDnD


register_heif_opener()


RESOLUTIONS = {
    "1920 x 1080": (1920, 1080),
    "2560 x 1440": (2560, 1440),
    "3840 x 2160": (3840, 2160),
}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".heic", ".heif"}

# スライダーの初期値（従来の見た目に近い既定）
DEFAULT_PHOTO_COUNT = 12
DEFAULT_ROTATION = 15
DEFAULT_MARGIN = 50
DEFAULT_CARD_SIZE = 80
DEFAULT_JITTER = 25
LAYOUTS = ("グリッド", "タイムライン", "放射状", "主役＋周囲")


class WallpaperMaker:
    def __init__(self, root):
        self.root = root
        self.root.title("Corkboard Wallpaper Maker")
        self.root.geometry("1280x820")
        self.root.minsize(1040, 700)

        self.folder = None
        self.corkboard_path = None
        self.preview_image = None
        self.last_image = None

        self.photo_count_var = tk.IntVar(value=DEFAULT_PHOTO_COUNT)
        self.rotation_var = tk.IntVar(value=DEFAULT_ROTATION)
        self.margin_var = tk.IntVar(value=DEFAULT_MARGIN)
        self.card_size_var = tk.IntVar(value=DEFAULT_CARD_SIZE)
        self.jitter_var = tk.IntVar(value=DEFAULT_JITTER)
        self.layout_var = tk.StringVar(value=LAYOUTS[0])

        self._build_ui()
        self._register_drop_target()

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
        self.drop_hint = ctk.CTkLabel(
            header,
            text="フォルダまたは背景画像をここへドロップ",
            text_color="#d8895b",
            font=ctk.CTkFont(size=12),
        )
        self.drop_hint.grid(row=4, column=0, sticky="w", pady=(8, 0))

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

        body = ctk.CTkFrame(self.root, fg_color="transparent")
        body.grid(row=1, column=0, sticky="nsew", padx=28, pady=(0, 16))
        body.grid_columnconfigure(0, weight=1)
        body.grid_columnconfigure(1, weight=0)
        body.grid_rowconfigure(0, weight=1)

        preview_frame = ctk.CTkFrame(body, corner_radius=14, fg_color="#24252a")
        preview_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
        preview_frame.grid_columnconfigure(0, weight=1)
        preview_frame.grid_rowconfigure(0, weight=1)
        self.preview = ctk.CTkLabel(
            preview_frame,
            text="写真フォルダを選択して生成してください",
            text_color="#777b85",
            font=ctk.CTkFont(size=15),
        )
        self.preview.grid(row=0, column=0, sticky="nsew", padx=18, pady=18)

        settings = ctk.CTkFrame(body, corner_radius=14, fg_color="#24252a", width=300)
        settings.grid(row=0, column=1, sticky="ns")
        settings.grid_propagate(False)
        settings.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            settings,
            text="配置の調整",
            font=ctk.CTkFont(size=16, weight="bold"),
        ).grid(row=0, column=0, sticky="w", padx=18, pady=(18, 4))
        ctk.CTkLabel(
            settings,
            text="生成時に反映されます",
            text_color="#8d9099",
            font=ctk.CTkFont(size=12),
        ).grid(row=1, column=0, sticky="w", padx=18, pady=(0, 12))

        ctk.CTkLabel(settings, text="レイアウト", text_color="#d0d2d8").grid(
            row=2, column=0, sticky="w", padx=18
        )
        ctk.CTkComboBox(
            settings,
            variable=self.layout_var,
            values=LAYOUTS,
            state="readonly",
            width=264,
        ).grid(row=3, column=0, sticky="ew", padx=18, pady=(6, 14))

        self.photo_count_value = self._add_slider(
            settings,
            row=4,
            label="写真枚数",
            variable=self.photo_count_var,
            from_=4,
            to=20,
            number_of_steps=16,
            format_value=lambda v: f"{int(v)} 枚",
        )
        self.rotation_value = self._add_slider(
            settings,
            row=5,
            label="回転の最大角度",
            variable=self.rotation_var,
            from_=0,
            to=30,
            number_of_steps=30,
            format_value=lambda v: f"±{int(v)}°",
        )
        self.margin_value = self._add_slider(
            settings,
            row=6,
            label="余白",
            variable=self.margin_var,
            from_=10,
            to=120,
            number_of_steps=110,
            format_value=lambda v: f"{int(v)} px",
        )
        self.card_size_value = self._add_slider(
            settings,
            row=7,
            label="カードサイズ",
            variable=self.card_size_var,
            from_=50,
            to=95,
            number_of_steps=45,
            format_value=lambda v: f"{int(v)} %",
        )
        self.jitter_value = self._add_slider(
            settings,
            row=8,
            label="位置のゆらぎ",
            variable=self.jitter_var,
            from_=0,
            to=80,
            number_of_steps=80,
            format_value=lambda v: f"{int(v)} %",
        )

        ctk.CTkButton(
            settings,
            text="既定値に戻す",
            fg_color="#3f424a",
            hover_color="#555963",
            command=self.reset_sliders,
        ).grid(row=9, column=0, sticky="ew", padx=18, pady=(8, 18))

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
        self.drop_targets = (header, body, preview_frame, settings, footer)

    def _add_slider(self, parent, row, label, variable, from_, to, number_of_steps, format_value):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.grid(row=row, column=0, sticky="ew", padx=18, pady=(0, 14))
        frame.grid_columnconfigure(0, weight=1)

        title_row = ctk.CTkFrame(frame, fg_color="transparent")
        title_row.grid(row=0, column=0, sticky="ew")
        title_row.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(title_row, text=label, text_color="#d0d2d8").grid(
            row=0, column=0, sticky="w"
        )
        value_label = ctk.CTkLabel(
            title_row,
            text=format_value(variable.get()),
            text_color="#d8895b",
            font=ctk.CTkFont(weight="bold"),
        )
        value_label.grid(row=0, column=1, sticky="e")

        def on_change(value, label_widget=value_label, formatter=format_value):
            label_widget.configure(text=formatter(value))

        ctk.CTkSlider(
            frame,
            from_=from_,
            to=to,
            number_of_steps=number_of_steps,
            variable=variable,
            command=on_change,
            progress_color="#c76845",
            button_color="#d8895b",
            button_hover_color="#e49a6d",
        ).grid(row=1, column=0, sticky="ew", pady=(8, 0))
        return value_label

    def reset_sliders(self):
        self.photo_count_var.set(DEFAULT_PHOTO_COUNT)
        self.rotation_var.set(DEFAULT_ROTATION)
        self.margin_var.set(DEFAULT_MARGIN)
        self.card_size_var.set(DEFAULT_CARD_SIZE)
        self.jitter_var.set(DEFAULT_JITTER)
        self.layout_var.set(LAYOUTS[0])
        self.photo_count_value.configure(text=f"{DEFAULT_PHOTO_COUNT} 枚")
        self.rotation_value.configure(text=f"±{DEFAULT_ROTATION}°")
        self.margin_value.configure(text=f"{DEFAULT_MARGIN} px")
        self.card_size_value.configure(text=f"{DEFAULT_CARD_SIZE} %")
        self.jitter_value.configure(text=f"{DEFAULT_JITTER} %")
        self.status.configure(text="スライダーを既定値に戻しました")

    def _register_drop_target(self):
        TkinterDnD.require(self.root)
        for widget in self.drop_targets:
            widget.drop_target_register(DND_FILES)
            widget.dnd_bind("<<Drop>>", self._handle_drop)

    def _handle_drop(self, event):
        dropped_paths = [Path(path) for path in self.root.tk.splitlist(event.data)]
        folder = next((path for path in dropped_paths if path.is_dir()), None)
        if folder is not None:
            self._set_folder(folder)
            return

        image_path = next(
            (
                path
                for path in dropped_paths
                if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
            ),
            None,
        )
        if image_path is not None:
            self._set_corkboard(image_path)
            return

        self.status.configure(text="対応するフォルダまたは画像をドロップしてください")

    def _set_folder(self, folder):
        self.folder = folder
        count = sum(
            1
            for path in folder.iterdir()
            if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
        )
        self.folder_label.configure(text=f"選択中: {folder} ({count}枚)")
        self.status.configure(text="準備完了。壁紙を生成できます")

    def _set_corkboard(self, image_path):
        self.corkboard_path = image_path
        self.corkboard_label.configure(text=f"背景: {image_path.name}")
        self.status.configure(text="コルク背景を設定しました")

    def _current_settings(self):
        return {
            "photo_count": int(self.photo_count_var.get()),
            "max_rotation": float(self.rotation_var.get()),
            "margin": int(self.margin_var.get()),
            "card_size": int(self.card_size_var.get()) / 100.0,
            "jitter": int(self.jitter_var.get()) / 100.0,
            "layout": self.layout_var.get(),
        }

    def choose_folder(self):
        selected = filedialog.askdirectory(title="写真フォルダを選択")
        if selected:
            self._set_folder(Path(selected))

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
        settings = self._current_settings()
        self.generate_button.configure(state="disabled")
        self.shuffle_button.configure(state="disabled")
        self.save_button.configure(state="disabled")
        self.status.configure(text=f"写真を「{settings['layout']}」に配置しています...")
        threading.Thread(
            target=self._generate_in_background,
            args=(width, height, self.corkboard_path, settings),
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
            self._set_corkboard(Path(selected))

    def _generate_in_background(self, width, height, corkboard_path, settings):
        try:
            image = create_wallpaper(
                self.folder,
                width,
                height,
                corkboard_path,
                photo_count=settings["photo_count"],
                max_rotation=settings["max_rotation"],
                margin_px=settings["margin"],
                card_size_ratio=settings["card_size"],
                jitter_ratio=settings["jitter"],
                layout=settings["layout"],
            )
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
        self.shuffle_button.configure(state="normal")
        if self.last_image is not None:
            self.save_button.configure(state="normal")
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
                    (
                        max(1, int(texture.width * scale)),
                        max(1, int(texture.height * scale)),
                    ),
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


def add_board_lighting(board):
    """Apply a soft upper-left light and subtle edge falloff to the corkboard."""
    width, height = board.size
    overlay = Image.new("RGBA", board.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")

    light_radius = int(max(width, height) * 0.78)
    light_center = (int(width * 0.2), int(height * 0.12))
    draw.ellipse(
        (
            light_center[0] - light_radius,
            light_center[1] - light_radius,
            light_center[0] + light_radius,
            light_center[1] + light_radius,
        ),
        fill=(255, 220, 170, 42),
    )
    overlay = overlay.filter(ImageFilter.GaussianBlur(max(24, width // 13)))
    lit_board = Image.alpha_composite(board, overlay)

    vignette = Image.new("L", board.size, 0)
    vignette_draw = ImageDraw.Draw(vignette)
    inset = -int(max(width, height) * 0.16)
    vignette_draw.ellipse((inset, inset, width - inset, height - inset), fill=180)
    vignette = vignette.filter(ImageFilter.GaussianBlur(max(32, width // 10)))
    shadow = Image.new("RGBA", board.size, (37, 20, 12, 0))
    shadow.putalpha(ImageOps.invert(vignette).point(lambda value: value // 3))
    return Image.alpha_composite(lit_board, shadow)


def make_polaroid(
    photo_path,
    board_width,
    max_width=None,
    max_height=None,
    max_rotation=15.0,
):
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
        photo = ImageOps.fit(
            photo, (photo_width, photo_height), method=Image.Resampling.LANCZOS
        )

    card_height = photo_height + 76
    card = Image.new("RGBA", (card_width, card_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(card)
    draw.rectangle((4, 5, card_width - 2, card_height - 1), fill=(255, 255, 252, 255))
    draw.line((5, 5, card_width - 3, 5), fill=(255, 255, 255, 230), width=2)
    draw.line(
        (card_width - 3, 6, card_width - 3, card_height - 2),
        fill=(196, 191, 180, 115),
        width=2,
    )
    draw.line(
        (5, card_height - 2, card_width - 3, card_height - 2),
        fill=(196, 191, 180, 115),
        width=2,
    )
    card.paste(photo, (18, 19))

    # ピンは写真と一緒に回転するため、カード上に描画する。
    pin_x = card_width // 2
    pin_y = 13
    draw.ellipse((pin_x - 16, pin_y - 12, pin_x + 16, pin_y + 18), fill=(70, 34, 22, 120))
    pin_color = random.choice(
        ((207, 48, 44, 255), (236, 177, 35, 255), (43, 116, 172, 255))
    )
    draw.ellipse((pin_x - 13, pin_y - 13, pin_x + 13, pin_y + 13), fill=pin_color)
    draw.ellipse((pin_x - 7, pin_y - 8, pin_x + 1, pin_y), fill=(255, 255, 255, 130))
    draw.line((pin_x, pin_y + 12, pin_x, pin_y + 28), fill=(70, 70, 70, 220), width=3)

    angle = random.uniform(-max_rotation, max_rotation) if max_rotation > 0 else 0.0
    rotated = card.rotate(angle, resample=Image.Resampling.BICUBIC, expand=True)
    shadow = Image.new("RGBA", rotated.size, (0, 0, 0, 0))
    shadow.paste((22, 12, 8, 125), (11, 14), rotated.getchannel("A"))
    shadow = shadow.filter(ImageFilter.GaussianBlur(11))
    result = Image.new("RGBA", rotated.size, (0, 0, 0, 0))
    result.alpha_composite(shadow)
    result.alpha_composite(rotated)
    return result


def create_wallpaper(
    folder,
    width,
    height,
    texture_path=None,
    photo_count=DEFAULT_PHOTO_COUNT,
    max_rotation=DEFAULT_ROTATION,
    margin_px=DEFAULT_MARGIN,
    card_size_ratio=DEFAULT_CARD_SIZE / 100.0,
    jitter_ratio=DEFAULT_JITTER / 100.0,
    layout=LAYOUTS[0],
):
    paths = [
        path
        for path in folder.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_EXTENSIONS
    ]
    if not paths:
        raise ValueError("選択したフォルダに JPG / PNG / HEIC 画像がありません。")

    random.shuffle(paths)
    photo_count = max(1, min(int(photo_count), len(paths)))
    board = create_corkboard((width, height), texture_path).convert("RGBA")
    board = add_board_lighting(board)
    # 解像度に合わせて余白をスケール（基準: 1920px 幅）
    margin = max(8, int(margin_px * width / 1920))

    card_fill = max(0.45, min(0.98, float(card_size_ratio)))
    jitter = max(0.0, min(1.0, float(jitter_ratio)))
    max_rotation = max(0.0, float(max_rotation))
    selected_paths = paths[:photo_count]

    if layout == "タイムライン":
        positions = _timeline_positions(photo_count, width, height, margin)
    elif layout == "放射状":
        positions = _radial_positions(photo_count, width, height, margin)
    elif layout == "主役＋周囲":
        positions = _hero_positions(photo_count, width, height, margin)
    else:
        positions = _grid_positions(photo_count, width, height, margin)

    for photo_path, (center_x, center_y, max_width, max_height, is_hero) in zip(
        selected_paths, positions
    ):
        card = make_polaroid(
            photo_path,
            width,
            max_width=max_width * (1.0 if is_hero else card_fill),
            max_height=max_height * (1.0 if is_hero else card_fill),
            max_rotation=max_rotation,
        )
        jitter_scale = 0.1 if is_hero else 0.5
        jitter_x = random.uniform(
            -max_width * jitter_scale * jitter, max_width * jitter_scale * jitter
        )
        jitter_y = random.uniform(
            -max_height * jitter_scale * jitter, max_height * jitter_scale * jitter
        )
        x = int(center_x + jitter_x - card.width / 2)
        y = int(center_y + jitter_y - card.height / 2)
        x = max(margin, min(x, width - card.width - margin))
        y = max(margin, min(y, height - card.height - margin))
        board.alpha_composite(card, (x, y))

    return board.convert("RGB")


def _grid_positions(photo_count, width, height, margin):
    aspect_ratio = width / height
    columns = min(
        range(1, photo_count + 1),
        key=lambda candidate: (
            abs(math.log((candidate / math.ceil(photo_count / candidate)) / aspect_ratio))
            + (candidate * math.ceil(photo_count / candidate) - photo_count)
            / photo_count,
            candidate,
        ),
    )
    rows = math.ceil(photo_count / columns)
    cell_width = (width - margin * 2) / columns
    cell_height = (height - margin * 2) / rows
    slots = list(range(columns * rows))
    random.shuffle(slots)
    return [
        (
            margin + (slot % columns + 0.5) * cell_width,
            margin + (slot // columns + 0.5) * cell_height,
            cell_width,
            cell_height,
            False,
        )
        for slot in slots
    ]


def _timeline_positions(photo_count, width, height, margin):
    band_height = (height - margin * 2) * 0.56
    card_width = min((width - margin * 2) / max(2, photo_count * 0.7), height * 0.34)
    card_height = min(band_height, height * 0.48)
    return [
        (
            margin + (index + 0.5) * (width - margin * 2) / photo_count,
            height * 0.5 + (-1 if index % 2 else 1) * height * 0.11,
            card_width,
            card_height,
            False,
        )
        for index in range(photo_count)
    ]


def _radial_positions(photo_count, width, height, margin):
    center_x, center_y = width / 2, height / 2
    radius_x = max(width * 0.16, width / 2 - margin - width * 0.14)
    radius_y = max(height * 0.12, height / 2 - margin - height * 0.18)
    card_width = min(width * 0.22, (width - margin * 2) / max(3, photo_count / 1.6))
    card_height = min(height * 0.38, (height - margin * 2) / 2.2)
    return [
        (
            center_x + math.cos(-math.pi / 2 + math.tau * index / photo_count) * radius_x,
            center_y + math.sin(-math.pi / 2 + math.tau * index / photo_count) * radius_y,
            card_width,
            card_height,
            False,
        )
        for index in range(photo_count)
    ]


def _hero_positions(photo_count, width, height, margin):
    center_x, center_y = width / 2, height / 2
    positions = [(center_x, center_y, width * 0.52, height * 0.72, True)]
    if photo_count == 1:
        return positions

    surrounding_count = photo_count - 1
    radius_x = max(width * 0.2, width / 2 - margin - width * 0.1)
    radius_y = max(height * 0.16, height / 2 - margin - height * 0.12)
    card_width = min(width * 0.2, (width - margin * 2) / max(3, surrounding_count / 1.5))
    card_height = min(height * 0.3, (height - margin * 2) / 2.8)
    positions.extend(
        (
            center_x + math.cos(-math.pi / 2 + math.tau * index / surrounding_count) * radius_x,
            center_y + math.sin(-math.pi / 2 + math.tau * index / surrounding_count) * radius_y,
            card_width,
            card_height,
            False,
        )
        for index in range(surrounding_count)
    )
    return positions


if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    ctk.set_default_color_theme("dark-blue")
    root = ctk.CTk()
    WallpaperMaker(root)
    root.mainloop()

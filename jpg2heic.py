"""Bildkonverter: Beamer-sichere JPGs oder HEIC (Windows)."""
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

register_heif_opener()
EXT = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".bmp", ".tif", ".tiff"}
RES = {"1280 x 720 (HD)": (1280, 720), "1920 x 1080 (Full HD)": (1920, 1080),
       "3840 x 2160 (4K)": (3840, 2160), "Original (nicht verkleinern)": None}


def aufnahmedatum(f):
    try:
        with Image.open(f) as img:
            ex = img.getexif()
            return ex.get_ifd(0x8769).get(36867) or ex.get(306) or ""
    except Exception:
        return ""


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Bildkonverter")
        self.resizable(False, False)
        self.src, self.dst = tk.StringVar(), tk.StringVar()
        self.mode = tk.StringVar(value="beamer")
        self.res = tk.StringVar(value="1920 x 1080 (Full HD)")
        self.quality = tk.IntVar(value=90)
        self.recursive = tk.BooleanVar(value=False)
        self.rename = tk.BooleanVar(value=True)
        self.bydate = tk.BooleanVar(value=True)

        p = {"padx": 6, "pady": 4}
        ttk.Label(self, text="Quellordner:").grid(row=0, column=0, sticky="w", **p)
        ttk.Entry(self, textvariable=self.src, width=50).grid(row=0, column=1, **p)
        ttk.Button(self, text="...", width=4, command=lambda: self.pick(self.src)).grid(row=0, column=2, **p)
        ttk.Label(self, text="Zielordner:").grid(row=1, column=0, sticky="w", **p)
        ttk.Entry(self, textvariable=self.dst, width=50).grid(row=1, column=1, **p)
        ttk.Button(self, text="...", width=4, command=lambda: self.pick(self.dst)).grid(row=1, column=2, **p)
        ttk.Label(self, text="(leer = Unterordner \"Konvertiert\" im Quellordner)",
                  foreground="gray").grid(row=2, column=1, sticky="w", padx=6)

        m = ttk.LabelFrame(self, text="Modus")
        m.grid(row=3, column=0, columnspan=3, sticky="we", **p)
        ttk.Radiobutton(m, text="Beamer-JPG (Baseline, RGB, verkleinert)", value="beamer",
                        variable=self.mode, command=self.toggle).pack(anchor="w", padx=6)
        ttk.Radiobutton(m, text="HEIC", value="heic",
                        variable=self.mode, command=self.toggle).pack(anchor="w", padx=6)

        o = ttk.LabelFrame(self, text="Optionen")
        o.grid(row=4, column=0, columnspan=3, sticky="we", **p)
        ttk.Label(o, text="Auflösung:").grid(row=0, column=0, sticky="w", padx=6, pady=2)
        self.cb = ttk.Combobox(o, textvariable=self.res, values=list(RES), state="readonly", width=28)
        self.cb.grid(row=0, column=1, columnspan=2, sticky="w", pady=2)
        ttk.Label(o, text="Qualität:").grid(row=1, column=0, sticky="w", padx=6)
        ttk.Scale(o, from_=50, to=100, variable=self.quality, length=180,
                  command=lambda v: self.qlbl.config(text=str(int(float(v))))).grid(row=1, column=1, sticky="w")
        self.qlbl = ttk.Label(o, text="90", width=4)
        self.qlbl.grid(row=1, column=2, sticky="w")
        self.cr = ttk.Checkbutton(o, text="Umbenennen in 001, 002, ...", variable=self.rename)
        self.cr.grid(row=2, column=0, columnspan=3, sticky="w", padx=6)
        self.cd = ttk.Checkbutton(o, text="Nach Aufnahmedatum sortieren (sonst Dateiname)", variable=self.bydate)
        self.cd.grid(row=3, column=0, columnspan=3, sticky="w", padx=6)
        ttk.Checkbutton(o, text="Unterordner einbeziehen", variable=self.recursive).grid(
            row=4, column=0, columnspan=3, sticky="w", padx=6)

        self.bar = ttk.Progressbar(self, length=440)
        self.bar.grid(row=5, column=0, columnspan=3, **p)
        self.status = ttk.Label(self, text="Bereit")
        self.status.grid(row=6, column=0, columnspan=3, sticky="w", **p)
        self.btn = ttk.Button(self, text="Konvertieren", command=self.start)
        self.btn.grid(row=7, column=0, columnspan=3, pady=8)

    def toggle(self):
        s = "readonly" if self.mode.get() == "beamer" else "disabled"
        self.cb.config(state=s)
        for w in (self.cr, self.cd):
            w.config(state="normal" if s == "readonly" else "disabled")

    def pick(self, var):
        d = filedialog.askdirectory()
        if d:
            var.set(d)

    def start(self):
        src = Path(self.src.get())
        if not src.is_dir():
            messagebox.showerror("Fehler", "Bitte gültigen Quellordner wählen.")
            return
        dst = Path(self.dst.get()) if self.dst.get() else src / "Konvertiert"
        pattern = "**/*" if self.recursive.get() else "*"
        files = [f for f in src.glob(pattern)
                 if f.is_file() and f.suffix.lower() in EXT and dst not in f.parents]
        if not files:
            messagebox.showinfo("Hinweis", "Keine Bilder gefunden.")
            return
        self.btn.config(state="disabled")
        self.bar.config(maximum=len(files), value=0)
        threading.Thread(target=self.run, args=(src, dst, files), daemon=True).start()

    def run(self, src, dst, files):
        beamer = self.mode.get() == "beamer"
        q = int(self.quality.get())
        size = RES[self.res.get()]
        if beamer and self.bydate.get():
            self.after(0, self.status.config, {"text": "Sortiere nach Aufnahmedatum ..."})
            files.sort(key=lambda f: (aufnahmedatum(f) or "9999", f.name.lower()))
        else:
            files.sort(key=lambda f: str(f).lower())
        ok, err = 0, []
        for i, f in enumerate(files, 1):
            self.after(0, self.status.config, {"text": f"{i}/{len(files)}: {f.name}"})
            try:
                with Image.open(f) as img:
                    img = ImageOps.exif_transpose(img)
                    if beamer:
                        name = f"{i:03d}.jpg" if self.rename.get() else f.stem + ".jpg"
                        out = dst / name
                        img = img.convert("RGB")
                        if size:
                            img.thumbnail(size, Image.LANCZOS)
                        dst.mkdir(parents=True, exist_ok=True)
                        img.save(out, "JPEG", quality=q, progressive=False,
                                 optimize=False, subsampling=2)
                    else:
                        out_dir = dst / f.parent.relative_to(src)
                        out_dir.mkdir(parents=True, exist_ok=True)
                        exif = img.getexif()
                        exif[0x0112] = 1
                        img.save(out_dir / (f.stem + ".heic"), format="HEIF",
                                 quality=q, exif=exif.tobytes())
                ok += 1
            except Exception as e:
                err.append(f"{f.name}: {e}")
            self.after(0, self.bar.config, {"value": i})
        self.after(0, self.done, ok, err, dst)

    def done(self, ok, err, dst):
        self.btn.config(state="normal")
        self.status.config(text=f"Fertig: {ok} konvertiert, {len(err)} Fehler -> {dst}")
        if err:
            messagebox.showwarning("Fehler", "\n".join(err[:15]))


if __name__ == "__main__":
    App().mainloop()

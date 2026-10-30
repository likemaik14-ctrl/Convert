"""JPG -> HEIC Konverter mit Ordnerauswahl (Windows)."""
import threading
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from PIL import Image, ImageOps
from pillow_heif import register_heif_opener

register_heif_opener()
EXT = {".jpg", ".jpeg"}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("JPG -> HEIC Konverter")
        self.resizable(False, False)
        self.src = tk.StringVar()
        self.dst = tk.StringVar()
        self.quality = tk.IntVar(value=85)
        self.recursive = tk.BooleanVar(value=False)
        self.overwrite = tk.BooleanVar(value=False)

        p = {"padx": 6, "pady": 4}
        ttk.Label(self, text="Quellordner:").grid(row=0, column=0, sticky="w", **p)
        ttk.Entry(self, textvariable=self.src, width=50).grid(row=0, column=1, **p)
        ttk.Button(self, text="...", width=4, command=lambda: self.pick(self.src)).grid(row=0, column=2, **p)

        ttk.Label(self, text="Zielordner:").grid(row=1, column=0, sticky="w", **p)
        ttk.Entry(self, textvariable=self.dst, width=50).grid(row=1, column=1, **p)
        ttk.Button(self, text="...", width=4, command=lambda: self.pick(self.dst)).grid(row=1, column=2, **p)
        ttk.Label(self, text="(leer = gleicher Ordner wie Quelle)", foreground="gray").grid(row=2, column=1, sticky="w", padx=6)

        f = ttk.Frame(self)
        f.grid(row=3, column=0, columnspan=3, sticky="w", **p)
        ttk.Label(f, text="Qualität:").pack(side="left")
        ttk.Scale(f, from_=30, to=100, variable=self.quality, length=180,
                  command=lambda v: self.qlbl.config(text=str(int(float(v))))).pack(side="left", padx=4)
        self.qlbl = ttk.Label(f, text="85", width=4)
        self.qlbl.pack(side="left")
        ttk.Checkbutton(f, text="Unterordner", variable=self.recursive).pack(side="left", padx=10)
        ttk.Checkbutton(f, text="Überschreiben", variable=self.overwrite).pack(side="left")

        self.bar = ttk.Progressbar(self, length=420)
        self.bar.grid(row=4, column=0, columnspan=3, **p)
        self.status = ttk.Label(self, text="Bereit")
        self.status.grid(row=5, column=0, columnspan=3, sticky="w", **p)
        self.btn = ttk.Button(self, text="Konvertieren", command=self.start)
        self.btn.grid(row=6, column=0, columnspan=3, pady=8)

    def pick(self, var):
        d = filedialog.askdirectory()
        if d:
            var.set(d)

    def start(self):
        src = Path(self.src.get())
        if not src.is_dir():
            messagebox.showerror("Fehler", "Bitte gültigen Quellordner wählen.")
            return
        pattern = "**/*" if self.recursive.get() else "*"
        files = [f for f in src.glob(pattern) if f.is_file() and f.suffix.lower() in EXT]
        if not files:
            messagebox.showinfo("Hinweis", "Keine JPG-Dateien gefunden.")
            return
        self.btn.config(state="disabled")
        self.bar.config(maximum=len(files), value=0)
        threading.Thread(target=self.run, args=(src, files), daemon=True).start()

    def run(self, src, files):
        dst_root = Path(self.dst.get()) if self.dst.get() else None
        q = int(self.quality.get())
        ok, skip, err = 0, 0, []
        for i, f in enumerate(files, 1):
            out_dir = (dst_root / f.parent.relative_to(src)) if dst_root else f.parent
            out = out_dir / (f.stem + ".heic")
            self.after(0, self.status.config, {"text": f"{i}/{len(files)}: {f.name}"})
            try:
                if out.exists() and not self.overwrite.get():
                    skip += 1
                else:
                    out_dir.mkdir(parents=True, exist_ok=True)
                    with Image.open(f) as img:
                        img = ImageOps.exif_transpose(img)  # Drehung fest übernehmen
                        exif = img.getexif()
                        exif[0x0112] = 1                    # Orientierung zurücksetzen
                        img.save(out, format="HEIF", quality=q, exif=exif.tobytes())
                    ok += 1
            except Exception as e:
                err.append(f"{f.name}: {e}")
            self.after(0, self.bar.config, {"value": i})
        self.after(0, self.done, ok, skip, err)

    def done(self, ok, skip, err):
        self.btn.config(state="normal")
        self.status.config(text=f"Fertig: {ok} konvertiert, {skip} übersprungen, {len(err)} Fehler")
        if err:
            messagebox.showwarning("Fehler", "\n".join(err[:15]))


if __name__ == "__main__":
    App().mainloop()

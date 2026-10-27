import os, shutil, zipfile, json, time, tkinter as tk
from tkinter import filedialog, messagebox, ttk

CFG = os.path.join(os.path.expanduser("~"), ".bl2modinstaller.json")
EXT = {".ini": "WillowGame/Config", ".u": "WillowGame/CookedPCConsole",
       ".upk": "WillowGame/CookedPCConsole", ".bin": "WillowGame/CookedPCConsole",
       ".dll": "Binaries/Win32", ".exe": "Binaries/Win32"}
ROOTS = ("willowgame", "binaries", "engine")


def load():
    try:
        return json.load(open(CFG))
    except Exception:
        return {}


def save(d):
    json.dump(d, open(CFG, "w"))


def targets(game, src):
    """Yield (name_in_game_relative, bytes_reader) pairs."""
    ext = os.path.splitext(src)[1].lower()
    if ext == ".zip":
        z = zipfile.ZipFile(src)
        for m in z.infolist():
            if m.is_dir():
                continue
            parts = [p for p in m.filename.replace("\\", "/").split("/") if p not in ("", ".", "..")]
            low = [p.lower() for p in parts]
            idx = next((i for i, p in enumerate(low) if p in ROOTS), None)
            if idx is not None:
                rel = "/".join(parts[idx:])
            else:
                e = os.path.splitext(parts[-1])[1].lower()
                if e not in EXT:
                    continue
                rel = EXT[e] + "/" + parts[-1]
            yield rel, (lambda m=m: z.read(m))
    else:
        if ext not in EXT:
            raise ValueError("Неподдерживаемый тип: " + ext)
        rel = EXT[ext] + "/" + os.path.basename(src)
        yield rel, (lambda: open(src, "rb").read())


def install(game, src):
    bdir = os.path.join(game, "_mod_backup", time.strftime("%Y%m%d_%H%M%S"))
    log = []
    for rel, rd in targets(game, src):
        dst = os.path.join(game, *rel.split("/"))
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.exists(dst):
            b = os.path.join(bdir, *rel.split("/"))
            os.makedirs(os.path.dirname(b), exist_ok=True)
            shutil.copy2(dst, b)
        open(dst, "wb").write(rd())
        log.append(rel)
    return log


def restore(game):
    root = os.path.join(game, "_mod_backup")
    if not os.path.isdir(root) or not os.listdir(root):
        raise ValueError("Нет резервных копий")
    last = os.path.join(root, sorted(os.listdir(root))[-1])
    n = 0
    for dp, _, fs in os.walk(last):
        for f in fs:
            s = os.path.join(dp, f)
            d = os.path.join(game, os.path.relpath(s, last))
            os.makedirs(os.path.dirname(d), exist_ok=True)
            shutil.copy2(s, d)
            n += 1
    shutil.rmtree(last)
    return n


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Borderlands 2 Mod Installer")
        self.geometry("520x330")
        self.cfg = load()
        self.ver = tk.StringVar(value=self.cfg.get("ver", "Borderlands 2"))
        self.game = tk.StringVar(value=self.cfg.get(self.ver.get(), ""))
        self.mod = tk.StringVar()
        f = ttk.Frame(self, padding=10)
        f.pack(fill="both", expand=True)
        ttk.Label(f, text="Версия игры:").pack(anchor="w")
        cb = ttk.Combobox(f, textvariable=self.ver, state="readonly",
                          values=["Borderlands 2", "Borderlands 2 Remastered"])
        cb.pack(fill="x")
        cb.bind("<<ComboboxSelected>>", self.chg)
        ttk.Label(f, text="Папка игры (где Binaries и WillowGame):").pack(anchor="w", pady=(8, 0))
        r = ttk.Frame(f); r.pack(fill="x")
        ttk.Entry(r, textvariable=self.game).pack(side="left", fill="x", expand=True)
        ttk.Button(r, text="Обзор", command=self.pg).pack(side="left")
        ttk.Label(f, text="Мод (.ini / .u / .upk / .zip):").pack(anchor="w", pady=(8, 0))
        r = ttk.Frame(f); r.pack(fill="x")
        ttk.Entry(r, textvariable=self.mod).pack(side="left", fill="x", expand=True)
        ttk.Button(r, text="Обзор", command=self.pm).pack(side="left")
        r = ttk.Frame(f); r.pack(fill="x", pady=10)
        ttk.Button(r, text="Установить мод", command=self.inst).pack(side="left", expand=True, fill="x")
        ttk.Button(r, text="Откатить последний", command=self.rest).pack(side="left", expand=True, fill="x")
        self.out = tk.Text(f, height=8, state="disabled")
        self.out.pack(fill="both", expand=True)

    def say(self, t):
        self.out.config(state="normal"); self.out.insert("end", t + "\n")
        self.out.config(state="disabled"); self.out.see("end")

    def chg(self, _=None):
        self.cfg["ver"] = self.ver.get(); save(self.cfg)
        self.game.set(self.cfg.get(self.ver.get(), ""))

    def pg(self):
        d = filedialog.askdirectory()
        if d:
            self.game.set(d)

    def pm(self):
        p = filedialog.askopenfilename(filetypes=[("Моды", "*.ini *.u *.upk *.bin *.zip *.dll"), ("Все", "*.*")])
        if p:
            self.mod.set(p)

    def check(self):
        g = self.game.get()
        if not (os.path.isdir(os.path.join(g, "WillowGame")) or os.path.isdir(os.path.join(g, "Binaries"))):
            messagebox.showerror("Ошибка", "Это не папка Borderlands 2")
            return None
        self.cfg[self.ver.get()] = g; save(self.cfg)
        return g

    def inst(self):
        g = self.check()
        if not g or not os.path.isfile(self.mod.get()):
            return
        try:
            for x in install(g, self.mod.get()):
                self.say("OK " + x)
            self.say("Готово. Копии заменённых файлов: _mod_backup")
        except Exception as e:
            messagebox.showerror("Ошибка", str(e))

    def rest(self):
        g = self.check()
        if g:
            try:
                self.say("Восстановлено файлов: %d" % restore(g))
            except Exception as e:
                messagebox.showerror("Ошибка", str(e))


if __name__ == "__main__":
    App().mainloop()

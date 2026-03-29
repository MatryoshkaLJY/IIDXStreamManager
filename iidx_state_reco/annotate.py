#!/usr/bin/env python3
"""
Image annotation tool for classification datasets.
Optimised for video-frame sequences (1fps extraction) where consecutive
frames share the same label.

Usage:
    python annotate.py [directory]

Dependencies:
    pip install pillow
"""

import os
import csv
import json
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from PIL import Image, ImageTk
import threading

# ── colours ────────────────────────────────────────────────────────────────
BG        = '#1e1e1e'
BG_ITEM   = '#2d2d2d'
BG_LABELED= '#1e3020'   # dark green tint — labeled but not selected
BG_SEL    = '#1a3a5c'   # blue tint — in selection
BG_CUR    = '#0d6efd'   # bright blue — current / anchor
FG        = '#e0e0e0'
FG_DIM    = '#888888'
FG_LABEL  = '#7ecf7e'
FG_ACC    = '#ffc857'   # accent (apply button)

THUMB_W, THUMB_H = 112, 72


class AnnotationTool:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Image Annotation Tool")
        self.root.geometry("1440x900")
        self.root.configure(bg=BG)

        # state
        self.images: list[str] = []
        self.annotations: dict[str, str] = {}
        self.current_dir = ''
        self.cur = 0               # current/anchor index
        self.sel: set[int] = set() # selected indices
        self.last_click = 0        # for shift-range
        self.labels: list[str] = []
        self.thumb_photos: list = []
        self.thumb_rows: list[dict] = []
        self._preview_photo = None

        self._build_ui()
        self._bind_keys()

    # ── UI construction ────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_menu()

        outer = tk.Frame(self.root, bg=BG)
        outer.pack(fill=tk.BOTH, expand=True)

        self._build_filmstrip(outer)
        self._build_right(outer)

        self.statusbar = tk.Label(
            self.root, text='Open a directory to begin (Ctrl+O)',
            bg='#111', fg=FG_DIM, anchor='w', padx=8, font=('Monospace', 9))
        self.statusbar.pack(side=tk.BOTTOM, fill=tk.X)

    def _build_menu(self):
        mb = tk.Menu(self.root)
        fm = tk.Menu(mb, tearoff=0)
        fm.add_command(label='Open Directory…   Ctrl+O', command=self.open_directory)
        fm.add_separator()
        fm.add_command(label='Load Annotations…',        command=self.load_annotations)
        fm.add_command(label='Save Annotations   Ctrl+S', command=self.save_annotations)
        fm.add_separator()
        fm.add_command(label='Quit', command=self.root.quit)
        mb.add_cascade(label='File', menu=fm)
        self.root.config(menu=mb)

    def _build_filmstrip(self, parent):
        left = tk.Frame(parent, bg=BG, width=260)
        left.pack(side=tk.LEFT, fill=tk.Y)
        left.pack_propagate(False)

        # header row
        hdr = tk.Frame(left, bg=BG)
        hdr.pack(fill=tk.X, padx=6, pady=(6, 2))
        tk.Label(hdr, text='Frames', bg=BG, fg=FG,
                 font=('Sans', 10, 'bold')).pack(side=tk.LEFT)
        self.progress_lbl = tk.Label(hdr, text='', bg=BG, fg=FG_DIM,
                                     font=('Monospace', 9))
        self.progress_lbl.pack(side=tk.RIGHT)

        # scrollable canvas
        wrap = tk.Frame(left, bg=BG)
        wrap.pack(fill=tk.BOTH, expand=True)

        self.tc = tk.Canvas(wrap, bg=BG, highlightthickness=0)
        vsb = tk.Scrollbar(wrap, orient=tk.VERTICAL, command=self.tc.yview)
        self.tc.configure(yscrollcommand=vsb.set)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.tc.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.tf = tk.Frame(self.tc, bg=BG)
        self._tf_win = self.tc.create_window((0, 0), window=self.tf, anchor='nw')
        self.tf.bind('<Configure>',
                     lambda e: self.tc.configure(scrollregion=self.tc.bbox('all')))
        self.tc.bind('<Configure>',
                     lambda e: self.tc.itemconfig(self._tf_win, width=e.width))
        for ev, fn in [('<Button-4>', lambda e: self.tc.yview_scroll(-3, 'units')),
                       ('<Button-5>', lambda e: self.tc.yview_scroll( 3, 'units')),
                       ('<MouseWheel>', self._wheel)]:
            self.tc.bind(ev, fn)

    def _build_right(self, parent):
        right = tk.Frame(parent, bg=BG)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # image preview — takes all available space
        self.preview = tk.Label(right, bg='#111', fg='#444',
                                text='No image', font=('Sans', 13))
        self.preview.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.preview.bind('<Configure>', self._on_preview_resize)

        # controls strip
        ctrl = tk.Frame(right, bg=BG)
        ctrl.pack(fill=tk.X, padx=10, pady=(0, 8))

        # label row
        r1 = tk.Frame(ctrl, bg=BG)
        r1.pack(fill=tk.X, pady=3)
        tk.Label(r1, text='Label:', bg=BG, fg=FG,
                 font=('Sans', 11)).pack(side=tk.LEFT, padx=(0, 6))
        self.label_var = tk.StringVar()
        self.label_entry = tk.Entry(
            r1, textvariable=self.label_var, font=('Sans', 13),
            bg='#3a3a3a', fg='white', insertbackground='white',
            relief=tk.FLAT, bd=5)
        self.label_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.label_entry.bind('<Return>', lambda e: self.apply_label())

        self.apply_btn = tk.Button(
            r1, text='Apply [Enter]', command=self.apply_label,
            bg='#0d6efd', fg='white', font=('Sans', 10, 'bold'),
            relief=tk.FLAT, padx=14, cursor='hand2')
        self.apply_btn.pack(side=tk.LEFT, padx=(8, 0))

        # quick labels row
        r2 = tk.Frame(ctrl, bg=BG)
        r2.pack(fill=tk.X, pady=2)
        tk.Label(r2, text='Quick [1–9]:', bg=BG, fg=FG_DIM,
                 font=('Sans', 9)).pack(side=tk.LEFT, padx=(0, 4))
        self.qf = tk.Frame(r2, bg=BG)
        self.qf.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self._new_ql_var = tk.StringVar()
        ql_entry = tk.Entry(r2, textvariable=self._new_ql_var, width=14,
                            bg='#3a3a3a', fg='white', insertbackground='white',
                            relief=tk.FLAT, bd=4)
        ql_entry.pack(side=tk.RIGHT, padx=(4, 0))
        ql_entry.bind('<Return>', self._add_quick_label)
        tk.Label(r2, text='+ add:', bg=BG, fg=FG_DIM,
                 font=('Sans', 9)).pack(side=tk.RIGHT, padx=(4, 0))

        # selection info / hints
        r3 = tk.Frame(ctrl, bg=BG)
        r3.pack(fill=tk.X, pady=2)
        self.sel_lbl = tk.Label(
            r3,
            text='Click=select  Shift+Click=extend range  Ctrl+Click=toggle  ← →=navigate',
            bg=BG, fg=FG_DIM, font=('Monospace', 8), anchor='w')
        self.sel_lbl.pack(fill=tk.X)

    # ── directory loading ──────────────────────────────────────────────────

    def open_directory(self, path: str = ''):
        if not path:
            path = filedialog.askdirectory(title='Select frame directory')
        if not path:
            return
        self.current_dir = path
        exts = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp'}
        self.images = sorted(
            f for f in os.listdir(path)
            if os.path.splitext(f)[1].lower() in exts
        )
        self.annotations = {f: '' for f in self.images}
        self.thumb_photos = [None] * len(self.images)
        self.cur = 0
        self.sel = {0} if self.images else set()
        self.last_click = 0
        self._build_rows()
        if self.images:
            self._show(0)
        self._refresh_progress()
        self._set_status(f'Loaded {len(self.images)} images  —  {path}')

    def _build_rows(self):
        for w in self.tf.winfo_children():
            w.destroy()
        self.thumb_rows = []

        for i, fname in enumerate(self.images):
            row = tk.Frame(self.tf, bg=BG_ITEM, pady=2, cursor='hand2')
            row.pack(fill=tk.X, padx=2, pady=1)

            img_lbl = tk.Label(row, bg=BG_ITEM,
                               width=THUMB_W, height=THUMB_H)
            img_lbl.pack(side=tk.LEFT, padx=4, pady=3)

            info = tk.Frame(row, bg=BG_ITEM)
            info.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 4))

            idx_lbl = tk.Label(info, text=f'#{i+1}', bg=BG_ITEM,
                               fg=FG_DIM, font=('Monospace', 8), anchor='w')
            idx_lbl.pack(anchor='w')

            name = fname if len(fname) <= 26 else fname[:24] + '…'
            nm_lbl = tk.Label(info, text=name, bg=BG_ITEM,
                              fg=FG, font=('Monospace', 8), anchor='w')
            nm_lbl.pack(anchor='w', fill=tk.X)

            ann_lbl = tk.Label(info, text='', bg=BG_ITEM,
                               fg=FG_LABEL, font=('Sans', 9, 'italic'),
                               anchor='w')
            ann_lbl.pack(anchor='w', fill=tk.X)

            all_w = [row, img_lbl, info, idx_lbl, nm_lbl, ann_lbl]
            self.thumb_rows.append({
                'row': row, 'img_lbl': img_lbl,
                'ann_lbl': ann_lbl, 'all': all_w,
            })

            for w in all_w:
                w.bind('<Button-1>',
                       lambda e, n=i: self._click(n, shift=False, ctrl=False))
                w.bind('<Shift-Button-1>',
                       lambda e, n=i: self._click(n, shift=True,  ctrl=False))
                w.bind('<Control-Button-1>',
                       lambda e, n=i: self._click(n, shift=False, ctrl=True))
                w.bind('<Button-4>',
                       lambda e: self.tc.yview_scroll(-3, 'units'))
                w.bind('<Button-5>',
                       lambda e: self.tc.yview_scroll( 3, 'units'))
                w.bind('<MouseWheel>', self._wheel)

        threading.Thread(target=self._load_thumbs, daemon=True).start()

    def _load_thumbs(self):
        for i, fname in enumerate(self.images):
            try:
                path = os.path.join(self.current_dir, fname)
                img = Image.open(path)
                img.thumbnail((THUMB_W, THUMB_H), Image.LANCZOS)
                pad = Image.new('RGB', (THUMB_W, THUMB_H), (40, 40, 40))
                pad.paste(img, ((THUMB_W - img.width) // 2,
                                (THUMB_H - img.height) // 2))
                ph = ImageTk.PhotoImage(pad)
                self.thumb_photos[i] = ph
                self.root.after(0, lambda i=i, p=ph: self._set_thumb(i, p))
            except Exception:
                pass

    def _set_thumb(self, i, photo):
        if i < len(self.thumb_rows):
            self.thumb_rows[i]['img_lbl'].configure(image=photo)

    # ── selection & navigation ─────────────────────────────────────────────

    def _click(self, idx: int, shift: bool, ctrl: bool):
        if shift:
            lo, hi = min(self.last_click, idx), max(self.last_click, idx)
            self.sel = set(range(lo, hi + 1))
        elif ctrl:
            self.sel ^= {idx}
            self.last_click = idx
        else:
            self.sel = {idx}
            self.last_click = idx
        self.cur = idx
        self._show(idx)
        self._paint()
        self._update_sel_lbl()
        self.root.focus_set()

    def _navigate(self, delta: int):
        if not self.images:
            return
        new = max(0, min(len(self.images) - 1, self.cur + delta))
        self.sel = {new}
        self.last_click = new
        self.cur = new
        self._show(new)
        self._paint()
        self._update_sel_lbl()

    def _paint(self):
        for i, r in enumerate(self.thumb_rows):
            if i == self.cur:
                bg = BG_CUR
            elif i in self.sel:
                bg = BG_SEL
            elif self.annotations.get(self.images[i]):
                bg = BG_LABELED
            else:
                bg = BG_ITEM
            for w in r['all']:
                try:
                    w.configure(bg=bg)
                except tk.TclError:
                    pass

    def _update_sel_lbl(self):
        n = len(self.sel)
        if n == 0:
            self.sel_lbl.config(text='No selection')
        elif n == 1:
            fname = self.images[self.cur]
            ann = self.annotations.get(fname, '')
            self.sel_lbl.config(text=f'{fname}  |  label: {ann or "(none)"}')
        else:
            lo, hi = min(self.sel), max(self.sel)
            self.sel_lbl.config(
                text=f'{n} frames selected  (#{lo+1} – #{hi+1})')

    # ── preview ────────────────────────────────────────────────────────────

    def _show(self, idx: int):
        if not self.images or idx >= len(self.images):
            return
        fname = self.images[idx]
        path = os.path.join(self.current_dir, fname)
        try:
            img = Image.open(path)
            pw = max(self.preview.winfo_width(),  400)
            ph = max(self.preview.winfo_height(), 300)
            img.thumbnail((pw, ph), Image.LANCZOS)
            ph_obj = ImageTk.PhotoImage(img)
            self.preview.configure(image=ph_obj, text='')
            self._preview_photo = ph_obj
        except Exception as ex:
            self.preview.configure(image='', text=f'Error:\n{ex}')

        ann = self.annotations.get(fname, '')
        self.label_var.set(ann)
        self._set_status(
            f'[{idx+1}/{len(self.images)}]  {fname}  '
            f'|  label: {ann or "(none)"}')
        self._scroll_to(idx)

    def _on_preview_resize(self, _event):
        # Re-render current image at new size
        self.root.after(50, lambda: self._show(self.cur))

    def _scroll_to(self, idx: int):
        if not self.thumb_rows or idx >= len(self.thumb_rows):
            return
        self.root.update_idletasks()
        iy = self.thumb_rows[idx]['row'].winfo_y()
        ih = self.thumb_rows[idx]['row'].winfo_height()
        ch = self.tc.winfo_height()
        fh = self.tf.winfo_height()
        if fh <= ch:
            return
        frac = max(0.0, min(1.0, (iy + ih / 2 - ch / 2) / (fh - ch)))
        self.tc.yview_moveto(frac)

    # ── labeling ───────────────────────────────────────────────────────────

    def apply_label(self):
        label = self.label_var.get().strip()
        if not self.images:
            return
        targets = self.sel if self.sel else {self.cur}
        for idx in targets:
            self.annotations[self.images[idx]] = label
            if idx < len(self.thumb_rows):
                self.thumb_rows[idx]['ann_lbl'].configure(text=label)
        self._paint()
        self._refresh_progress()
        # auto-advance past selection
        last = max(targets)
        nxt = last + 1
        if nxt < len(self.images):
            self.sel = {nxt}
            self.last_click = nxt
            self.cur = nxt
            self._show(nxt)
            self._paint()
            self._update_sel_lbl()
        self._set_status(
            f"Labeled {len(targets)} frame(s) as '{label}'  "
            f"— {self._labeled_count()}/{len(self.images)} done")

    # ── quick labels ───────────────────────────────────────────────────────

    def _add_quick_label(self, _event=None):
        label = self._new_ql_var.get().strip()
        if label and label not in self.labels:
            self.labels.append(label)
            self._rebuild_quick_btns()
            self._new_ql_var.set('')

    def _rebuild_quick_btns(self):
        for w in self.qf.winfo_children():
            w.destroy()
        for i, label in enumerate(self.labels[:9]):
            b = tk.Button(
                self.qf, text=f'[{i+1}] {label}',
                command=lambda l=label: self._quick_apply(l),
                bg='#3a3a3a', fg=FG, font=('Sans', 9),
                relief=tk.FLAT, padx=8, pady=2, cursor='hand2')
            b.pack(side=tk.LEFT, padx=2)

    def _quick_apply(self, label: str):
        self.label_var.set(label)
        self.apply_label()

    def _apply_quick_idx(self, n: int):
        if n < len(self.labels):
            self._quick_apply(self.labels[n])

    # ── save / load ────────────────────────────────────────────────────────

    def save_annotations(self):
        if not self.current_dir:
            messagebox.showwarning('Nothing to save', 'Open a directory first.')
            return
        out = os.path.join(self.current_dir, 'annotations.csv')
        with open(out, 'w', newline='', encoding='utf-8') as f:
            w = csv.writer(f)
            w.writerow(['filename', 'label'])
            for fname in self.images:
                w.writerow([fname, self.annotations.get(fname, '')])
        self._set_status(f'Saved → {out}')

    def load_annotations(self):
        path = filedialog.askopenfilename(
            title='Load annotations',
            filetypes=[('CSV', '*.csv'), ('JSON', '*.json'), ('All', '*.*')])
        if not path:
            return
        try:
            if path.endswith('.json'):
                with open(path, encoding='utf-8') as f:
                    data: dict = json.load(f)
            else:
                data = {}
                with open(path, encoding='utf-8') as f:
                    for row in csv.DictReader(f):
                        data[row['filename']] = row.get('label', '')
            self.annotations.update(data)
            for i, fname in enumerate(self.images):
                ann = self.annotations.get(fname, '')
                if i < len(self.thumb_rows):
                    self.thumb_rows[i]['ann_lbl'].configure(text=ann)
            self._paint()
            self._refresh_progress()
            self._set_status(f'Loaded annotations from {path}')
        except Exception as ex:
            messagebox.showerror('Load error', str(ex))

    # ── helpers ────────────────────────────────────────────────────────────

    def _bind_keys(self):
        r = self.root
        r.bind('<Control-o>', lambda e: self.open_directory())
        r.bind('<Control-s>', lambda e: self.save_annotations())
        r.bind('<Return>',    lambda e: self.apply_label())
        r.bind('<Right>',     lambda e: self._navigate(1))
        r.bind('<Left>',      lambda e: self._navigate(-1))
        r.bind('<Down>',      lambda e: self._navigate(1))
        r.bind('<Up>',        lambda e: self._navigate(-1))
        for i in range(1, 10):
            r.bind(str(i), lambda e, n=i-1: self._apply_quick_idx(n))

    def _wheel(self, event):
        self.tc.yview_scroll(-1 * (event.delta // 120), 'units')

    def _labeled_count(self) -> int:
        return sum(1 for v in self.annotations.values() if v)

    def _refresh_progress(self):
        labeled = self._labeled_count()
        total = len(self.images)
        pct = int(labeled / total * 100) if total else 0
        self.progress_lbl.config(text=f'{labeled}/{total}  ({pct}%)')

    def _set_status(self, msg: str):
        self.statusbar.config(text=msg)


def main():
    root = tk.Tk()
    app = AnnotationTool(root)
    if len(sys.argv) > 1 and os.path.isdir(sys.argv[1]):
        app.open_directory(sys.argv[1])
    root.mainloop()


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
服薬ラベル発行ツール (Python版)
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, timedelta
import calendar
import json
import os
import webbrowser
import tempfile

from reportlab.lib.pagesizes import mm
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.colors import black, white, red, blue

# ============================================================
# 設定
# ============================================================
DATA_FILE = os.path.join(os.path.expanduser("~"), ".medication_labels.json")
LABEL_WIDTH = 29 * mm
LABEL_HEIGHT = 52 * mm

WEEKDAYS = ["月", "火", "水", "木", "金", "土", "日"]

# ひらがな変換マップ
HIRAGANA_MAP = {
    "朝食後": "あさ", "昼食後": "ひる", "夕食後": "ゆう",
    "朝食前": "あさ前", "昼食前": "ひる前", "夕食前": "ゆう前",
    "就寝前": "ねるまえ", "起床時": "おきぬけ",
}

# ============================================================
# フォント設定
# ============================================================
def setup_fonts():
    font_paths = [
        "/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc",
        "/usr/share/fonts/truetype/fonts-japanese-gothic.ttf",
        "/usr/share/fonts/truetype/takao-gothic/TakaoPGothic.ttf",
        "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
        "C:/Windows/Fonts/msgothic.ttc",
        "C:/Windows/Fonts/meiryo.ttc",
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                pdfmetrics.registerFont(TTFont("JapaneseFont", path))
                return "JapaneseFont"
            except:
                continue
    return "Helvetica"

FONT_NAME = setup_fonts()

# ============================================================
# データ管理
# ============================================================
def load_patients():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    return []

def save_patients(patients):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(patients, f, ensure_ascii=False, indent=2)

# ============================================================
# PDF生成
# ============================================================
def draw_label(c, facility, name, date, timing, use_hiragana=False, show_date=True, show_facility=True, name_reading=""):
    w, h = LABEL_WIDTH, LABEL_HEIGHT
    cx = w / 2

    c.setFillColor(white)
    c.rect(0, 0, w, h, fill=True, stroke=False)
    c.setFillColor(black)

    # 施設名（show_facilityがTrueかつ施設名がある場合のみ表示）
    y_cursor = h
    if show_facility and facility:
        c.setFont(FONT_NAME, 8)
        y_cursor -= 4 * mm
        c.drawCentredString(cx, y_cursor, facility)

    name_display = f"{name} 様"
    name_font = 13 if len(name) <= 6 else 11
    c.setFont(FONT_NAME, name_font)
    y_cursor -= 6 * mm
    c.drawCentredString(cx, y_cursor, name_display)

    # 区切り線
    line_y = y_cursor - 1 * mm if not show_date else y_cursor - 2 * mm
    c.setStrokeColor(black)
    c.setLineWidth(0.5)
    c.line(2 * mm, line_y, w - 2 * mm, line_y)

    # 日付表示
    if show_date:
        date_str = f"{date.month}/{date.day}"
        weekday_idx = date.weekday()
        weekday_str = f"({WEEKDAYS[weekday_idx]})"

        if weekday_idx == 6:
            c.setFillColor(red)
        elif weekday_idx == 5:
            c.setFillColor(blue)
        else:
            c.setFillColor(black)

        c.setFont(FONT_NAME, 23)
        c.drawCentredString(cx, line_y - 11 * mm, date_str)
        c.setFont(FONT_NAME, 13)
        c.drawCentredString(cx, line_y - 19 * mm, weekday_str)

        # 用法エリア（日付あり）
        box_bottom = 1.5 * mm
        box_top = line_y - 24 * mm
    else:
        # 用法エリア（日付なし - 区切り線直下から詰めて使う）
        box_bottom = 1.5 * mm
        box_top = line_y

    box_height = box_top - box_bottom
    box_center_y = box_bottom + box_height / 2

    c.setFillColor(black)

    # 用法テキスト（ひらがなモードの場合は変換）
    if use_hiragana:
        display_text = HIRAGANA_MAP.get(timing, timing)
    else:
        display_text = timing

    # 文字数に応じてフォントサイズ調整（大きめ +2）
    text_len = len(display_text)
    if text_len <= 3:
        font_size = 26
    elif text_len <= 5:
        font_size = 20
    elif text_len <= 7:
        font_size = 16
    else:
        font_size = 14

    c.setFont(FONT_NAME, font_size)
    c.drawCentredString(cx, box_center_y, display_text)

    # 用法テキストの下にアンダーライン (10pt下)
    text_width = c.stringWidth(display_text, FONT_NAME, font_size)
    underline_y = box_center_y - 10
    c.setStrokeColor(black)
    c.setLineWidth(0.5)
    c.line(cx - text_width / 2, underline_y, cx + text_width / 2, underline_y)

def generate_pdf(facility, name, start_date, days, timings, sort_by_date=False, use_hiragana=False, show_date=True, show_facility=True, name_reading=""):
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    temp_path = temp_file.name
    temp_file.close()

    c = canvas.Canvas(temp_path, pagesize=(LABEL_WIDTH, LABEL_HEIGHT))
    first_page = True

    if sort_by_date:
        for day_offset in range(days):
            current_date = start_date + timedelta(days=day_offset)
            for timing in timings:
                if not first_page:
                    c.showPage()
                first_page = False
                draw_label(c, facility, name, current_date, timing, use_hiragana, show_date, show_facility, name_reading)
    else:
        for timing in timings:
            for day_offset in range(days):
                current_date = start_date + timedelta(days=day_offset)
                if not first_page:
                    c.showPage()
                first_page = False
                draw_label(c, facility, name, current_date, timing, use_hiragana, show_date, show_facility, name_reading)

    c.save()
    return temp_path

# ============================================================
# カレンダーポップアップ
# ============================================================
class CalendarPopup(tk.Toplevel):
    def __init__(self, parent, callback, initial_date=None):
        super().__init__(parent)
        self.callback = callback
        self.current_date = initial_date or datetime.now()
        self.current_year = self.current_date.year
        self.current_month = self.current_date.month
        
        self.title("日付選択")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        x = parent.winfo_rootx() + 100
        y = parent.winfo_rooty() + 100
        self.geometry(f"+{x}+{y}")
        
        self.create_widgets()
        self.update_calendar()
    
    def create_widgets(self):
        # クイック選択
        quick_frame = ttk.Frame(self, padding=10)
        quick_frame.pack(fill=tk.X)
        
        for text, days in [("今日", 0), ("明日", 1), ("+3日", 3), ("+7日", 7), ("+14日", 14)]:
            ttk.Button(quick_frame, text=text, width=6,
                      command=lambda d=days: self.quick_select(d)).pack(side=tk.LEFT, padx=2)
        
        # 月ナビ
        nav_frame = ttk.Frame(self, padding=5)
        nav_frame.pack(fill=tk.X)
        
        ttk.Button(nav_frame, text="◀◀", width=4, command=self.prev_year).pack(side=tk.LEFT)
        ttk.Button(nav_frame, text="◀", width=4, command=self.prev_month).pack(side=tk.LEFT)
        self.month_label = ttk.Label(nav_frame, text="", font=("", 14, "bold"))
        self.month_label.pack(side=tk.LEFT, expand=True)
        ttk.Button(nav_frame, text="▶", width=4, command=self.next_month).pack(side=tk.RIGHT)
        ttk.Button(nav_frame, text="▶▶", width=4, command=self.next_year).pack(side=tk.RIGHT)
        
        # カレンダー
        self.cal_frame = ttk.Frame(self, padding=10)
        self.cal_frame.pack()
        
        for i, day in enumerate(["月", "火", "水", "木", "金", "土", "日"]):
            fg = "red" if i == 6 else ("blue" if i == 5 else "black")
            lbl = tk.Label(self.cal_frame, text=day, width=5, font=("", 12, "bold"), fg=fg)
            lbl.grid(row=0, column=i, pady=5)
    
    def update_calendar(self):
        for w in self.cal_frame.winfo_children():
            if int(w.grid_info().get("row", 0)) > 0:
                w.destroy()
        
        self.month_label.config(text=f"{self.current_year}年 {self.current_month}月")
        
        cal = calendar.Calendar(firstweekday=0)
        today = datetime.now().date()
        
        for row, week in enumerate(cal.monthdayscalendar(self.current_year, self.current_month), start=1):
            for col, day in enumerate(week):
                if day == 0:
                    ttk.Label(self.cal_frame, text="", width=5).grid(row=row, column=col)
                else:
                    date = datetime(self.current_year, self.current_month, day).date()
                    is_today = date == today
                    
                    btn = tk.Button(
                        self.cal_frame, text=str(day), width=5, height=2,
                        bg="#2563eb" if is_today else "white",
                        fg="white" if is_today else ("red" if col == 6 else ("blue" if col == 5 else "black")),
                        font=("", 11),
                        command=lambda d=day: self.select_date(d)
                    )
                    btn.grid(row=row, column=col, padx=1, pady=1)
    
    def prev_year(self):
        self.current_year -= 1
        self.update_calendar()
    
    def next_year(self):
        self.current_year += 1
        self.update_calendar()
    
    def prev_month(self):
        if self.current_month == 1:
            self.current_month = 12
            self.current_year -= 1
        else:
            self.current_month -= 1
        self.update_calendar()
    
    def next_month(self):
        if self.current_month == 12:
            self.current_month = 1
            self.current_year += 1
        else:
            self.current_month += 1
        self.update_calendar()
    
    def quick_select(self, days):
        self.callback(datetime.now() + timedelta(days=days))
        self.destroy()
    
    def select_date(self, day):
        self.callback(datetime(self.current_year, self.current_month, day))
        self.destroy()

# ============================================================
# メインアプリケーション
# ============================================================
class MedicationLabelApp:
    def __init__(self, root):
        self.root = root
        self.root.title("💊 服薬ラベル発行")

        # 高DPI対応 (Windows)
        try:
            from ctypes import windll
            windll.shcore.SetProcessDpiAwareness(1)
        except Exception:
            pass

        self.root.geometry("880x520")
        self.root.resizable(True, True)
        self.root.minsize(800, 480)

        self.patients = load_patients()
        self.timing_vars = {}
        self.selected_date = datetime.now()

        self.create_widgets()
        self.update_patient_list()
    
    def create_widgets(self):
        # タイトル
        ttk.Label(self.root, text="💊 服薬ラベル発行", font=("", 16, "bold")).pack(pady=(8, 5))

        # ===== 左右分割 =====
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10)

        # --- 左ペイン: 患者リスト＋基本情報 ---
        left_pane = ttk.Frame(main_frame)
        left_pane.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))

        # 患者リスト
        frame1 = ttk.LabelFrame(left_pane, text="📋 患者リスト", padding=8)
        frame1.pack(fill=tk.X, pady=(0, 5))

        row1 = ttk.Frame(frame1)
        row1.pack(fill=tk.X)

        self.patient_combo = ttk.Combobox(row1, state="readonly", width=20, font=("", 11))
        self.patient_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.patient_combo.bind("<<ComboboxSelected>>", self.on_patient_selected)

        ttk.Button(row1, text="💾 保存", command=self.save_patient).pack(side=tk.LEFT, padx=(8, 2))
        ttk.Button(row1, text="🗑️ 削除", command=self.delete_patient).pack(side=tk.LEFT, padx=2)

        # 基本情報
        frame2 = ttk.LabelFrame(left_pane, text="👤 基本情報", padding=8)
        frame2.pack(fill=tk.BOTH, expand=True, pady=(0, 5))

        row2 = ttk.Frame(frame2)
        row2.pack(fill=tk.X)
        ttk.Label(row2, text="施設名:", font=("", 11)).pack(side=tk.LEFT)
        self.facility_entry = ttk.Entry(row2, width=14, font=("", 11))
        self.facility_entry.pack(side=tk.LEFT, padx=(4, 15))
        ttk.Label(row2, text="氏名:", font=("", 11)).pack(side=tk.LEFT)
        self.name_entry = ttk.Entry(row2, width=14, font=("", 11))
        self.name_entry.pack(side=tk.LEFT, padx=4)

        row2b = ttk.Frame(frame2)
        row2b.pack(fill=tk.X, pady=(4, 0))
        ttk.Label(row2b, text="よみがな:", font=("", 11)).pack(side=tk.LEFT)
        self.reading_entry = ttk.Entry(row2b, width=14, font=("", 11))
        self.reading_entry.pack(side=tk.LEFT, padx=(4, 0))
        ttk.Label(row2b, text="例: やまだ たろう", foreground="gray").pack(side=tk.LEFT, padx=8)

        # コメント欄
        row2c = ttk.Frame(frame2)
        row2c.pack(fill=tk.BOTH, expand=True, pady=(4, 0))
        ttk.Label(row2c, text="コメント:", font=("", 11)).pack(side=tk.LEFT, anchor=tk.N)
        self.comment_text = tk.Text(row2c, width=25, height=3, font=("", 10), wrap=tk.WORD)
        self.comment_text.pack(side=tk.LEFT, padx=(4, 0), fill=tk.BOTH, expand=True)

        # データ管理
        data_frame = ttk.Frame(left_pane)
        data_frame.pack(fill=tk.X)
        ttk.Label(data_frame, text="データ管理:").pack(side=tk.LEFT)
        ttk.Button(data_frame, text="↓ エクスポート", command=self.export_json).pack(side=tk.LEFT, padx=5)
        ttk.Button(data_frame, text="↑ インポート", command=self.import_json).pack(side=tk.LEFT, padx=5)
        if FONT_NAME == "Helvetica":
            ttk.Label(data_frame, text="⚠️ 日本語フォント未検出", foreground="red").pack(side=tk.RIGHT)

        # --- 右ペイン: 印刷設定 ---
        right_pane = ttk.Frame(main_frame)
        right_pane.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(5, 0))

        frame3 = ttk.LabelFrame(right_pane, text="🖨️ 印刷設定", padding=8)
        frame3.pack(fill=tk.BOTH, expand=True)

        # 印刷順序 + 用法表示
        row3a = ttk.Frame(frame3)
        row3a.pack(fill=tk.X, pady=3)
        ttk.Label(row3a, text="印刷順序:", font=("", 11)).pack(side=tk.LEFT)
        self.sort_var = tk.StringVar(value="timing")
        ttk.Radiobutton(row3a, text="まとめ印刷", variable=self.sort_var, value="timing").pack(side=tk.LEFT, padx=8)
        ttk.Radiobutton(row3a, text="1日分セット", variable=self.sort_var, value="date").pack(side=tk.LEFT)

        row3b = ttk.Frame(frame3)
        row3b.pack(fill=tk.X, pady=3)
        ttk.Label(row3b, text="用法表示:", font=("", 11)).pack(side=tk.LEFT)
        self.hiragana_var = tk.StringVar(value="kanji")
        ttk.Radiobutton(row3b, text="漢字", variable=self.hiragana_var, value="kanji").pack(side=tk.LEFT, padx=8)
        ttk.Radiobutton(row3b, text="ひらがな", variable=self.hiragana_var, value="hiragana").pack(side=tk.LEFT)

        # 表示オプション
        row3b2 = ttk.Frame(frame3)
        row3b2.pack(fill=tk.X, pady=3)
        self.show_facility_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(row3b2, text="施設名を印刷", variable=self.show_facility_var).pack(side=tk.LEFT, padx=(0, 10))
        self.show_date_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(row3b2, text="日付を印刷", variable=self.show_date_var).pack(side=tk.LEFT)

        # 日付
        row3c = ttk.Frame(frame3)
        row3c.pack(fill=tk.X, pady=3)
        ttk.Label(row3c, text="開始日:", font=("", 11)).pack(side=tk.LEFT)
        self.date_btn = ttk.Button(row3c, text=self.format_date(self.selected_date), command=self.show_calendar)
        self.date_btn.pack(side=tk.LEFT, padx=8)
        ttk.Label(row3c, text="日数:", font=("", 11)).pack(side=tk.LEFT, padx=(15, 0))
        self.days_var = tk.StringVar(value="7")
        ttk.Spinbox(row3c, from_=1, to=365, width=5, textvariable=self.days_var, font=("", 11)).pack(side=tk.LEFT, padx=4)
        ttk.Label(row3c, text="日分", font=("", 11)).pack(side=tk.LEFT)

        # 服用時点
        ttk.Label(frame3, text="服用時点:", font=("", 11)).pack(anchor=tk.W, pady=(6, 3))

        timing_frame = ttk.Frame(frame3)
        timing_frame.pack(fill=tk.X)

        timings = [
            ("朝食前", False), ("昼食前", False), ("夕食前", False), ("就寝前", False),
            ("朝食後", True), ("昼食後", True), ("夕食後", True), ("起床時", False),
        ]

        for i, (timing, default) in enumerate(timings):
            var = tk.BooleanVar(value=default)
            self.timing_vars[timing] = var
            cb = ttk.Checkbutton(timing_frame, text=timing, variable=var)
            cb.grid(row=i // 4, column=i % 4, sticky=tk.W, padx=6, pady=2)

        # カスタム
        row3d = ttk.Frame(frame3)
        row3d.pack(fill=tk.X, pady=(6, 0))
        ttk.Label(row3d, text="カスタム:", font=("", 11)).pack(side=tk.LEFT)
        self.custom_entry = ttk.Entry(row3d, width=15, font=("", 11))
        self.custom_entry.pack(side=tk.LEFT, padx=8)
        ttk.Label(row3d, text="例: 疼痛時, 頓服", foreground="gray").pack(side=tk.LEFT)

        # ===== 印刷ボタン（下部） =====
        print_btn = tk.Button(
            self.root, text="🖨️  PDF生成・印刷プレビュー",
            font=("", 14, "bold"), bg="#2563eb", fg="white",
            activebackground="#1d4ed8", activeforeground="white",
            pady=8, command=self.generate_labels
        )
        print_btn.pack(fill=tk.X, padx=10, pady=(8, 10))
    
    def format_date(self, date):
        return f"{date.year}/{date.month:02d}/{date.day:02d} ({WEEKDAYS[date.weekday()]})"
    
    def show_calendar(self):
        CalendarPopup(self.root, self.on_date_selected, self.selected_date)
    
    def on_date_selected(self, date):
        self.selected_date = date
        self.date_btn.config(text=self.format_date(date))
    
    def update_patient_list(self):
        self.patients = load_patients()
        self.patients.sort(key=lambda p: p.get("nameReading", "") or p.get("name", ""))
        values = ["-- 新規入力 --"] + [
            f"{p['name']} ({p.get('facility', '')})" if p.get('facility') else p['name']
            for p in self.patients
        ]
        self.patient_combo["values"] = values
        self.patient_combo.set("-- 新規入力 --")
    
    def on_patient_selected(self, event=None):
        idx = self.patient_combo.current()
        if idx <= 0:
            return
        p = self.patients[idx - 1]
        
        self.name_entry.delete(0, tk.END)
        self.name_entry.insert(0, p.get("name", ""))
        self.reading_entry.delete(0, tk.END)
        self.reading_entry.insert(0, p.get("nameReading", ""))
        self.facility_entry.delete(0, tk.END)
        self.facility_entry.insert(0, p.get("facility", ""))
        self.custom_entry.delete(0, tk.END)
        self.custom_entry.insert(0, p.get("customTiming", ""))
        self.comment_text.delete("1.0", tk.END)
        self.comment_text.insert("1.0", p.get("comment", ""))

        for var in self.timing_vars.values():
            var.set(False)
        for t in p.get("timings", []):
            if t in self.timing_vars:
                self.timing_vars[t].set(True)
    
    def save_patient(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("警告", "氏名を入力してください")
            return
        
        record = {
            "name": name,
            "nameReading": self.reading_entry.get().strip(),
            "facility": self.facility_entry.get().strip(),
            "timings": [t for t, v in self.timing_vars.items() if v.get()],
            "customTiming": self.custom_entry.get().strip(),
            "comment": self.comment_text.get("1.0", tk.END).strip()
        }
        
        idx = next((i for i, p in enumerate(self.patients) if p["name"] == name), None)
        if idx is not None:
            self.patients[idx] = record
            messagebox.showinfo("更新", f"「{name}」様を更新しました")
        else:
            self.patients.append(record)
            messagebox.showinfo("保存", f"「{name}」様を保存しました")
        
        save_patients(self.patients)
        self.update_patient_list()
    
    def delete_patient(self):
        idx = self.patient_combo.current()
        if idx <= 0:
            messagebox.showwarning("警告", "削除する患者を選択してください")
            return
        
        p = self.patients[idx - 1]
        if messagebox.askyesno("確認", f"「{p['name']}」様を削除しますか？"):
            del self.patients[idx - 1]
            save_patients(self.patients)
            self.update_patient_list()
            self.name_entry.delete(0, tk.END)
            self.reading_entry.delete(0, tk.END)
            self.facility_entry.delete(0, tk.END)
            self.custom_entry.delete(0, tk.END)
            self.comment_text.delete("1.0", tk.END)
            for v in self.timing_vars.values():
                v.set(False)
    
    def generate_labels(self):
        name = self.name_entry.get().strip()
        if not name:
            messagebox.showwarning("警告", "氏名を入力してください")
            return
        
        timings = [t for t, v in self.timing_vars.items() if v.get()]
        custom = self.custom_entry.get().strip()
        if custom:
            timings.extend([s.strip() for s in custom.replace("、", ",").split(",") if s.strip()])
        
        if not timings:
            messagebox.showwarning("警告", "服用時点を1つ以上選択してください")
            return
        
        pdf_path = generate_pdf(
            self.facility_entry.get().strip(),
            name,
            self.selected_date,
            int(self.days_var.get()),
            timings,
            self.sort_var.get() == "date",
            self.hiragana_var.get() == "hiragana",
            self.show_date_var.get(),
            self.show_facility_var.get(),
            self.reading_entry.get().strip()
        )
        webbrowser.open(f"file://{pdf_path}")
    
    def export_json(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json")],
            initialfile="medication_patients_backup.json"
        )
        if path:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.patients, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("完了", "エクスポートしました")
    
    def import_json(self):
        path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
        if path:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if not isinstance(data, list):
                    raise ValueError("ファイル形式が正しくありません")
                if messagebox.askyesno("確認", "現在のリストを上書きしますか？"):
                    self.patients = data
                    save_patients(self.patients)
                    self.update_patient_list()
                    messagebox.showinfo("完了", "読み込みました")
            except Exception as e:
                messagebox.showerror("エラー", str(e))

def main():
    root = tk.Tk()
    app = MedicationLabelApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()

import tkinter as tk
from tkinter import ttk


class StatsPanel(tk.Frame):
    def __init__(self, master, **kwargs):
        super().__init__(master, bg="#1E1E2E", **kwargs)
        self._build()

    def _build(self):
        title = tk.Label(self, text="📊 HIỆU SUẤT", bg="#1E1E2E", fg="#CDD6F4",
                         font=("Helvetica", 12, "bold"))
        title.pack(pady=(10, 6))

        current_frame = tk.LabelFrame(self, text=" Lần chạy hiện tại ",
                                      bg="#1E1E2E", fg="#89B4FA",
                                      font=("Helvetica", 9, "bold"),
                                      bd=1, relief="groove")
        current_frame.pack(fill="x", padx=8, pady=4)

        self.labels = {}
        fields = [
            ("algo",    "Thuật toán",     "—"),
            ("steps",   "👣 Tổng bước",   "—"),
            ("dust",    "🧹 Bụi đã hút",  "—"),
            ("battery", "🔋 Pin còn lại", "—"),
            ("charges", "⚡ Lần sạc",     "—"),
            ("status",  "📍 Trạng thái",  "—"),
        ]
        for key, label, default in fields:
            row = tk.Frame(current_frame, bg="#1E1E2E")
            row.pack(fill="x", padx=6, pady=2)
            tk.Label(row, text=label+":", bg="#1E1E2E", fg="#A6ADC8",
                     font=("Helvetica", 9), width=14, anchor="w").pack(side="left")
            lbl = tk.Label(row, text=default, bg="#1E1E2E", fg="#CDD6F4",
                           font=("Helvetica", 9, "bold"), anchor="w")
            lbl.pack(side="left")
            self.labels[key] = lbl

        # Tab Buttons
        tab_frame = tk.Frame(self, bg="#1E1E2E")
        tab_frame.pack(fill="x", padx=8, pady=(10, 0))
        
        self.btn_hist = tk.Button(tab_frame, text="Lịch sử", bg="#585B70", fg="#CDD6F4",
                                  font=("Helvetica", 9, "bold"), relief="flat",
                                  command=self._show_hist)
        self.btn_hist.pack(side="left", fill="x", expand=True, padx=(0, 2))
        
        self.btn_log = tk.Button(tab_frame, text="Nhật ký", bg="#313244", fg="#CDD6F4",
                                 font=("Helvetica", 9, "bold"), relief="flat",
                                 command=self._show_log)
        self.btn_log.pack(side="left", fill="x", expand=True, padx=(2, 0))

        # Bottom container
        self.bottom_container = tk.Frame(self, bg="#1E1E2E", bd=1, relief="groove")
        self.bottom_container.pack(fill="both", expand=True, padx=8, pady=(0, 4))

        # Hist Frame
        self.hist_frame = tk.Frame(self.bottom_container, bg="#1E1E2E")
        self.hist_frame.pack(fill="both", expand=True)

        # Log Frame
        self.log_frame = tk.Frame(self.bottom_container, bg="#1E1E2E")

        cols = ("Thuật toán", "Bước", "Sạc", "Bụi", "Pin còn")
        self.tree = ttk.Treeview(self.hist_frame, columns=cols, show="headings", height=12)
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Treeview", background="#313244", foreground="#CDD6F4",
                        fieldbackground="#313244", rowheight=20,
                        font=("Helvetica", 8))
        style.configure("Treeview.Heading", background="#45475A", foreground="#89B4FA",
                        font=("Helvetica", 8, "bold"))
        style.map("Treeview", background=[("selected", "#585B70")])

        for col in cols:
            w = 90 if col == "Thuật toán" else 50
            self.tree.heading(col, text=col)
            self.tree.column(col, width=w, anchor="center")

        vsb = ttk.Scrollbar(self.hist_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(self.hist_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        vsb.pack(side="right", fill="y")
        hsb.pack(side="bottom", fill="x")
        self.tree.pack(fill="both", expand=True, padx=4, pady=4)

        btn_clear = tk.Button(self.hist_frame, text="🗑 Xoá lịch sử", bg="#45475A", fg="#CDD6F4",
                              font=("Helvetica", 9), relief="flat", cursor="hand2",
                              command=self._clear_history)
        btn_clear.pack(pady=6)

        # Build Log
        self.log_text = tk.Text(self.log_frame, bg="#1E1E2E", fg="#A6ADC8",
                                font=("Consolas", 8), state="disabled",
                                wrap="word", height=12)
        log_scroll = ttk.Scrollbar(self.log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scroll.set)
        log_scroll.pack(side="right", fill="y")
        self.log_text.pack(side="left", fill="both", expand=True, pady=4)

    def update_live(self, algo_name, steps, dust_collected, total_dust,
                    battery, charges, status_text):
        self.labels["algo"].config(text=algo_name, fg="#89DCEB")
        self.labels["steps"].config(text=str(steps))
        if total_dust != "":
            self.labels["dust"].config(text=f"{dust_collected}/{total_dust}")
        else:
            self.labels["dust"].config(text=str(dust_collected))
        self.labels["battery"].config(text=str(battery))
        self.labels["charges"].config(text=str(charges))
        color = "#A6E3A1" if status_text == "Đang chạy" else (
            "#F38BA8" if status_text == "Hết pin" else "#89DCEB")
        self.labels["status"].config(text=status_text, fg=color)

    def add_history(self, algo_name, steps, charges, dust_collected,
                    total_dust, battery):
        dust_text = f"{dust_collected}/{total_dust}" if total_dust != "" else str(dust_collected)
        self.tree.insert("", 0, values=(
            algo_name[:16], steps, charges,
            dust_text, battery
        ))

    def reset_current(self):
        for key, lbl in self.labels.items():
            lbl.config(text="—", fg="#CDD6F4")

    def _clear_history(self):
        for item in self.tree.get_children():
            self.tree.delete(item)

    def _show_hist(self):
        self.btn_hist.config(bg="#585B70")
        self.btn_log.config(bg="#313244")
        self.log_frame.pack_forget()
        self.hist_frame.pack(fill="both", expand=True)

    def _show_log(self):
        self.btn_log.config(bg="#585B70")
        self.btn_hist.config(bg="#313244")
        self.hist_frame.pack_forget()
        self.log_frame.pack(fill="both", expand=True)

    def clear_log(self):
        self.log_text.config(state="normal")
        self.log_text.delete(1.0, "end")
        self.log_text.config(state="disabled")

    def add_log(self, text):
        self.log_text.config(state="normal")
        self.log_text.insert("end", text + "\n")
        lines = int(self.log_text.index("end-1c").split('.')[0])
        if lines > 200:
            self.log_text.delete(1.0, f"{lines-200}.0")
        self.log_text.see("end")
        self.log_text.config(state="disabled")

"""
Vacuum World — Main Application
"""
import sys, os
import tkinter as tk
from tkinter import ttk

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from map_generator import (generate_map, generate_map_dual,
                            GRID_ROWS, GRID_COLS, BATTERY_MAX, DUST, FLOOR)
from algorithms import ALGORITHMS, EXPLORATION_ALGOS, ADVERSARIAL_ALGOS, DUAL_ALGOS
from ui.map_canvas import VacuumCanvas, CELL_SIZE
from ui.stats_panel import StatsPanel

ANIMATION_DELAY_MS = 60

ALGO_GROUPS = [
    ("Uninformed Search",       ["BFS", "DFS"]),
    ("Informed / Heuristic",    ["GBFS (Greedy)", "A*"]),
    ("Local Search",            ["Hill Climbing", "Simulated Annealing"]),
    ("Constraint Satisfaction", ["Backtracking", "Forward Checking"]),
    ("Complex Environment",     ["Unknown - BFS", "Partial Observable (R=2)"]),
    ("Adversarial Search",      ["Minimax", "Alpha-Beta"]),
]

GROUP_COLORS = ["#89B4FA","#A6E3A1","#FAB387","#F38BA8","#89DCEB","#CBA6F7"]

FONT_TITLE  = ("Segoe UI", 11, "bold")
FONT_GROUP  = ("Segoe UI", 9, "bold")
FONT_ITEM   = ("Segoe UI", 9)
FONT_SMALL  = ("Segoe UI", 8)
FONT_BTN    = ("Segoe UI", 9, "bold")


class AccordionGroup(tk.Frame):
    def __init__(self, master, title, color, algo_var, algo_names,
                 on_select_cb, **kwargs):
        super().__init__(master, bg="#1E1E2E", **kwargs)
        self._open  = True
        self._color = color

        self._header = tk.Button(
            self, text=f"  {title}",
            bg="#2A2A3E", fg=color,
            font=FONT_GROUP,
            relief="flat", anchor="w", padx=8, pady=5,
            cursor="hand2",
            command=self._toggle
        )
        self._header.pack(fill="x", pady=(2, 0))
        self._header.bind("<Enter>", lambda e: self._header.config(bg="#35354F"))
        self._header.bind("<Leave>", lambda e: self._header.config(bg="#2A2A3E"))

        self._body = tk.Frame(self, bg="#1E1E2E")
        self._body.pack(fill="x", padx=4)

        for name in algo_names:
            rb = tk.Radiobutton(
                self._body,
                text=f"  {name}",
                variable=algo_var,
                value=name,
                bg="#1E1E2E", fg="#CDD6F4",
                selectcolor="#2A2A3E",
                activebackground="#1E1E2E",
                activeforeground=color,
                font=FONT_ITEM,
                indicatoron=True,
                anchor="w",
                justify="left",
                command=on_select_cb,
            )
            rb.pack(anchor="w", padx=16, pady=2, fill="x")
            rb.bind("<Enter>", lambda e, b=rb: b.config(fg=color))
            rb.bind("<Leave>", lambda e, b=rb: b.config(fg="#CDD6F4"))

    def _toggle(self):
        self._open = not self._open
        if self._open:
            self._body.pack(fill="x", padx=4)
        else:
            self._body.pack_forget()


class VacuumApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Vacuum World — AI Search Algorithms")
        self.configure(bg="#1E1E2E")
        self.resizable(True, True)
        self.minsize(1100, 780)

        self._grid        = None
        self._dock        = None
        self._dust_cells  = None
        self._room_info   = []
        self._agent       = None
        self._agent2      = None   # 2nd robot for Complex Environment
        self._running     = False
        self._animating   = False
        self._after_id    = None
        self._algo_name   = ""
        self._prev_pet_pos = None
        self._is_dual     = False

        self._build_ui()
        self._new_map()

    # ─────────────────────────── UI BUILD ─────────────────────────────
    def _build_ui(self):
        # Top bar — không có icon
        top = tk.Frame(self, bg="#13131F", pady=7)
        top.pack(fill="x")
        tk.Label(top, text="Vacuum World",
                 bg="#13131F", fg="#CDD6F4",
                 font=("Segoe UI", 14, "bold")).pack(side="left", padx=14)
        tk.Label(top, text="AI Search Algorithm Visualizer",
                 bg="#13131F", fg="#585B70",
                 font=("Segoe UI", 9)).pack(side="left", padx=6)

        # Main layout
        main = tk.Frame(self, bg="#1E1E2E")
        main.pack(fill="both", expand=True, padx=8, pady=8)

        # Left sidebar
        left_outer = tk.Frame(main, bg="#1E1E2E", width=225)
        left_outer.pack(side="left", fill="y", padx=(0, 6))
        left_outer.pack_propagate(False)

        lc = tk.Canvas(left_outer, bg="#1E1E2E", highlightthickness=0, width=210)
        ls = ttk.Scrollbar(left_outer, orient="vertical", command=lc.yview)
        lc.configure(yscrollcommand=ls.set)
        ls.pack(side="right", fill="y")
        lc.pack(side="left", fill="both", expand=True)
        left = tk.Frame(lc, bg="#1E1E2E")
        lc.create_window((0, 0), window=left, anchor="nw")
        left.bind("<Configure>", lambda e: lc.configure(scrollregion=lc.bbox("all")))
        lc.bind_all("<MouseWheel>",
                    lambda e: lc.yview_scroll(int(-1*(e.delta/120)), "units"))
        self._build_left_panel(left)

        # Center
        center = tk.Frame(main, bg="#1E1E2E")
        center.pack(side="left", fill="both", expand=True)
        self._map_frame = center

        # Right stats
        right = tk.Frame(main, bg="#1E1E2E", width=295)
        right.pack(side="left", fill="y", padx=(6, 0))
        right.pack_propagate(False)
        self.stats = StatsPanel(right)
        self.stats.pack(fill="both", expand=True)

    def _build_left_panel(self, parent):
        tk.Label(parent, text="Chon thuat toan",
                 bg="#1E1E2E", fg="#89B4FA",
                 font=FONT_TITLE).pack(pady=(10, 4))

        tk.Frame(parent, bg="#313244", height=1).pack(fill="x", padx=8, pady=(0, 6))

        self._algo_var = tk.StringVar(value="A*")
        for (title, names), color in zip(ALGO_GROUPS, GROUP_COLORS):
            grp = AccordionGroup(
                parent, title, color,
                algo_var=self._algo_var,
                algo_names=names,
                on_select_cb=self._on_algo_change,
            )
            grp.pack(fill="x", padx=4, pady=1)

        tk.Frame(parent, bg="#313244", height=1).pack(fill="x", padx=8, pady=8)

        # Speed
        tk.Label(parent, text="Toc do animation",
                 bg="#1E1E2E", fg="#A6ADC8",
                 font=FONT_SMALL).pack()
        self._speed_var = tk.IntVar(value=ANIMATION_DELAY_MS)
        tk.Scale(parent, from_=5, to=200, orient="horizontal",
                 variable=self._speed_var,
                 bg="#1E1E2E", fg="#CDD6F4",
                 troughcolor="#313244", highlightthickness=0,
                 label="ms/buoc", font=FONT_SMALL).pack(fill="x", padx=8)

        tk.Frame(parent, bg="#313244", height=1).pack(fill="x", padx=8, pady=8)

        # Buttons — không có icon
        bdef = dict(font=FONT_BTN, relief="flat", cursor="hand2", pady=5, bd=0)
        self._btn_run = self._make_btn(parent, "Chay", "#A6E3A1", "#1E1E2E",
                                       self._run, **bdef)
        self._btn_stop = self._make_btn(parent, "Dung", "#FAB387", "#1E1E2E",
                                        self._stop, **bdef)
        self._btn_stop.config(state="disabled")
        self._make_btn(parent, "Reset",     "#89B4FA", "#1E1E2E", self._reset, **bdef)
        self._make_btn(parent, "Map moi",   "#CBA6F7", "#1E1E2E", self._new_map, **bdef)

        tk.Frame(parent, bg="#313244", height=1).pack(fill="x", padx=8, pady=8)

        # Legend — không có icon
        legend_lines = [
            ("Robot tim", "#7E57C2"),
            ("  Vong pin: xanh la / cam / do", "#A6ADC8"),
            ("Robot xanh (Dual mode)", "#89DCEB"),
            ("Pet (Minimax/AB)", "#FF8A65"),
            ("O da di qua", "#4FC3F7"),
            ("Chua kham pha", "#585B70"),
            ("O cua thong phong", "#BCAAA4"),
        ]
        for txt, col in legend_lines:
            tk.Label(parent, text=txt, bg="#1E1E2E", fg=col,
                     font=FONT_SMALL, anchor="w").pack(anchor="w", padx=12, pady=1)

    def _make_btn(self, parent, text, bg, fg, cmd, **kw):
        btn = tk.Button(parent, text=text, bg=bg, fg=fg, command=cmd, **kw)
        btn.pack(fill="x", padx=8, pady=2)
        btn.bind("<Enter>", lambda e, b=btn, c=bg: b.config(bg=self._lighten(c)))
        btn.bind("<Leave>", lambda e, b=btn, c=bg: b.config(bg=c))
        return btn

    @staticmethod
    def _lighten(hex_color):
        try:
            r = min(255, int(hex_color[1:3], 16) + 35)
            g = min(255, int(hex_color[3:5], 16) + 35)
            b = min(255, int(hex_color[5:7], 16) + 35)
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return hex_color

    # ─────────────────────────── MAP ──────────────────────────────────
    # Removed _pick_robot2_start

    def _new_map(self):
        self._stop()
        algo = self._algo_var.get() if hasattr(self, "_algo_var") else ""
        self._is_dual = algo in DUAL_ALGOS

        if self._is_dual:
            result = generate_map_dual(GRID_ROWS, GRID_COLS)
            (self._grid, (self._dock, self._dock2), self._dust_cells,
             self._room_info, self._furniture_map, self._door_info) = result
        else:
            result = generate_map(GRID_ROWS, GRID_COLS)
            (self._grid, self._dock, self._dust_cells,
             self._room_info, self._furniture_map, self._door_info) = result
            self._dock2 = None

        if hasattr(self, "_canvas") and self._canvas:
            self._canvas.destroy()

        self._canvas = VacuumCanvas(
            self._map_frame, self._grid, self._dock, self._dust_cells,
            room_info=self._room_info,
            furniture_map=self._furniture_map,
            door_info=self._door_info)
        self._canvas.pack()

        self._agent  = None
        self._agent2 = None
        self._prev_pet_pos = None
        self._robot2_start = None
        self.stats.reset_current()
        self.stats.clear_log()
        self._log_idx1 = 0
        self._log_idx2 = 0

        # Robot 1 luôn xuất hiện tại dock ngay từ đầu
        self._canvas.move_robot(self._dock, 1.0)
        # Robot 2 xuất hiện ngay từ đầu nếu là dual mode (tại dock2)
        if self._is_dual:
            self._canvas.move_robot2(self._dock2, 1.0)

    def _reset(self):
        self._stop()
        if hasattr(self, "_canvas") and self._canvas:
            self._canvas.grid_data = [row[:] for row in self._grid]
            self._canvas.reset_display()
        self._agent  = None
        self._agent2 = None
        self._prev_pet_pos = None
        self.stats.reset_current()
        self.stats.clear_log()
        self._log_idx1 = 0
        self._log_idx2 = 0

        # Robot 1 luôn hiện tại dock sau reset
        self._canvas.move_robot(self._dock, 1.0)
        # Robot 2 xuất hiện ngay nếu đang ở dual mode
        if self._is_dual:
            self._canvas.move_robot2(self._dock2, 1.0)

    # ─────────────────────────── ALGO ─────────────────────────────────
    def _on_algo_change(self):
        # Cập nhật dual mode TRƯỚC khi reset để _reset() vẽ đúng số robot
        algo = self._algo_var.get()
        was_dual = self._is_dual
        self._is_dual = algo in DUAL_ALGOS
        if was_dual != self._is_dual:
            # Chuyển giữa dual/non-dual: tạo lại map mới phù hợp
            self._new_map()
        else:
            # Cùng loại mode: chỉ reset, giữ nguyên map
            self._reset()

    def _run(self):
        if self._running:
            return
        self._reset()
        self._algo_name = self._algo_var.get()
        cls = ALGORITHMS.get(self._algo_name)
        if cls is None:
            return

        self._is_dual = self._algo_name in DUAL_ALGOS

        import random
        run_seed = random.randint(0, 1000000)

        # ==========================================
        # GIAI ĐOẠN 1: MÔ PHỎNG ẨN (HIDDEN SIMULATION)
        # Chi chay voi cac thuat toan NHANH (khong phai exploration/dual)
        # De tranh dong UI thread
        # ==========================================
        if self._algo_name not in EXPLORATION_ALGOS and not self._is_dual:
            random.seed(run_seed)
            dummy_grid = [row[:] for row in self._grid]
            dummy_a = cls(dummy_grid, self._dock, set(self._dust_cells), GRID_ROWS, GRID_COLS)
            sim_steps = 0
            while not dummy_a.done and sim_steps < 5000:
                dummy_a.step()
                sim_steps += 1
            self._log_events(dummy_a, '_log_idx1', 'Robot Tím')
            def format_path(log):
                coords = [f"({p[0]},{p[1]})" if isinstance(p, tuple) and len(p) == 2 else str(p) 
                          for p, e in log if p is not None]
                lines = []
                for i in range(0, len(coords), 4):
                    lines.append(" -> ".join(coords[i:i+4]))
                return " -> \n".join(lines)
            path_str = format_path(dummy_a.move_log)
            self.stats.add_log(f"DUONG DI HOAN CHINH:\n{path_str}")

        # ==========================================
        # GIAI ĐOẠN 2: CHẠY HOẠT ẢNH (ANIMATION)
        # ==========================================
        random.seed(run_seed)

        if self._is_dual:
            # 2 robots, chia bụi về 2 nửa
            dust1, dust2 = self._dust_cells
            from map_generator import DUST, DUST2
            # Truyền target_dust_val ngay khi khởi tạo để _reveal dùng đúng loại bụi
            try:
                self._agent  = cls(self._grid, self._dock, dust1, GRID_ROWS, GRID_COLS, target_dust_val=DUST)
                self._agent2 = cls(self._grid, self._dock2, dust2, GRID_ROWS, GRID_COLS, target_dust_val=DUST2)
            except TypeError:
                # Fallback nếu thuật toán không hỗ trợ tham số mới
                self._agent  = cls(self._grid, self._dock, dust1, GRID_ROWS, GRID_COLS)
                self._agent2 = cls(self._grid, self._dock2, dust2, GRID_ROWS, GRID_COLS)
                self._agent.target_dust_val = DUST
                # Set target_dust_val TRUOC khi set_start_pos de reveal dung loai bui
                self._agent2.target_dust_val = DUST2
            
            if hasattr(self._agent2, 'set_start_pos'):
                self._agent2.set_start_pos(self._dock2)
            else:
                self._agent2.pos = self._dock2
        else:
            self._agent = cls(self._grid, self._dock, self._dust_cells,
                              GRID_ROWS, GRID_COLS)

        if self._algo_name in EXPLORATION_ALGOS:
            self._canvas.set_known_grid(self._agent.known_grid)
        else:
            self._canvas.show_known = False
            self._canvas.known_grid = None

        if self._algo_name in ADVERSARIAL_ALGOS:
            self._prev_pet_pos = self._agent.pet_pos
            self._canvas.draw_pet(self._agent.pet_pos)
        else:
            self._canvas.clear_pet()
            self._prev_pet_pos = None

        self._running   = True
        self._animating = False
        self._btn_run.config(state="disabled")
        self._btn_stop.config(state="normal")

        # Vẽ robot SAU set_known_grid (vì set_known_grid xóa canvas)
        self._canvas.move_robot(self._agent.pos, 1.0)
        if self._is_dual and self._agent2:
            self._canvas.move_robot2(self._agent2.pos, 1.0)

        self._animate()

    def _log_events(self, agent, idx_attr, prefix):
        idx = getattr(self, idx_attr, 0)
        while idx < len(agent.move_log):
            pos, event = agent.move_log[idx]
            if pos is None and isinstance(event, str) and event.startswith("ALGO:"):
                msg = f"[{prefix}] {event[5:]}"
            else:
                pos_str = f"({pos[0]},{pos[1]})" if isinstance(pos, tuple) and len(pos) == 2 else str(pos)
                if event == "move": msg = f"{prefix}: Di chuyển đến {pos_str}"
                elif event == "vacuum": msg = f"{prefix}: Hút bụi tại {pos_str}"
                elif event == "charge": msg = f"{prefix}: Sạc pin tại {pos_str}"
                elif event == "finished": msg = f"{prefix}: Hoàn thành tại {pos_str}"
                elif event == "dead": msg = f"{prefix}: Hết pin tại {pos_str}"
                else: msg = f"{prefix}: {event} tại {pos_str}"
            self.stats.add_log(msg)
            idx += 1
        setattr(self, idx_attr, idx)

    def _animate(self):
        if not self._running:
            return
        if self._animating:
            self._after_id = self.after(5, self._animate)
            return
        self._animating = True

        delay = self._speed_var.get()

        if self._is_dual:
            self._animate_dual(delay)
            return

        agent     = self._agent
        prev_dust = set(agent.dust_remaining)
        prev_pos  = agent.pos
        prev_pet  = getattr(agent, "pet_pos", None)
        alive     = agent.step()
        new_pos   = agent.pos
        new_pet   = getattr(agent, "pet_pos", None)

        if self._algo_name in EXPLORATION_ALGOS:
            self._canvas.known_grid = agent.known_grid
            self._canvas.refresh_known()

        if new_pos in prev_dust and new_pos not in agent.dust_remaining:
            self._canvas.update_cell_after_vacuum(new_pos)

        self._canvas.mark_visited(prev_pos)

        # CSP backtrack highlight
        if self._algo_name in {"Backtracking", "Forward Checking"}:
            bt_step = getattr(agent, "_last_backtrack", None)
            if bt_step:
                self._canvas.flash_backtrack(bt_step)

        battery_ratio = max(0, agent.battery) / BATTERY_MAX

        def after_move():
            self._animating = False
            self._update_live_stats()
            if alive:
                self._after_id = self.after(delay, self._animate)
            else:
                self._finish()

        self._canvas.move_robot_smooth(
            prev_pos, new_pos, battery_ratio,
            steps=5, delay=max(3, delay // 5),
            on_done=after_move)

        if (self._algo_name in ADVERSARIAL_ALGOS
                and new_pet and prev_pet and new_pet != prev_pet):
            self._canvas.move_pet_smooth(
                prev_pet, new_pet,
                steps=4, delay=max(3, delay // 6))

    def _animate_dual(self, delay):
        a1, a2 = self._agent, self._agent2

        prev1 = a1.pos
        prev2 = a2.pos if a2 and not a2.done else None
        pd1   = set(a1.dust_remaining)
        pd2   = set(a2.dust_remaining) if a2 else set()

        alive1 = a1.step() if not a1.done else False
        alive2 = a2.step() if a2 and not a2.done else False

        # Cap nhat log tung buoc trong animation (thay vi hidden simulation)
        self._log_events(a1, '_log_idx1', 'BS1')
        if a2:
            self._log_events(a2, '_log_idx2', 'BS2')

        # Cập nhật fog of war cho exploration algos (dual mode)
        # Merge known_grid của cả 2 robot: ô nào ai biết thì cả 2 đều thấy
        if self._algo_name in EXPLORATION_ALGOS:
            UNKNOWN_VAL = -1
            kg1 = a1.known_grid
            kg2 = getattr(a2, 'known_grid', None) if a2 else None
            if kg2 is not None:
                for r in range(GRID_ROWS):
                    for c in range(GRID_COLS):
                        # kg1 chưa biết, kg2 đã biết → copy từ kg2 sang kg1
                        if kg1[r][c] == UNKNOWN_VAL and kg2[r][c] != UNKNOWN_VAL:
                            kg1[r][c] = kg2[r][c]
                        # kg2 chưa biết, kg1 đã biết → copy từ kg1 sang kg2
                        elif kg2[r][c] == UNKNOWN_VAL and kg1[r][c] != UNKNOWN_VAL:
                            kg2[r][c] = kg1[r][c]
                        # Cả 2 cùng biết, nhưng 1 bên đã hút bụi (0) -> đồng bộ 0 cho bên kia
                        elif kg1[r][c] != UNKNOWN_VAL and kg2[r][c] != UNKNOWN_VAL:
                            if kg1[r][c] == 0:
                                kg2[r][c] = 0
                            elif kg2[r][c] == 0:
                                kg1[r][c] = 0
            self._canvas.known_grid = kg1
            self._canvas.refresh_known()

        # Update vacuumed cells
        if a1.pos in pd1 and a1.pos not in a1.dust_remaining:
            self._canvas.update_cell_after_vacuum(a1.pos)
            # Sync grid thật để _reveal không hiển thị lại bụi đã hút
            if a2:
                a2.grid[a1.pos[0]][a1.pos[1]] = 0
        if a2 and a2.pos in pd2 and a2.pos not in a2.dust_remaining:
            self._canvas.update_cell_after_vacuum(a2.pos)
            a1.grid[a2.pos[0]][a2.pos[1]] = 0

        self._canvas.mark_visited(prev1)
        if prev2:
            self._canvas.mark_visited(prev2)

        br1 = max(0, a1.battery) / BATTERY_MAX
        br2 = max(0, a2.battery) / BATTERY_MAX if a2 else 1.0

        both_done = a1.done and (not a2 or a2.done)

        def after_move():
            self._animating = False
            self._update_live_stats_dual()
            if not both_done:
                self._after_id = self.after(delay, self._animate)
            else:
                self._finish_dual()

        self._canvas.move_robot_smooth(
            prev1, a1.pos, br1,
            steps=5, delay=max(3, delay // 5),
            on_done=after_move)

        if prev2 and a2:
            self._canvas.move_robot2_smooth(
                prev2, a2.pos, br2,
                steps=5, delay=max(3, delay // 5))

    def _update_live_stats(self):
        agent = self._agent
        status_map = {
            "running":  "Dang chay",
            "finished": "Hoan thanh",
            "dead":     "Het pin",
            "failed":   "That bai (>10 sac)",
        }
        self.stats.update_live(
            algo_name=self._algo_name,
            steps=agent.steps,
            dust_collected=agent.dust_collected,
            total_dust=agent.total_dust,
            battery=agent.battery,
            charges=agent.charges,
            status_text=status_map.get(agent.status, "Dang chay"),
        )

    def _update_live_stats_dual(self):
        a1, a2 = self._agent, self._agent2
        both_done = a1.done and (not a2 or a2.done)
        any_dead = a1.status == "dead" or (a2 and a2.status == "dead")

        if both_done: st = "Hoàn thành"
        elif any_dead: st = "Hết pin"
        else: st = "Đang chạy"

        self.stats.update_live(
            algo_name=self._algo_name + " [x2]",
            steps=f"BS1:{a1.steps} BS2:{a2.steps if a2 else 0}",
            dust_collected=f"BS1:{a1.dust_collected}/{a1.total_dust} | BS2:{a2.dust_collected if a2 else 0}/{a2.total_dust if a2 else 0}",
            total_dust="",
            battery=f"BS1:{a1.battery} BS2:{a2.battery if a2 else 0}",
            charges=f"BS1:{a1.charges} BS2:{a2.charges if a2 else 0}",
            status_text=st
        )

    def _finish(self):
        self._running = False
        self._btn_run.config(state="normal")
        self._btn_stop.config(state="disabled")
        self._update_live_stats()
        a = self._agent
        self.stats.add_history(self._algo_name, a.steps, a.charges,
                               a.dust_collected, a.total_dust, a.battery)
                               
        def format_path(log):
            coords = [f"({p[0]},{p[1]})" if isinstance(p, tuple) and len(p) == 2 else str(p) 
                      for p, e in log if p is not None]
            lines = []
            for i in range(0, len(coords), 4):
                lines.append(" -> ".join(coords[i:i+4]))
            return " -> \n".join(lines)
            
        path_str = format_path(a.move_log)
        self.stats.add_log(f"DUONG DI HOAN CHINH:\n{path_str}")

    def _finish_dual(self):
        self._running = False
        self._btn_run.config(state="normal")
        self._btn_stop.config(state="disabled")
        a1, a2 = self._agent, self._agent2
        self._update_live_stats_dual()
        
        # Gộp (sum) chỉ số cho History
        total_steps = str(a1.steps + (a2.steps if a2 else 0))
        total_charges = str(a1.charges + (a2.charges if a2 else 0))
        collected = a1.dust_collected + (a2.dust_collected if a2 else 0)
        total_dust_all = a1.total_dust + (a2.total_dust if a2 else 0)
        dust_text = f"{collected}/{total_dust_all}"
        total_bat = str(a1.battery + (a2.battery if a2 else 0))
        
        self.stats.add_history(self._algo_name + " [x2]", total_steps,
                               total_charges, dust_text, "", total_bat)
                               
        # In duong di tong hop sau khi animation hoan thanh
        def format_path(log):
            coords = [f"({p[0]},{p[1]})" if isinstance(p, tuple) and len(p) == 2 else str(p) 
                      for p, e in log if p is not None]
            lines = []
            for i in range(0, len(coords), 4):
                lines.append(" -> ".join(coords[i:i+4]))
            return " -> \n".join(lines)
            
        path_str1 = format_path(a1.move_log)
        self.stats.add_log(f"DUONG DI HOAN CHINH (BS1):\n{path_str1}")
        if a2:
            path_str2 = format_path(a2.move_log)
            self.stats.add_log(f"DUONG DI HOAN CHINH (BS2):\n{path_str2}")

    def _stop(self):
        self._running   = False
        self._animating = False
        if self._after_id:
            self.after_cancel(self._after_id)
            self._after_id = None
        if hasattr(self, "_btn_run"):
            self._btn_run.config(state="normal")
        if hasattr(self, "_btn_stop"):
            self._btn_stop.config(state="disabled")


if __name__ == "__main__":
    app = VacuumApp()
    app.mainloop()

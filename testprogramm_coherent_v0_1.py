import socket
import threading
import tkinter as tk
from datetime import datetime
from tkinter import ttk

APP_NAME = "Testprogramm Coherent V0.1"
TITLE_TEXT = "Coherent Belp"
VERSION_TEXT = "Softwareversion: V0.1"
INTERNET_TITLE = "Internet Connection Test:"
USER_TITLE = "Benutzer auswählen"
DURATION_MS = 5000
UPDATE_MS = 50
MONITOR_INTERVAL_MS = 5000
PASS_TO_USER_DELAY_MS = 700
DNS_TEST_PORT = 53
# DNS endpoints for connectivity probing (Cloudflare, Google, Quad9).
DNS_TEST_SERVERS = ["1.1.1.1", "8.8.8.8", "9.9.9.9"]
CONNECT_TIMEOUT_SEC = 1.0
QUESTION_TEXTS = [
    "Frage 1: Sind auf dem Gehäuse Kratzer oder andere Arten mechanischer Schäden zu erkennen?",
    "Frage 2: Ist die nächste Sichtprüfung ohne Auffälligkeiten?",
]
WIFI_ICON_X_OFFSET = -15
WIFI_ICON_Y_OFFSET = 10
WIFI_ICON_SIZE = (64, 48)
WIFI_ARCS = [(8, 8, 56, 56), (16, 16, 48, 48), (24, 24, 40, 40)]
WIFI_DOT = (29, 35, 35, 41)


class TestprogrammApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_NAME)
        self.root.configure(bg="white")
        self.root.attributes("-fullscreen", True)
        self.root.bind("<Escape>", lambda e: self.on_close())
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.main_frame = tk.Frame(self.root, bg="white")
        self.main_frame.pack(expand=True, fill="both")

        self.elapsed = 0
        self.connected = False

        self.progress = None
        self.status_label = None
        self.result_label = None
        self.retry_button = None
        self.wifi_canvas = None
        self.datetime_label = None
        self.selected_user_label = None
        self.confirm_user_button = None
        self.selected_user = None
        self.question_result_label = None
        self.animate_after_id = None
        self.datetime_after_id = None
        self.monitor_after_id = None
        self.pass_transition_after_id = None
        self.connection_check_running = False
        self.internet_test_running = False
        self.monitor_lock = threading.Lock()
        self.internet_test_lock = threading.Lock()

        self.show_start_screen()
        self.start_connection_monitor()

    def clear_screen(self):
        if self.animate_after_id is not None:
            try:
                self.root.after_cancel(self.animate_after_id)
            except tk.TclError:
                pass
            self.animate_after_id = None

        if self.datetime_after_id is not None:
            try:
                self.root.after_cancel(self.datetime_after_id)
            except tk.TclError:
                pass
            self.datetime_after_id = None

        if self.pass_transition_after_id is not None:
            try:
                self.root.after_cancel(self.pass_transition_after_id)
            except tk.TclError:
                pass
            self.pass_transition_after_id = None

        for widget in self.main_frame.winfo_children():
            widget.destroy()

        self.progress = None
        self.status_label = None
        self.result_label = None
        self.retry_button = None
        self.wifi_canvas = None
        self.datetime_label = None
        self.selected_user_label = None
        self.confirm_user_button = None
        self.question_result_label = None

    def add_wifi_icon(self):
        self.wifi_canvas = tk.Canvas(
            self.main_frame,
            width=WIFI_ICON_SIZE[0],
            height=WIFI_ICON_SIZE[1],
            bg="white",
            highlightthickness=0,
        )
        self.wifi_canvas.place(relx=1.0, x=WIFI_ICON_X_OFFSET, y=WIFI_ICON_Y_OFFSET, anchor="ne")
        self.draw_wifi_icon("green" if self.connected else "red")

    def draw_wifi_icon(self, color: str):
        if not self.wifi_canvas:
            return
        c = self.wifi_canvas
        c.delete("all")
        for x1, y1, x2, y2 in WIFI_ARCS:
            c.create_arc(x1, y1, x2, y2, start=35, extent=110, style=tk.ARC, width=4, outline=color)
        c.create_oval(*WIFI_DOT, fill=color, outline=color)

    def has_internet_connection(self) -> bool:
        for host in DNS_TEST_SERVERS:
            try:
                # Successful connect is the connectivity test; socket is auto-closed by context manager.
                with socket.create_connection((host, DNS_TEST_PORT), timeout=CONNECT_TIMEOUT_SEC):
                    return True
            except OSError:
                continue
        return False

    def start_connection_monitor(self):
        self.schedule_connection_check()

    def schedule_connection_check(self):
        if not self.root.winfo_exists():
            return

        with self.monitor_lock:
            if self.connection_check_running:
                return
            self.connection_check_running = True
        threading.Thread(target=self._connection_check_worker, daemon=True).start()

    def _connection_check_worker(self):
        connected = self.has_internet_connection()
        self.root.after(0, self._apply_connection_check_result, connected)

    def _apply_connection_check_result(self, connected: bool):
        with self.monitor_lock:
            self.connection_check_running = False
        self.set_connection_state(connected)
        if self.root.winfo_exists():
            self.monitor_after_id = self.root.after(MONITOR_INTERVAL_MS, self.schedule_connection_check)

    def set_connection_state(self, connected: bool):
        self.connected = connected
        self.draw_wifi_icon("green" if connected else "red")

    def show_start_screen(self):
        self.clear_screen()
        self.elapsed = 0

        title_label = tk.Label(
            self.main_frame,
            text=TITLE_TEXT,
            font=("Arial", 42, "bold underline"),
            fg="blue",
            bg="white",
        )
        title_label.pack(expand=True)

        version_label = tk.Label(
            self.main_frame,
            text=VERSION_TEXT,
            font=("Arial", 22, "bold"),
            fg="blue",
            bg="white",
        )
        version_label.pack(pady=(0, 20))

        self.progress = ttk.Progressbar(
            self.main_frame,
            orient="horizontal",
            mode="determinate",
            length=500,
            maximum=DURATION_MS,
        )
        self.progress.pack(pady=20)

        self.animate_progress()

    def animate_progress(self):
        self.elapsed += UPDATE_MS
        if self.progress:
            self.progress["value"] = self.elapsed

        if self.elapsed < DURATION_MS:
            self.animate_after_id = self.root.after(UPDATE_MS, self.animate_progress)
        else:
            self.animate_after_id = None
            self.show_internet_screen()

    def show_internet_screen(self):
        self.clear_screen()
        self.add_wifi_icon()

        heading = tk.Label(
            self.main_frame,
            text=INTERNET_TITLE,
            font=("Arial", 34, "bold"),
            fg="blue",
            bg="white",
        )
        heading.pack(pady=(120, 40))

        self.status_label = tk.Label(
            self.main_frame,
            text="Checking internet connection...",
            font=("Arial", 24),
            fg="black",
            bg="white",
        )
        self.status_label.pack(pady=10)

        self.result_label = tk.Label(
            self.main_frame,
            text="",
            font=("Arial", 30, "bold"),
            bg="white",
        )
        self.result_label.pack(pady=10)

        self.retry_button = tk.Button(
            self.main_frame,
            text="Retry",
            font=("Arial", 20, "bold"),
            bg="#f0f0f0",
            activebackground="#d9d9d9",
            command=self.start_internet_test,
            padx=30,
            pady=12,
        )

        self.start_internet_test()

    def start_internet_test(self):
        with self.internet_test_lock:
            if self.internet_test_running:
                return
            self.internet_test_running = True

        if self.status_label:
            self.status_label.config(text="Checking internet connection...", fg="black")
        if self.result_label:
            self.result_label.config(text="", fg="black")
        if self.retry_button and self.retry_button.winfo_manager():
            self.retry_button.pack_forget()

        threading.Thread(target=self._internet_test_worker, daemon=True).start()

    def _internet_test_worker(self):
        connected = self.has_internet_connection()
        self.root.after(0, self._finish_internet_test, connected)

    def _finish_internet_test(self, connected: bool):
        with self.internet_test_lock:
            self.internet_test_running = False
        self.update_internet_test_result(connected)

    def update_internet_test_result(self, connected: bool):
        self.set_connection_state(connected)

        if connected:
            if self.status_label:
                self.status_label.config(text="")
            if self.result_label:
                self.result_label.config(text="PASS", fg="green")
            self.pass_transition_after_id = self.root.after(
                PASS_TO_USER_DELAY_MS, self.show_user_selection_screen
            )
        else:
            if self.status_label:
                self.status_label.config(text="No Internet Connection", fg="black")
            if self.result_label:
                self.result_label.config(text="FAIL", fg="red")
            if self.retry_button and not self.retry_button.winfo_manager():
                self.retry_button.pack(pady=20)

    def show_user_selection_screen(self):
        self.clear_screen()
        self.add_wifi_icon()
        self.selected_user = None

        self.datetime_label = tk.Label(
            self.main_frame,
            text="",
            font=("Arial", 16, "bold"),
            fg="black",
            bg="white",
        )
        self.datetime_label.place(x=20, y=20, anchor="nw")
        self.update_datetime()

        heading = tk.Label(
            self.main_frame,
            text=USER_TITLE,
            font=("Arial", 34, "bold"),
            fg="black",
            bg="white",
        )
        heading.pack(pady=(120, 40))

        button_frame = tk.Frame(self.main_frame, bg="white")
        button_frame.pack(pady=20)

        vff_button = tk.Button(
            button_frame,
            text="VFF",
            font=("Arial", 24, "bold"),
            width=10,
            height=2,
            command=lambda: self.select_user("VFF"),
        )
        vff_button.grid(row=0, column=0, padx=20)

        koo_button = tk.Button(
            button_frame,
            text="KOO",
            font=("Arial", 24, "bold"),
            width=10,
            height=2,
            command=lambda: self.select_user("KOO"),
        )
        koo_button.grid(row=0, column=1, padx=20)

        self.selected_user_label = tk.Label(
            self.main_frame,
            text="",
            font=("Arial", 20, "bold"),
            fg="blue",
            bg="white",
        )
        self.selected_user_label.pack(pady=20)

        self.confirm_user_button = tk.Button(
            self.main_frame,
            text="User bestätigen",
            font=("Arial", 18, "bold"),
            bg="#f0f0f0",
            activebackground="#d9d9d9",
            command=self.confirm_selected_user,
            padx=24,
            pady=10,
        )

    def update_datetime(self):
        if self.root.winfo_exists() and self.datetime_label and self.datetime_label.winfo_exists():
            now_text = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            self.datetime_label.config(text=now_text)
            self.datetime_after_id = self.root.after(1000, self.update_datetime)

    def select_user(self, user: str):
        self.selected_user = user
        if self.selected_user_label:
            self.selected_user_label.config(text=f"Ausgewählt: {user}")
        if self.confirm_user_button and not self.confirm_user_button.winfo_manager():
            self.confirm_user_button.pack(pady=(0, 30))

    def confirm_selected_user(self):
        if self.selected_user and self.selected_user_label:
            self.selected_user_label.config(text=f"User bestätigt: {self.selected_user}", fg="green")
        if self.confirm_user_button:
            self.confirm_user_button.config(state="disabled")
        if self.selected_user:
            self.show_question_screen(0)

    def show_question_screen(self, question_index: int):
        self.clear_screen()
        self.add_wifi_icon()

        self.datetime_label = tk.Label(
            self.main_frame,
            text="",
            font=("Arial", 16, "bold"),
            fg="black",
            bg="white",
        )
        self.datetime_label.place(relx=1.0, x=-20, y=20, anchor="ne")
        self.update_datetime()

        selected_user_text = self.selected_user if self.selected_user else "-"
        user_badge = tk.Label(
            self.main_frame,
            text=f"User: {selected_user_text}",
            font=("Arial", 14, "bold"),
            fg="black",
            bg="white",
        )
        user_badge.place(relx=1.0, x=-(WIFI_ICON_SIZE[0] + 28), y=20, anchor="ne")

        heading = tk.Label(
            self.main_frame,
            text="Prüffragen",
            font=("Arial", 32, "bold"),
            fg="black",
            bg="white",
        )
        heading.pack(pady=(120, 30))

        if question_index >= len(QUESTION_TEXTS):
            done_label = tk.Label(
                self.main_frame,
                text="Alle Fragen erfolgreich abgeschlossen.",
                font=("Arial", 24, "bold"),
                fg="green",
                bg="white",
            )
            done_label.pack(pady=40)
            return

        question_label = tk.Label(
            self.main_frame,
            text=QUESTION_TEXTS[question_index],
            font=("Arial", 24, "bold"),
            fg="black",
            bg="white",
            wraplength=1200,
            justify="center",
        )
        question_label.pack(padx=60, pady=20)

        button_frame = tk.Frame(self.main_frame, bg="white")
        button_frame.pack(pady=30)

        pass_button = tk.Button(
            button_frame,
            text="PASS",
            font=("Arial", 22, "bold"),
            width=10,
            height=2,
            bg="#d9f7d9",
            activebackground="#bdeebd",
            command=lambda: self.on_question_pass(question_index),
        )
        pass_button.grid(row=0, column=0, padx=20)

        fail_button = tk.Button(
            button_frame,
            text="FAIL",
            font=("Arial", 22, "bold"),
            width=10,
            height=2,
            bg="#ffd9d9",
            activebackground="#ffc0c0",
            command=self.on_question_fail,
        )
        fail_button.grid(row=0, column=1, padx=20)

        self.question_result_label = tk.Label(
            self.main_frame,
            text="",
            font=("Arial", 20, "bold"),
            fg="red",
            bg="white",
        )
        self.question_result_label.pack(pady=10)

    def on_question_pass(self, current_index: int):
        self.show_question_screen(current_index + 1)

    def on_question_fail(self):
        if self.question_result_label:
            self.question_result_label.config(text="FAIL bestätigt. Bitte Gehäuse prüfen.")

    def on_close(self):
        if self.monitor_after_id is not None:
            try:
                self.root.after_cancel(self.monitor_after_id)
            except tk.TclError:
                pass
            self.monitor_after_id = None
        self.clear_screen()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = TestprogrammApp(root)
    root.mainloop()

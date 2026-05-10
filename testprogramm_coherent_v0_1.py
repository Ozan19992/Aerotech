import socket
import threading
import tkinter as tk
from tkinter import ttk

APP_NAME = "Testprogramm Coherent V0.1"
TITLE_TEXT = "Coherent Belp"
VERSION_TEXT = "Softwareversion: V0.1"
NEXT_TITLE = "Internet Connection Test:"
DURATION_MS = 5000
UPDATE_MS = 50
WIFI_ICON_X_OFFSET = -15
WIFI_ICON_Y_OFFSET = 10
WIFI_ICON_SIZE = (80, 60)
WIFI_ARCS = [(10, 10, 70, 70), (20, 20, 60, 60), (30, 30, 50, 50)]
WIFI_DOT = (36, 46, 44, 54)


class TestprogrammApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_NAME)
        self.root.configure(bg="white")
        self.root.attributes("-fullscreen", True)
        self.root.bind("<Escape>", lambda e: self.root.destroy())

        self.main_frame = tk.Frame(self.root, bg="white")
        self.main_frame.pack(expand=True, fill="both")

        self.elapsed = 0
        self.progress = None
        self.status_label = None
        self.result_label = None
        self.wifi_canvas = None

        self.show_start_screen()

    def clear_screen(self):
        for widget in self.main_frame.winfo_children():
            widget.destroy()

    def show_start_screen(self):
        self.clear_screen()

        title_label = tk.Label(
            self.main_frame,
            text=TITLE_TEXT,
            font=("Arial", 42, "underline", "bold"),
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
        self.progress["value"] = self.elapsed

        if self.elapsed < DURATION_MS:
            self.root.after(UPDATE_MS, self.animate_progress)
        else:
            self.show_internet_screen()

    def show_internet_screen(self):
        self.clear_screen()

        self.wifi_canvas = tk.Canvas(
            self.main_frame,
            width=WIFI_ICON_SIZE[0],
            height=WIFI_ICON_SIZE[1],
            bg="white",
            highlightthickness=0,
        )
        self.wifi_canvas.place(relx=1.0, x=WIFI_ICON_X_OFFSET, y=WIFI_ICON_Y_OFFSET, anchor="ne")

        heading = tk.Label(
            self.main_frame,
            text=NEXT_TITLE,
            font=("Arial", 34, "bold"),
            fg="black",
            bg="white",
        )
        heading.pack(pady=(120, 40))

        self.status_label = tk.Label(
            self.main_frame,
            text="Prüfe Internetverbindung...",
            font=("Arial", 24),
            fg="black",
            bg="white",
        )
        self.status_label.pack(pady=10)

        self.result_label = tk.Label(
            self.main_frame,
            text="",
            font=("Arial", 26, "bold"),
            bg="white",
        )
        self.result_label.pack(pady=10)

        threading.Thread(target=self.check_internet_connection, daemon=True).start()

    def check_internet_connection(self):
        connected = False

        test_targets = [
            ("1.1.1.1", 53),
            ("8.8.8.8", 53),
            ("9.9.9.9", 53),
        ]

        for host, port in test_targets:
            try:
                with socket.create_connection((host, port), timeout=2):
                    connected = True
                    break
            except OSError:
                continue

        self.root.after(0, lambda: self.update_connection_ui(connected))

    def draw_wifi_icon(self, color: str):
        c = self.wifi_canvas
        c.delete("all")
        for x1, y1, x2, y2 in WIFI_ARCS:
            c.create_arc(x1, y1, x2, y2, start=35, extent=110, style=tk.ARC, width=4, outline=color)
        c.create_oval(*WIFI_DOT, fill=color, outline=color)

    def update_connection_ui(self, connected: bool):
        if connected:
            self.status_label.config(text="Internet Connected")
            self.result_label.config(text="PASS", fg="green")
            self.draw_wifi_icon("green")
        else:
            self.status_label.config(text="No Internet Connection")
            self.result_label.config(text="FAIL", fg="red")
            self.draw_wifi_icon("red")


if __name__ == "__main__":
    root = tk.Tk()
    app = TestprogrammApp(root)
    root.mainloop()

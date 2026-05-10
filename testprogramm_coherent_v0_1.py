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
USER_GUIDE_TEXT = """Touch Aktivierung – Anleitung

1. Connect the GPIO interface
Raspberry Pi leads out 40 GPIO pins, while the screen leads out 26 pins.
When connecting, pay attention to the corresponding pins and Raspberry Pi pins.

2. Connect the HDMI connector to the HDMI port of the screen and the Pi.

3. Turn the Backlight on the back of the LCD to "ON".
Note: Raspberry Pi Zero / Zero 2 W needs an additional HDMI cable for connection.

The hardware connection is as shown below (Pi 4 and Pi 3B+):
- 3.5inch-HDMI-LCD-Manual-PI4B.jpg
- 3.5inch-HDMILCD-Manual-PI3B+.jpg

Software Setting
This LCD can support Raspberry Pi OS / Ubuntu / Kali / Retropie systems.

1) Download the compressed file to the PC, and unzip it to get the .img file.
2) Connect the TF card to the PC, and use SDFormatter software to format the TF card.
3) Open the Win32DiskImager software, select the system image downloaded in step 1, and click 'Write'.
4) After image write, open config.txt in TF root and add:

hdmi_group=2
hdmi_mode=87
#Display with 800*480 resolution
hdmi_cvt 800 480 60 6 0 0 0
#Use 480*320 resolution display, you need to add the following 3 lines of code
#hdmi_pixel_freq_limit=20000000
#hdmi_cvt 480 320 60 6 0 0 0
#hdmi_drive=1
dtoverlay=waveshare-ads7846,penirq=25,xmin=200,xmax=3900,ymin=200,ymax=3900,speed=50000

5) Download waveshare-ads7846.dtbo and copy dtbo files to /boot/overlays/.
6) Insert TF card, power on Raspberry Pi, and wait more than 10 seconds.

Touch calibration
If left edge cannot be touched: adjust x_min down (e.g. 200 -> 100).
If right edge cannot be touched: adjust x_max up (e.g. 3900 -> 4000).
If top edge cannot be touched: adjust y_min down (e.g. 200 -> 100).
If bottom edge cannot be touched: adjust y_max up (e.g. 3900 -> 4000).

Use evtest for values:
sudo apt-get install evtest
sudo evtest

Calibration images:
- Calibration 1.png
- Calibration 2.png (x_min)
- Calibration 3.png (x_max)
- Calibration 4.png (y_min)
- Calibration 5.png (y_max)

sudo nano /boot/firmware/config.txt
Add:
dtoverlay=waveshare-ads7846,x_min=164,x_max=4010,y_min=154,y_max=3758
Then:
sudo reboot

Rotation
Bookworm:
1. Open "Screen Configuration"
2. Screen -> HDMI-1 -> Orientation -> Apply
After rotation, switch xmin/xmax/ymin/ymax accordingly.

Lite way (wayfire):
sudo nano .config/wayfire.ini
Add:
[output:HDMI-A-1]
mode = 480x320@60
transform = 270

Bullseye/Kali:
Check /boot/config.txt for:
dtoverlay=vc4-kms-v3d or dtoverlay=vc4-fkms-v3d

If enabled:
sudo nano /etc/xdg/lxsession/LXDE-pi/autostart
xrandr -o 1

If not enabled:
sudo nano /boot/config.txt
display_rotate=3

Ubuntu:
Check /boot/firmware/config.txt for vc4-kms/fkms line.
Then rotate in "Displays" app.
"""

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

        guide_frame = tk.Frame(self.main_frame, bg="white")
        guide_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        guide_scroll = tk.Scrollbar(guide_frame, orient="vertical")
        guide_scroll.pack(side="right", fill="y")

        guide_text = tk.Text(
            guide_frame,
            wrap="word",
            font=("Arial", 13),
            bg="white",
            fg="black",
            yscrollcommand=guide_scroll.set,
        )
        guide_text.pack(side="left", fill="both", expand=True)
        guide_scroll.config(command=guide_text.yview)
        guide_text.insert("1.0", USER_GUIDE_TEXT)
        guide_text.bind("<ButtonPress-1>", lambda e: guide_text.scan_mark(e.x, e.y))
        guide_text.bind("<B1-Motion>", lambda e: guide_text.scan_dragto(e.x, e.y, gain=1))
        guide_text.bind("<Key>", lambda e: "break")
        guide_text.bind("<<Paste>>", lambda e: "break")
        guide_text.bind("<<Cut>>", lambda e: "break")

    def update_datetime(self):
        if self.root.winfo_exists() and self.datetime_label and self.datetime_label.winfo_exists():
            now_text = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
            self.datetime_label.config(text=now_text)
            self.datetime_after_id = self.root.after(1000, self.update_datetime)

    def select_user(self, user: str):
        if self.selected_user_label:
            self.selected_user_label.config(text=f"Ausgewählt: {user}")

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

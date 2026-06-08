import socket
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import ttk

try:
    from gpiozero import MCP3008 as GPIOZERO_MCP3008
    MCP3008_IMPORT_ERROR = None
except Exception as exc:
    GPIOZERO_MCP3008 = None
    MCP3008_IMPORT_ERROR = exc

try:
    from gpiozero import OutputDevice as GPIOZERO_OutputDevice
    GPIO20_IMPORT_ERROR = None
except Exception as exc:
    GPIOZERO_OutputDevice = None
    GPIO20_IMPORT_ERROR = exc

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
    "Frage 1: Hat das Gehäuse Kratzer und mechanische Schäden am Gehäuse?",
    "Frage 2: Ist alles mechanisch angezogen/fest?",
    "Frage 3: Sind alle Stecker/Schalter und Geräte mit Label versehen?",
    "Frage 4: Leuchtet die Netzteil LED grün?",
    "Frage 5: Gefahren Label auf dem Gehäuse vorhanden?",
    "Frage 6: Sind Defekte an der Isolation oder Krimpungen zu erkennen?",
]
REPORT_FILENAME_PREFIX = "PSV_Test"
MCP3008_NUM_CHANNELS = 8
MCP3008_VREF = 3.3
MCP3008_UPDATE_MS = 150
MCP3008_ADC_MAX_VALUE = 1023
MCP3008_VOLTS_PER_BIT = MCP3008_VREF / MCP3008_ADC_MAX_VALUE
MCP3008_SAMPLES_PER_CHANNEL = 5
MCP3008_TRIMMED_SAMPLES_PER_SIDE = 1
# Gemessene Referenz: 24 V Eingang ergeben typischerweise raw 506.0-508.4.
MCP3008_CALIBRATION_INPUT_VOLTS = 24.0
MCP3008_CALIBRATION_RAW_LOW = 506.0
MCP3008_CALIBRATION_RAW_HIGH = 508.4
MCP3008_CALIBRATION_RAW_MIDPOINT = (MCP3008_CALIBRATION_RAW_LOW + MCP3008_CALIBRATION_RAW_HIGH) / 2
MCP3008_TARGET_DISPLAY_VOLTS = 24.0
MCP3008_TARGET_DISPLAY_TOLERANCE_PERCENT = 1.0
# Schnellere Annäherung nach Spannungswechsel: ansteigend schnell, abfallend noch schneller.
MCP3008_SMOOTHING_ALPHA_STABLE = 0.20
MCP3008_SMOOTHING_ALPHA_RISE = 0.55
MCP3008_SMOOTHING_ALPHA_FALL = 0.80
MCP3008_SMOOTHING_DEADBAND_RAW = 0.6
# Zustandsfenster aus Messwerten:
# <=0.006 V ADC: GND angeschlossen
# <=0.030 V ADC: Eingang offen / kein Signal
# 1.45-1.85 V ADC: entspricht 24 V Eingang nach Teiler/Kalibration
MCP3008_STATE_GND_ADC_MAX = 0.006
MCP3008_STATE_OPEN_ADC_MAX = 0.030
MCP3008_STATE_24V_ADC_MIN = 1.45
MCP3008_STATE_24V_ADC_MAX = 1.85
MCP3008_VISIBLE_CHANNELS_BY_CHIP = [
    list(range(MCP3008_NUM_CHANNELS)),  # MCP3008 #1: CH0-CH7
    [3, 4, 5, 6],  # MCP3008 #2: nur CH3-CH6 anzeigen
]
MCP3008_TARGET_CHANNELS_BY_CHIP = [
    list(range(MCP3008_NUM_CHANNELS)),  # MCP3008 #1: CH0-CH7
    [3, 4, 5, 6],  # MCP3008 #2: CH3-CH6
]
# Klartextbezeichnungen für Klemmen auf dem Anschluss X2
# MCP3008 #1: CH0=PIN 12 X2 ... CH7=PIN 5 X2
# MCP3008 #2: CH3=PIN 4 X2  ... CH6=PIN 1 X2
MCP3008_CHANNEL_PIN_LABELS = [
    {ch: f"PIN {12 - ch} X2" for ch in range(8)},
    {3: "PIN 4 X2", 4: "PIN 3 X2", 5: "PIN 2 X2", 6: "PIN 1 X2"},
]
MCP3008_CHANNEL_DISPLAY_CALIBRATIONS = {}
for chip_index, channels in enumerate(MCP3008_TARGET_CHANNELS_BY_CHIP):
    for channel in channels:
        MCP3008_CHANNEL_DISPLAY_CALIBRATIONS[(chip_index, channel)] = {
            "input_volts_per_raw": MCP3008_CALIBRATION_INPUT_VOLTS / MCP3008_CALIBRATION_RAW_MIDPOINT,
            "input_decimals": 2,
            "display_target_volts": MCP3008_TARGET_DISPLAY_VOLTS,
            "display_target_tolerance_percent": MCP3008_TARGET_DISPLAY_TOLERANCE_PERCENT,
            "smoothing_alpha_rise": MCP3008_SMOOTHING_ALPHA_RISE,
            "smoothing_alpha_fall": MCP3008_SMOOTHING_ALPHA_FALL,
            "smoothing_deadband_raw": MCP3008_SMOOTHING_DEADBAND_RAW,
        }
SOFT_SPI_CLK_PIN = 13
SOFT_SPI_MISO_PIN = 19
SOFT_SPI_MOSI_PIN = 26
MCP3008_SELECT_PINS = [5, 6]
GPIO20_OUTPUT_PIN = 20
WIFI_ICON_X_OFFSET = -15
WIFI_ICON_Y_OFFSET = 10
WIFI_ICON_SIZE = (64, 48)
WIFI_ARCS = [(8, 8, 56, 56), (16, 16, 48, 48), (24, 24, 40, 40)]
WIFI_DOT = (29, 35, 35, 41)
USER_BADGE_SPACING = 28
# Max text width (px) for question labels, tuned for 3.5" (480 px wide) display.
QUESTION_WRAPLENGTH = 450
MCP3008_TABLE_HEADER = f"{'PIN':<8}{'SPANNUNG':>12}{'STATUS':>12}"


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
        self.test_start_time: datetime | None = None
        self.question_answers: list[str] = []
        self.mcp_data_labels: list[tk.Label] = []
        self.mcp_after_id = None
        self.mcp_readers = None
        self.mcp_error_message = None
        self.mcp_smoothed_raw_values: dict[tuple[int, int], float] = {}
        self.mcp_status_label = None
        self.voltage_test_result: str | None = None
        self.voltage_test_lines: list[str] = []
        self.gpio20_output = None
        self.gpio20_button = None
        self.gpio20_status_label = None
        self.gpio20_error_message = None

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

        if self.mcp_after_id is not None:
            try:
                self.root.after_cancel(self.mcp_after_id)
            except tk.TclError:
                pass
            self.mcp_after_id = None

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
        self.mcp_data_labels = []
        self.mcp_smoothed_raw_values = {}
        self.mcp_status_label = None
        self.gpio20_button = None
        self.gpio20_status_label = None
        self.gpio20_error_message = None

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
            self.test_start_time = datetime.now()
            self.question_answers = []
            self.voltage_test_result = None
            self.voltage_test_lines = []
            self.show_question_screen(0)

    def _init_mcp_readers(self):
        if self.mcp_readers is not None:
            return
        if GPIOZERO_MCP3008 is None:
            self.mcp_error_message = f"MCP3008 nicht verfügbar: {MCP3008_IMPORT_ERROR}"
            return

        try:
            readers = []
            for select_pin in MCP3008_SELECT_PINS:
                chip_channels = []
                for channel in range(MCP3008_NUM_CHANNELS):
                    chip_channels.append(
                        GPIOZERO_MCP3008(
                            channel=channel,
                            clock_pin=SOFT_SPI_CLK_PIN,
                            mosi_pin=SOFT_SPI_MOSI_PIN,
                            miso_pin=SOFT_SPI_MISO_PIN,
                            select_pin=select_pin,
                        )
                    )
                readers.append(chip_channels)
            self.mcp_readers = readers
            self.mcp_error_message = None
        except Exception as exc:
            self.mcp_error_message = f"MCP3008 Initialisierung fehlgeschlagen: {exc}"

    def _init_gpio20_output(self):
        if self.gpio20_output is not None:
            return
        if GPIOZERO_OutputDevice is None:
            self.gpio20_error_message = f"GPIO 20 nicht verfügbar: {GPIO20_IMPORT_ERROR}"
            return

        try:
            self.gpio20_output = GPIOZERO_OutputDevice(GPIO20_OUTPUT_PIN, active_high=True, initial_value=False)
            self.gpio20_error_message = None
        except Exception as exc:
            self.gpio20_error_message = f"GPIO 20 Initialisierung fehlgeschlagen: {exc}"

    def set_gpio20_high(self):
        self._init_gpio20_output()

        if self.gpio20_error_message is not None:
            if self.gpio20_status_label:
                self.gpio20_status_label.config(text=self.gpio20_error_message, fg="red")
            return

        if self.gpio20_output is None:
            if self.gpio20_status_label:
                self.gpio20_status_label.config(text="GPIO 20 konnte nicht initialisiert werden.", fg="red")
            return

        try:
            self.gpio20_output.on()
            if self.gpio20_button:
                self.gpio20_button.config(state="disabled")
            if self.gpio20_status_label:
                self.gpio20_status_label.config(text="GPIO 20 ist jetzt HIGH (bis Programmende).", fg="green")
        except Exception as exc:
            if self.gpio20_status_label:
                self.gpio20_status_label.config(text=f"GPIO 20 konnte nicht gesetzt werden: {exc}", fg="red")

    def add_mcp_voltage_panel(self):
        self._init_mcp_readers()

        panel = tk.Frame(self.main_frame, bg="white")
        panel.pack(fill="both", expand=True, padx=10, pady=(6, 10))

        tk.Label(
            panel,
            text="X2 Spannungsübersicht",
            font=("Arial", 24, "bold"),
            fg="#0b3d91",
            bg="white",
        ).pack(pady=(4, 10))

        values_frame = tk.Frame(panel, bg="white")
        values_frame.pack(fill="both", expand=True, padx=2, pady=(0, 8))
        values_frame.columnconfigure(0, weight=1, uniform="mcp")
        values_frame.columnconfigure(1, weight=1, uniform="mcp")

        self.mcp_data_labels = []
        for idx, title in enumerate(("LINKE SEITE | PIN 1 - 6", "RECHTE SEITE | PIN 7 - 12")):
            card = tk.Frame(
                values_frame,
                bg="#f8fbff",
                highlightbackground="#b8c7d9",
                highlightthickness=2,
            )
            card.grid(row=0, column=idx, sticky="nsew", padx=6, pady=4)

            tk.Label(
                card,
                text=title,
                font=("Arial", 18, "bold"),
                fg="#0b3d91",
                bg="#f8fbff",
            ).pack(fill="x", padx=12, pady=(12, 8))

            label = tk.Label(
                card,
                text=f"{MCP3008_TABLE_HEADER}\n\nMessung läuft...",
                font=("Courier New", 18, "bold"),
                fg="#1d2a3a",
                bg="#eef4fb",
                justify="left",
                anchor="nw",
                padx=18,
                pady=16,
            )
            label.pack(fill="both", expand=True, padx=12, pady=(0, 12))
            self.mcp_data_labels.append(label)

        self.mcp_status_label = tk.Label(
            panel,
            text="Prüfung wird vorbereitet...",
            font=("Arial", 18, "bold"),
            fg="#1d2a3a",
            bg="white",
        )
        self.mcp_status_label.pack(pady=(2, 8))

        tk.Label(
            panel,
            text=f"Sollwert: {MCP3008_TARGET_DISPLAY_VOLTS:.2f} V   |   Toleranz: ±{MCP3008_TARGET_DISPLAY_TOLERANCE_PERCENT:.1f}%",
            font=("Arial", 16, "bold"),
            fg="#264b73",
            bg="white",
        ).pack(pady=(0, 2))

        self.update_mcp_voltage_panel()

    def _get_filtered_mcp_raw_average(self, adc):
        raw_values = [adc.raw_value for _ in range(MCP3008_SAMPLES_PER_CHANNEL)]
        raw_values.sort()
        max_trim_count = max(0, (len(raw_values) - 1) // 2)
        trim_count = min(MCP3008_TRIMMED_SAMPLES_PER_SIDE, max_trim_count)
        if trim_count > 0:
            raw_values = raw_values[trim_count:-trim_count]
        return sum(raw_values) / len(raw_values)

    def _get_mcp_channel_measurement(self, chip_index: int, channel: int, avg_raw: float):
        adc_voltage = avg_raw * MCP3008_VOLTS_PER_BIT
        if adc_voltage <= MCP3008_STATE_GND_ADC_MAX:
            input_state = "GND"
        elif adc_voltage <= MCP3008_STATE_OPEN_ADC_MAX:
            input_state = "OFFEN"
        elif MCP3008_STATE_24V_ADC_MIN <= adc_voltage <= MCP3008_STATE_24V_ADC_MAX:
            input_state = "24V"
        else:
            input_state = "ZWISCHEN"
        calibration = MCP3008_CHANNEL_DISPLAY_CALIBRATIONS.get((chip_index, channel))
        if calibration is None:
            return {
                "display_voltage": adc_voltage,
                "adc_voltage": adc_voltage,
                "raw_avg": avg_raw,
                "in_tolerance": True,
                "has_target": False,
                "input_state": input_state,
            }

        input_voltage = avg_raw * calibration["input_volts_per_raw"]
        display_target_volts = calibration.get("display_target_volts")
        display_target_tolerance_percent = calibration.get("display_target_tolerance_percent")
        in_tolerance = True
        if display_target_volts is not None and display_target_tolerance_percent is not None:
            tolerance_volts = abs(display_target_volts) * (abs(display_target_tolerance_percent) / 100.0)
            in_tolerance = abs(input_voltage - display_target_volts) <= tolerance_volts
            if in_tolerance:
                input_voltage = float(display_target_volts)
        return {
            "display_voltage": input_voltage,
            "adc_voltage": adc_voltage,
            "raw_avg": avg_raw,
            "in_tolerance": in_tolerance,
            "has_target": display_target_volts is not None and display_target_tolerance_percent is not None,
            "input_state": input_state,
        }

    def _get_smoothed_mcp_raw(self, chip_index: int, channel: int, raw_avg: float):
        calibration = MCP3008_CHANNEL_DISPLAY_CALIBRATIONS.get((chip_index, channel), {})
        alpha_rise = max(0.0, min(1.0, calibration.get("smoothing_alpha_rise", 1.0)))
        alpha_fall = max(0.0, min(1.0, calibration.get("smoothing_alpha_fall", alpha_rise)))
        deadband_raw = max(0.0, float(calibration.get("smoothing_deadband_raw", 0.0)))
        key = (chip_index, channel)
        previous = self.mcp_smoothed_raw_values.get(key)
        if previous is None:
            smoothed = raw_avg
        else:
            delta = raw_avg - previous
            if abs(delta) <= deadband_raw:
                alpha = MCP3008_SMOOTHING_ALPHA_STABLE
            else:
                alpha = alpha_rise if delta > 0 else alpha_fall
            smoothed = previous + (alpha * delta)
        self.mcp_smoothed_raw_values[key] = smoothed
        return smoothed

    def _get_pin_number_from_label(self, pin_label: str):
        parts = pin_label.split()
        for index, part in enumerate(parts):
            if part == "PIN" and index + 1 < len(parts):
                try:
                    return int(parts[index + 1])
                except ValueError:
                    return None
        return None

    def _get_measurement_status_text(self, measurement):
        input_state = measurement.get("input_state")
        if input_state == "GND":
            return "GND/0V"
        if input_state == "OFFEN":
            return "NC"
        if input_state == "24V":
            return "HIGH"
        return "UNKLAR"

    def _collect_mcp_measurements(self):
        if self.mcp_error_message is not None or not self.mcp_readers:
            return None

        measurements = []
        for idx, chip_channels in enumerate(self.mcp_readers):
            visible_channels = (
                MCP3008_VISIBLE_CHANNELS_BY_CHIP[idx]
                if idx < len(MCP3008_VISIBLE_CHANNELS_BY_CHIP)
                else list(range(MCP3008_NUM_CHANNELS))
            )
            chip_measurements = []
            for channel in visible_channels:
                adc = chip_channels[channel]
                avg_raw = self._get_filtered_mcp_raw_average(adc)
                smoothed_raw = self._get_smoothed_mcp_raw(idx, channel, avg_raw)
                measurement = self._get_mcp_channel_measurement(idx, channel, smoothed_raw)
                chip_measurements.append((channel, measurement))
            measurements.append(chip_measurements)
        return measurements

    def update_mcp_voltage_panel(self):
        if not self.mcp_data_labels:
            return

        if self.mcp_error_message is not None:
            self.mcp_data_labels[0].config(text=self.mcp_error_message, fg="red")
            for label in self.mcp_data_labels[1:]:
                label.config(text="")
            if self.mcp_status_label:
                self.mcp_status_label.config(text="Spannungstest: FEHLER", fg="red")
        elif not self.mcp_readers:
            self.mcp_data_labels[0].config(text="MCP3008 nicht initialisiert.", fg="red")
            for label in self.mcp_data_labels[1:]:
                label.config(text="")
            if self.mcp_status_label:
                self.mcp_status_label.config(text="Spannungstest: FEHLER", fg="red")
        else:
            try:
                measurements = self._collect_mcp_measurements()
                overall_voltage_pass = True
                measurements_by_pin = {}
                for idx, chip_measurements in enumerate(measurements or []):
                    pin_map = (
                        MCP3008_CHANNEL_PIN_LABELS[idx]
                        if idx < len(MCP3008_CHANNEL_PIN_LABELS)
                        else {}
                    )
                    for channel, measurement in chip_measurements:
                        pin_label = pin_map.get(channel, f"CH{channel}")
                        pin_number = self._get_pin_number_from_label(pin_label)
                        if pin_number is not None:
                            measurements_by_pin[pin_number] = measurement
                        if measurement["has_target"] and not measurement["in_tolerance"]:
                            overall_voltage_pass = False

                for label_index, pin_numbers in enumerate((range(1, 7), range(7, 13))):
                    lines = [MCP3008_TABLE_HEADER]
                    for pin_number in pin_numbers:
                        measurement = measurements_by_pin.get(pin_number)
                        if measurement is None:
                            lines.append(f"{f'PIN {pin_number}':<8}{'--.-- V':>12}{'---':>12}")
                            continue
                        status_text = self._get_measurement_status_text(measurement)
                        lines.append(
                            f"{f'PIN {pin_number}':<8}{f'{measurement['display_voltage']:.2f} V':>12}{status_text:>12}"
                        )
                    self.mcp_data_labels[label_index].config(text="\n".join(lines), fg="#1d2a3a")

                if self.mcp_status_label:
                    status_text = "PASS" if overall_voltage_pass else "FAIL"
                    status_color = "green" if overall_voltage_pass else "red"
                    self.mcp_status_label.config(text=f"Aktueller Spannungstest: {status_text}", fg=status_color)
            except Exception as exc:
                self.mcp_data_labels[0].config(text=f"Messfehler: {exc}", fg="red")
                for label in self.mcp_data_labels[1:]:
                    label.config(text="")
                if self.mcp_status_label:
                    self.mcp_status_label.config(text="Spannungstest: FEHLER", fg="red")

        if self.root.winfo_exists():
            self.mcp_after_id = self.root.after(MCP3008_UPDATE_MS, self.update_mcp_voltage_panel)

    def _evaluate_voltage_test(self):
        if self.mcp_error_message is not None:
            return "FAIL", [self.mcp_error_message]
        if not self.mcp_readers:
            return "FAIL", ["MCP3008 nicht initialisiert."]

        measurements = self._collect_mcp_measurements()
        if measurements is None:
            return "FAIL", ["Keine Messdaten verfügbar."]

        lines = []
        overall_voltage_pass = True
        for chip_index, chip_measurements in enumerate(measurements):
            for channel, measurement in chip_measurements:
                if not measurement["has_target"]:
                    continue
                status = "PASS" if measurement["in_tolerance"] else "FAIL"
                lines.append(
                    f"MCP3008 #{chip_index + 1} CH{channel}: {measurement['display_voltage']:.2f} V ({status})"
                )
                if not measurement["in_tolerance"]:
                    overall_voltage_pass = False

        if not lines:
            return "FAIL", ["Keine Zielkanäle für den Spannungstest konfiguriert."]
        return ("PASS" if overall_voltage_pass else "FAIL"), lines

    def show_question_screen(self, question_index: int):
        if question_index >= len(QUESTION_TEXTS):
            self.show_voltage_test_screen()
            return

        self.clear_screen()

        # Header: Datum links | User mittig | WLAN rechts
        header = tk.Frame(self.main_frame, bg="white")
        header.pack(fill="x", padx=4, pady=2)
        header.columnconfigure(0, weight=1)
        header.columnconfigure(1, weight=1)
        header.columnconfigure(2, weight=0)

        self.datetime_label = tk.Label(
            header,
            text="",
            font=("Arial", 16, "bold"),
            fg="black",
            bg="white",
            anchor="w",
        )
        self.datetime_label.grid(row=0, column=0, sticky="w")
        self.update_datetime()

        selected_user_text = self.selected_user if self.selected_user else "Unbekannt"
        tk.Label(
            header,
            text=f"User: {selected_user_text}",
            font=("Arial", 16, "bold"),
            fg="black",
            bg="white",
            anchor="center",
        ).grid(row=0, column=1)

        self.wifi_canvas = tk.Canvas(
            header,
            width=WIFI_ICON_SIZE[0],
            height=WIFI_ICON_SIZE[1],
            bg="white",
            highlightthickness=0,
        )
        self.wifi_canvas.grid(row=0, column=2, sticky="e")
        self.draw_wifi_icon("green" if self.connected else "red")

        tk.Label(
            self.main_frame,
            text="Prüffragen",
            font=("Arial", 18, "bold"),
            fg="black",
            bg="white",
        ).pack(pady=(4, 4))

        tk.Label(
            self.main_frame,
            text=QUESTION_TEXTS[question_index],
            font=("Arial", 30, "bold"),
            fg="black",
            bg="white",
            wraplength=QUESTION_WRAPLENGTH,
            justify="center",
        ).pack(padx=8, pady=8)

        button_frame = tk.Frame(self.main_frame, bg="white")
        button_frame.pack(pady=10)

        tk.Button(
            button_frame,
            text="PASS",
            font=("Arial", 20, "bold"),
            width=10,
            height=2,
            bg="#d9f7d9",
            activebackground="#bdeebd",
            command=lambda: self.on_question_pass(question_index),
        ).grid(row=0, column=0, padx=10)

        tk.Button(
            button_frame,
            text="FAIL",
            font=("Arial", 20, "bold"),
            width=10,
            height=2,
            bg="#ffd9d9",
            activebackground="#ffc0c0",
            command=lambda: self.on_question_fail(question_index),
        ).grid(row=0, column=1, padx=10)

        self.question_result_label = tk.Label(
            self.main_frame,
            text="",
            font=("Arial", 12, "bold"),
            fg="red",
            bg="white",
        )
        self.question_result_label.pack(pady=4)

    def on_question_pass(self, current_index: int):
        self.question_answers.append("PASS")
        next_index = current_index + 1
        if next_index >= len(QUESTION_TEXTS):
            self.show_voltage_test_screen()
            return
        self.show_question_screen(next_index)

    def on_question_fail(self, current_index: int):
        self.question_answers.append("FAIL")
        next_index = current_index + 1
        if next_index >= len(QUESTION_TEXTS):
            self.show_voltage_test_screen()
            return
        self.show_question_screen(next_index)

    def show_voltage_test_screen(self):
        self.clear_screen()

        header = tk.Frame(self.main_frame, bg="white")
        header.pack(fill="x", padx=4, pady=2)
        header.columnconfigure(0, weight=1)
        header.columnconfigure(1, weight=1)
        header.columnconfigure(2, weight=0)

        self.datetime_label = tk.Label(
            header,
            text="",
            font=("Arial", 16, "bold"),
            fg="black",
            bg="white",
            anchor="w",
        )
        self.datetime_label.grid(row=0, column=0, sticky="w")
        self.update_datetime()

        selected_user_text = self.selected_user if self.selected_user else "Unbekannt"
        tk.Label(
            header,
            text=f"User: {selected_user_text}",
            font=("Arial", 16, "bold"),
            fg="black",
            bg="white",
            anchor="center",
        ).grid(row=0, column=1)

        self.wifi_canvas = tk.Canvas(
            header,
            width=WIFI_ICON_SIZE[0],
            height=WIFI_ICON_SIZE[1],
            bg="white",
            highlightthickness=0,
        )
        self.wifi_canvas.grid(row=0, column=2, sticky="e")
        self.draw_wifi_icon("green" if self.connected else "red")

        tk.Label(
            self.main_frame,
            text="X2 I/O Test",
            font=("Arial", 22, "bold"),
            fg="#0b3d91",
            bg="white",
            anchor="center",
            justify="center",
        ).pack(fill="x", pady=(8, 2))

        self.add_mcp_voltage_panel()

        gpio20_frame = tk.Frame(self.main_frame, bg="white")
        gpio20_frame.pack(fill="x", pady=(4, 2))

        self.gpio20_button = tk.Button(
            gpio20_frame,
            text="GPIO 20 HIGH",
            font=("Arial", 18, "bold"),
            bg="#fff2cc",
            activebackground="#ffe599",
            padx=16,
            pady=8,
            command=self.set_gpio20_high,
        )
        self.gpio20_button.pack()

        self.gpio20_status_label = tk.Label(
            gpio20_frame,
            text="",
            font=("Arial", 14, "bold"),
            fg="#1d2a3a",
            bg="white",
        )
        self.gpio20_status_label.pack(pady=(6, 0))

        tk.Button(
            self.main_frame,
            text="Weiter zum Gesamtergebnis",
            font=("Arial", 18, "bold"),
            bg="#d8ebff",
            activebackground="#c3defa",
            padx=16,
            pady=8,
            command=self.finish_voltage_test,
        ).pack(pady=(6, 10))

    def finish_voltage_test(self):
        voltage_result, voltage_lines = self._evaluate_voltage_test()
        self.voltage_test_result = voltage_result
        self.voltage_test_lines = voltage_lines
        self.show_final_result_screen()

    def show_final_result_screen(self):
        self.clear_screen()
        self.add_wifi_icon()

        test_end_time = datetime.now()
        overall = self._generate_report(test_end_time)
        result_color = "green" if overall == "PASS" else "red"
        voltage_color = "green" if self.voltage_test_result == "PASS" else "red"

        tk.Label(
            self.main_frame,
            text="Test abgeschlossen",
            font=("Arial", 24, "bold"),
            fg="#0b3d91",
            bg="white",
        ).pack(pady=(40, 12))
        tk.Label(
            self.main_frame,
            text=f"Fragen: {'PASS' if self.question_answers and all(a == 'PASS' for a in self.question_answers) else 'FAIL'}",
            font=("Arial", 18, "bold"),
            fg="green" if self.question_answers and all(a == "PASS" for a in self.question_answers) else "red",
            bg="white",
        ).pack(pady=4)
        tk.Label(
            self.main_frame,
            text=f"Spannungstest: {self.voltage_test_result or 'FAIL'}",
            font=("Arial", 18, "bold"),
            fg=voltage_color,
            bg="white",
        ).pack(pady=4)
        tk.Label(
            self.main_frame,
            text=f"Gesamtergebnis: {overall}",
            font=("Arial", 32, "bold"),
            fg=result_color,
            bg="white",
        ).pack(pady=(12, 20))

    def _generate_report(self, end_time: datetime) -> str:
        """Write a TXT report to the desktop and return the overall result string."""
        questions_pass = bool(self.question_answers) and all(a == "PASS" for a in self.question_answers)
        voltage_pass = self.voltage_test_result == "PASS"
        overall = "PASS" if questions_pass and voltage_pass else "FAIL"

        desktop = Path.home() / "Desktop"
        desktop.mkdir(parents=True, exist_ok=True)

        start_str = (
            self.test_start_time.strftime("%Y%m%d_%H%M%S")
            if self.test_start_time
            else "unbekannt"
        )
        filename = f"{REPORT_FILENAME_PREFIX}_{start_str}_{overall}.txt"
        filepath = desktop / filename

        with open(filepath, "w", encoding="utf-8") as f:
            f.write("PSV Testprotokoll\n")
            f.write("=" * 45 + "\n")
            f.write(f"Tester:        {self.selected_user or 'Unbekannt'}\n")
            f.write(
                f"Testbeginn:    "
                + (
                    self.test_start_time.strftime("%d.%m.%Y %H:%M:%S")
                    if self.test_start_time
                    else "unbekannt"
                )
                + "\n"
            )
            f.write(f"Testende:      {end_time.strftime('%d.%m.%Y %H:%M:%S')}\n")
            f.write("=" * 45 + "\n\n")
            f.write("Prüffragen:\n\n")
            for i, (question, answer) in enumerate(
                zip(QUESTION_TEXTS, self.question_answers), 1
            ):
                f.write(f"  {question}\n")
                f.write(f"  Ergebnis: {answer}\n\n")
            f.write("Spannungstest:\n")
            f.write(f"  Ergebnis: {self.voltage_test_result or 'FAIL'}\n")
            for line in self.voltage_test_lines:
                f.write(f"  {line}\n")
            f.write("\n")
            f.write("=" * 45 + "\n")
            f.write(f"Gesamtergebnis: {overall}\n")

        return overall

    def on_close(self):
        if self.monitor_after_id is not None:
            try:
                self.root.after_cancel(self.monitor_after_id)
            except tk.TclError:
                pass
            self.monitor_after_id = None
        if self.gpio20_output is not None:
            try:
                self.gpio20_output.off()
            except Exception:
                pass
            try:
                self.gpio20_output.close()
            except Exception:
                pass
            self.gpio20_output = None
        self.clear_screen()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = TestprogrammApp(root)
    root.mainloop()

import io
import math
import random
import shutil
import struct
import subprocess
import threading
import wave

from textual.app import App, ComposeResult, SystemCommand
from textual.binding import Binding
from textual.containers import Container
from textual.reactive import reactive
from textual.screen import Screen
from textual.widgets import Static


TRANSLATIONS = {
    "de": {
        "lang_name": "Deutsch",
        "phases": {
            "BEREIT": "BEREIT",
            "READY": "BEREIT MACHEN",
            "ZAZEN": "ZAZEN",
            "KINHIN": "KINHIN",
            "ZAZEN II": "ZAZEN II",
            "FERTIG": "FERTIG",
        },
        "anim": "Anim",
        "anim_on": "Spirale",
        "anim_off": "Pur",
        "sound": "Ton",
        "sounds": ["Schale", "Glocke", "System", "Aus"],
        "displays": ["Balken", "Zahlen", "Pur"],
        "pause": " (Pause)",
        "sched_ready": "Ready",
        "sched_zazen": "Zazen",
        "sched_kinhin": "Kinhin",
        "hints": (
            "space: start/pause  ↑/↓: ±5m  ←/→: ±1m  p: ready  k: kinhin  2: 2.runde\n"
            "a: spirale  t: anzeige  s: ton  c: koan  l: sprache  ctrl+p: menü  q: quit"
        ),
        "koans": [
            "„Wie klingt das Klatschen einer einzelnen Hand?“",
            "„Welches Gesicht hattest du, bevor deine Eltern geboren wurden?“",
            "„Wenn du den Buddha triffst, töte ihn.“",
            "„Der Weg ist nicht im Himmel; der Weg ist im Herzen.“",
            "„Sitzend in Stille, nichts tuend, kommt der Frühling und das Gras wächst von selbst.“",
            "„Nicht der Wind bewegt sich, nicht die Fahne bewegt sich – euer Geist bewegt sich.“",
            "„Trinke deinen Tee.“",
            "„Ein Tag ohne Arbeit ist ein Tag ohne Essen.“",
            "„Form ist Leere, Leere ist Form.“",
            "„Der Hindernis-Stein auf dem Weg wird selbst zum Weg.“",
        ],
    },
    "en": {
        "lang_name": "English",
        "phases": {
            "BEREIT": "IDLE",
            "READY": "GET READY",
            "ZAZEN": "ZAZEN",
            "KINHIN": "KINHIN",
            "ZAZEN II": "ZAZEN II",
            "FERTIG": "COMPLETE",
        },
        "anim": "Anim",
        "anim_on": "Spiral",
        "anim_off": "None",
        "sound": "Sound",
        "sounds": ["Bowl", "Bell", "System", "Mute"],
        "displays": ["Bar", "Digits", "Pure"],
        "pause": " (Paused)",
        "sched_ready": "Ready",
        "sched_zazen": "Zazen",
        "sched_kinhin": "Kinhin",
        "hints": (
            "space: start/pause  ↑/↓: ±5m  ←/→: ±1m  p: ready  k: kinhin  2: 2nd round\n"
            "a: spiral  t: display  s: sound  c: koan  l: lang  ctrl+p: palette  q: quit"
        ),
        "koans": [
            "“What is the sound of one hand clapping?”",
            "“What was your original face before your parents were born?”",
            "“If you meet the Buddha on the road, kill him.”",
            "“Sitting quietly, doing nothing, spring comes, and the grass grows by itself.”",
            "“Not the wind, not the flag is moving; it is your mind that moves.”",
            "“Drink your tea.”",
            "“A day without work is a day without eating.”",
            "“Form is emptiness, emptiness is form.”",
            "“The obstacle in the path becomes the path.”",
            "“Before enlightenment, chop wood, carry water. After enlightenment, chop wood, carry water.”",
        ],
    },
    "jp": {
        "lang_name": "日本語 (Zen)",
        "phases": {
            "BEREIT": "待機 (Taiki)",
            "READY": "調身 (Chōshin)",
            "ZAZEN": "坐禅 (Zazen)",
            "KINHIN": "経行 (Kinhin)",
            "ZAZEN II": "坐禅 二 (Zazen II)",
            "FERTIG": "円成 (Enjō)",
        },
        "anim": "図",
        "anim_on": "螺旋",
        "anim_off": "無",
        "sound": "音",
        "sounds": ["磬子", "鐘", "システム", "無音"],
        "displays": ["線", "数字", "無"],
        "pause": " (一時停止)",
        "sched_ready": "調身",
        "sched_zazen": "坐禅",
        "sched_kinhin": "経行",
        "hints": (
            "space: 開始/停止  ↑/↓: ±5分  ←/→: ±1分  p: 調身  k: 経行  2: 二坐\n"
            "a: 螺旋  t: 表示  s: 音  c: 公案  l: 言語  ctrl+p: コマンド  q: 終了"
        ),
        "koans": [
            "「隻手の音声（せきしゅのおんじょう）」— 片手の拍手の音とは何か。",
            "「父母未生以前の本来の面目」— 父母が生まれる前の本来の姿とは。",
            "「逢仏殺仏、逢祖殺祖」— 仏に逢えば仏を殺せ。",
            "「春来草自生」— 春来たりて草おのずから生ず。",
            "「喫茶去（きっさこ）」— まあ、お茶を一杯飲みなさい。",
            "「一日不作一日不食」— 一日作さざれば一日食らわず。",
            "「色即是空、空即是色」— 形あるものは空であり、空は形である。",
            "「行雲流水（こううんりゅうすい）」— 行く雲のように、流れる水のように。",
            "「日々是好日（にちにちこれこうじつ）」— 毎日がかけがえのない良き日である。",
            "「知足（ちそく）」— 足るを知る者は富む。",
        ],
    },
}


def generate_singing_bowl_wav(freq: float = 196.0, duration: float = 4.0) -> bytes:
    """Generiert eine weiche Klangschale (Sinus + Obertöne + Fade-Out) im Speicher."""
    sample_rate = 44100
    num_samples = int(sample_rate * duration)
    buf = io.BytesIO()

    with wave.open(buf, "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)

        frames = bytearray()
        for i in range(num_samples):
            t = i / sample_rate
            attack = min(1.0, t / 0.03)
            decay = math.exp(-1.4 * t)
            envelope = attack * decay

            sample = (
                0.60 * math.sin(2 * math.pi * freq * t)
                + 0.25 * math.sin(2 * math.pi * (freq * 2.756) * t) * math.exp(-2.2 * t)
                + 0.15 * math.sin(2 * math.pi * (freq * 5.404) * t) * math.exp(-3.5 * t)
            )
            value = int(max(-32767, min(32767, sample * envelope * 26000)))
            frames.extend(struct.pack("<h", value))

        wav_file.writeframes(frames)

    return buf.getvalue()


class ZenApp(App):
    """Kompakte Zen-TUI im Dracula-Theme mit Debian-Spirale, Kinhin und Command-Palette."""

    CSS = """
    Screen {
        background: #282a36;
        color: #f8f8f2;
        align: center middle;
        transition: background 700ms out_cubic;
    }

    Screen.visual-bell {
        background: #44475a;
    }

    #main-box {
        width: 62;
        height: 24;
        align: center middle;
        background: #282a36;
    }

    Static {
        background: #282a36;
    }

    #app-title {
        height: 1;
        width: 100%;
        content-align: center middle;
        color: #ff79c6;
        text-style: bold;
        margin-bottom: 1;
    }

    #header-info {
        height: 1;
        width: 100%;
        content-align: center middle;
        color: #bd93f9;
        transition: opacity 800ms;
    }

    #schedule-info {
        height: 1;
        width: 100%;
        content-align: center middle;
        color: #6272a4;
        transition: opacity 800ms;
    }

    #canvas {
        height: 11;
        width: 100%;
        content-align: center middle;
        margin: 1 0;
    }

    #timer-display {
        height: 1;
        width: 100%;
        content-align: center middle;
        color: #8be9fd;
    }

    #koan-box {
        height: 2;
        width: 100%;
        content-align: center middle;
        color: #f1fa8c;
        text-style: italic;
        margin-top: 1;
        transition: opacity 800ms;
    }

    #footer-hints {
        height: 2;
        width: 100%;
        content-align: center middle;
        color: #6272a4;
        margin-top: 1;
        transition: opacity 800ms;
    }

    .dimmed {
        opacity: 0.12;
    }

    .hidden-running {
        opacity: 0.0;
    }
    """

    BINDINGS = [
        Binding("space", "toggle_timer", "Start/Pause", show=False),
        Binding("up", "adjust_zazen(300)", "+5 Min", show=False),
        Binding("down", "adjust_zazen(-300)", "-5 Min", show=False),
        Binding("right", "adjust_zazen(60)", "+1 Min", show=False),
        Binding("left", "adjust_zazen(-60)", "-1 Min", show=False),
        Binding("p", "cycle_prep", "Vorbereitung / Ready", show=False),
        Binding("k", "cycle_kinhin", "Kinhin", show=False),
        Binding("2", "toggle_second_zazen", "2. Runde Zazen", show=False),
        Binding("a", "toggle_animation", "Animation", show=False),
        Binding("t", "cycle_display", "Anzeige", show=False),
        Binding("s", "cycle_sound", "Klang", show=False),
        Binding("c", "next_koan", "Neues Koan", show=False),
        Binding("l", "cycle_language", "Sprache / Language", show=False),
        Binding("r", "reset_timer", "Reset", show=False),
        Binding("q", "quit", "Beenden", show=False),
    ]

    lang = reactive("de")
    is_running = reactive(False)
    prep_mins = reactive(1)
    zazen_mins = reactive(20)
    kinhin_mins = reactive(0)
    second_zazen = reactive(True)

    current_stage_total = reactive(20 * 60)
    remaining = reactive(20 * 60)
    phase = reactive("BEREIT")

    anim_enabled = reactive(True)
    display_mode = reactive(0)
    sound_mode = reactive(0)

    KINHIN_OPTIONS = (0, 5, 10, 15)
    LANG_ORDER = ("de", "en", "jp")

    def __init__(self):
        super().__init__()
        self.tick_count = 0
        self.ui_fade_timer = None
        self.koan_idx = random.randrange(len(TRANSLATIONS["de"]["koans"]))
        self.wav_bowl = generate_singing_bowl_wav(freq=196.0, duration=4.0)
        self.wav_bell = generate_singing_bowl_wav(freq=528.0, duration=2.8)
        self._sync_initial_time()

    @property
    def tr(self) -> dict:
        return TRANSLATIONS[self.lang]

    def get_system_commands(self, screen: Screen):
        """Fügt Sprach- und Zen-Befehle zur Textual Command Palette (Ctrl+P) hinzu."""
        yield from super().get_system_commands(screen)
        yield SystemCommand(
            "Sprache: Deutsch (DE)",
            "Oberfläche und Koans auf Deutsch umstellen",
            lambda: self.set_language("de"),
        )
        yield SystemCommand(
            "Language: English (EN)",
            "Switch interface and koans to English",
            lambda: self.set_language("en"),
        )
        yield SystemCommand(
            "言語: 日本語 / Zen (JP)",
            "表示と公案を日本語に切り替える",
            lambda: self.set_language("jp"),
        )
        yield SystemCommand(
            "Koan wechseln / Next Koan",
            "Ein neues zufälliges Zen-Koan anzeigen",
            self.action_next_koan,
        )

    def set_language(self, lang_code: str) -> None:
        if lang_code in TRANSLATIONS:
            self.lang = lang_code
            self._update_all_ui()

    def _sync_initial_time(self) -> None:
        if self.prep_mins > 0:
            self.current_stage_total = self.prep_mins * 60
        else:
            self.current_stage_total = self.zazen_mins * 60
        self.remaining = self.current_stage_total

    def compose(self) -> ComposeResult:
        with Container(id="main-box"):
            yield Static("Z E N", id="app-title")
            yield Static(id="header-info")
            yield Static(id="schedule-info")
            yield Static(id="canvas")
            yield Static(id="timer-display")
            yield Static(id="koan-box")
            yield Static(id="footer-hints")

    def on_mount(self) -> None:
        self.set_interval(0.1, self._on_tick)
        self._update_all_ui()

    def _on_tick(self) -> None:
        self.tick_count += 1

        if self.is_running and self.remaining > 0:
            if self.tick_count % 10 == 0:
                self.remaining -= 1
                if self.remaining == 0:
                    self._advance_phase()

        self._render_canvas()
        self._render_timer()

    def _advance_phase(self) -> None:
        if self.phase == "READY":
            self.trigger_bell()
            self.phase = "ZAZEN"
            self.current_stage_total = self.zazen_mins * 60
            self.remaining = self.current_stage_total
            self._update_headers()
            return

        if self.phase == "ZAZEN" and self.kinhin_mins > 0:
            self.trigger_bell()
            self.phase = "KINHIN"
            self.current_stage_total = self.kinhin_mins * 60
            self.remaining = self.current_stage_total
            self._update_headers()
            return

        if self.phase == "KINHIN" and self.second_zazen:
            self.trigger_bell()
            self.phase = "ZAZEN II"
            self.current_stage_total = self.zazen_mins * 60
            self.remaining = self.current_stage_total
            self._update_headers()
            return

        # Ende der gesamten Sitzung -> 3x Glocke
        self.trigger_triple_bell()
        self.is_running = False
        self.phase = "FERTIG"
        self.action_next_koan()
        self._set_ui_dimmed(False)
        self._update_headers()

    def trigger_bell(self) -> None:
        if self.sound_mode == 0:
            self._play_wav_async(self.wav_bowl)
        elif self.sound_mode == 1:
            self._play_wav_async(self.wav_bell)
        elif self.sound_mode == 2:
            self.bell()

        self.screen.add_class("visual-bell")
        self.set_timer(0.7, lambda: self.screen.remove_class("visual-bell"))

    def trigger_triple_bell(self) -> None:
        """Lässt Klangschale und Visual Bell zum Abschluss 3-mal ertönen."""
        self.trigger_bell()
        self.set_timer(1.8, self.trigger_bell)
        self.set_timer(3.6, self.trigger_bell)

    def _play_wav_async(self, wav_bytes: bytes) -> None:
        def worker():
            player = shutil.which("paplay") or shutil.which("aplay")
            if player:
                try:
                    proc = subprocess.Popen(
                        [player],
                        stdin=subprocess.PIPE,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                    proc.communicate(input=wav_bytes, timeout=6)
                    return
                except Exception:
                    pass
            self.call_from_thread(self.bell)

        threading.Thread(target=worker, daemon=True).start()

    def trigger_bell(self) -> None:
        if self.sound_mode == 0:
            self._play_wav_async(self.wav_bowl)
        elif self.sound_mode == 1:
            self._play_wav_async(self.wav_bell)
        elif self.sound_mode == 2:
            self.bell()

        self.screen.add_class("visual-bell")
        self.set_timer(0.7, lambda: self.screen.remove_class("visual-bell"))

    def _set_ui_dimmed(self, dimmed: bool) -> None:
        header = self.query_one("#header-info")
        schedule = self.query_one("#schedule-info")
        footer = self.query_one("#footer-hints")
        koan = self.query_one("#koan-box")

        if dimmed and self.is_running:
            header.add_class("dimmed")
            schedule.add_class("dimmed")
            footer.add_class("dimmed")
            koan.add_class("hidden-running")
        else:
            header.remove_class("dimmed")
            schedule.remove_class("dimmed")
            footer.remove_class("dimmed")
            koan.remove_class("hidden-running")

    def _schedule_ui_fade(self) -> None:
        self._set_ui_dimmed(False)
        if self.ui_fade_timer:
            self.ui_fade_timer.stop()
        if self.is_running:
            self.ui_fade_timer = self.set_timer(2.5, lambda: self._set_ui_dimmed(True))

    def on_key(self, event) -> None:
        if self.is_running:
            self._schedule_ui_fade()

    # --- Actions ---

    def action_toggle_timer(self) -> None:
        if self.phase == "FERTIG":
            self.action_reset_timer()
            return

        if not self.is_running:
            if self.phase == "BEREIT":
                if self.prep_mins > 0:
                    self.phase = "READY"
                    self.current_stage_total = self.prep_mins * 60
                    self.remaining = self.current_stage_total
                else:
                    self.phase = "ZAZEN"
                    self.current_stage_total = self.zazen_mins * 60
                    self.remaining = self.current_stage_total
                    self.trigger_bell()
            self.is_running = True
            self._schedule_ui_fade()
        else:
            self.is_running = False
            self._set_ui_dimmed(False)

        self._update_headers()

    def action_adjust_zazen(self, delta_seconds: int) -> None:
        if not self.is_running and self.phase in ("BEREIT", "FERTIG"):
            delta_mins = delta_seconds // 60
            self.zazen_mins = max(1, min(120, self.zazen_mins + delta_mins))
            self.phase = "BEREIT"
            self._sync_initial_time()
            self._update_all_ui()

    def action_cycle_prep(self) -> None:
        if not self.is_running and self.phase in ("BEREIT", "FERTIG"):
            self.prep_mins = (self.prep_mins + 1) % 6
            self.phase = "BEREIT"
            self._sync_initial_time()
            self._update_all_ui()

    def action_cycle_kinhin(self) -> None:
        if not self.is_running and self.phase in ("BEREIT", "FERTIG"):
            idx = self.KINHIN_OPTIONS.index(self.kinhin_mins)
            self.kinhin_mins = self.KINHIN_OPTIONS[(idx + 1) % len(self.KINHIN_OPTIONS)]
            self.phase = "BEREIT"
            self._update_headers()

    def action_toggle_second_zazen(self) -> None:
        if not self.is_running and self.phase in ("BEREIT", "FERTIG") and self.kinhin_mins > 0:
            self.second_zazen = not self.second_zazen
            self.phase = "BEREIT"
            self._update_headers()

    def action_toggle_animation(self) -> None:
        self.anim_enabled = not self.anim_enabled
        self._update_all_ui()

    def action_cycle_display(self) -> None:
        self.display_mode = (self.display_mode + 1) % 3
        self._render_timer()
        self._update_headers()

    def action_cycle_sound(self) -> None:
        self.sound_mode = (self.sound_mode + 1) % 4
        self._update_headers()
        if self.sound_mode == 0:
            self._play_wav_async(self.wav_bowl)
        elif self.sound_mode == 1:
            self._play_wav_async(self.wav_bell)
        elif self.sound_mode == 2:
            self.bell()

    def action_next_koan(self) -> None:
        total = len(self.tr["koans"])
        choices = [i for i in range(total) if i != self.koan_idx]
        self.koan_idx = random.choice(choices)
        self._update_koan()

    def action_cycle_language(self) -> None:
        idx = self.LANG_ORDER.index(self.lang)
        self.set_language(self.LANG_ORDER[(idx + 1) % len(self.LANG_ORDER)])

    def action_reset_timer(self) -> None:
        self.is_running = False
        self.phase = "BEREIT"
        self._sync_initial_time()
        self._set_ui_dimmed(False)
        self._update_all_ui()

    # --- Rendering ---

    def _update_all_ui(self) -> None:
        self._update_headers()
        self._render_canvas()
        self._render_timer()
        self._update_koan()
        self.query_one("#footer-hints", Static).update(self.tr["hints"])

    def _update_koan(self) -> None:
        koans = self.tr["koans"]
        self.query_one("#koan-box", Static).update(koans[self.koan_idx % len(koans)])

    def _update_headers(self) -> None:
        t = self.tr
        phase_label = t["phases"][self.phase]
        anim_str = t["anim_on"] if self.anim_enabled else t["anim_off"]
        sound_str = t["sounds"][self.sound_mode]
        status_header = f"[bold]{phase_label}[/]  •  {t['anim']}: {anim_str}  •  {t['sound']}: {sound_str}"
        self.query_one("#header-info", Static).update(status_header)

        parts = []
        if self.prep_mins > 0:
            parts.append(f"{t['sched_ready']} {self.prep_mins}m")
        parts.append(f"{t['sched_zazen']} {self.zazen_mins}m")
        if self.kinhin_mins > 0:
            parts.append(f"{t['sched_kinhin']} {self.kinhin_mins}m")
            if self.second_zazen:
                parts.append(f"{t['sched_zazen']} {self.zazen_mins}m")
        self.query_one("#schedule-info", Static).update(" → ".join(parts))

    def _render_timer(self) -> None:
        widget = self.query_one("#timer-display", Static)
        if self.display_mode == 2:
            widget.update("")
            return

        if self.display_mode == 1:
            mins, secs = divmod(self.remaining, 60)
            status = "" if self.is_running else self.tr["pause"]
            color = "#ffb86c" if self.phase == "READY" else "#f8f8f2"
            widget.update(f"[{color}]{mins:02d}:{secs:02d}[/][#6272a4]{status}[/]")
            return

        width = 28
        progress = self.remaining / max(1, self.current_stage_total)
        filled = int(round(width * progress))
        bar_color = "#ffb86c" if self.phase == "READY" else "#bd93f9"
        bar = f"[{bar_color}]{'━' * filled}[/][#44475a]{'─' * (width - filled)}[/]"
        widget.update(bar)

    def _render_canvas(self) -> None:
        canvas = self.query_one("#canvas", Static)
        if not self.anim_enabled:
            canvas.update("")
            return
        canvas.update(self._draw_spiral())

    def _draw_spiral(self) -> str:
        """Offene, rotierende Debian-Spirale mit sanftem Dracula-Farbverlauf."""
        rows, cols = 11, 25
        cx, cy = cols // 2, rows // 2
        grid = [[{"char": " ", "weight": -1.0} for _ in range(cols)] for _ in range(rows)]

        speed = 0.04 if self.phase == "READY" else 0.08
        rotation = (self.tick_count * speed) if self.is_running else 0.4

        steps = 110
        max_theta = 3.35 * math.pi
        for i in range(steps):
            progress = i / steps
            theta = progress * max_theta
            radius = 0.6 + progress * 4.3

            angle = theta + rotation
            x = int(round(cx + math.cos(angle) * radius * 2.05))
            y = int(round(cy + math.sin(angle) * radius))

            if 0 <= x < cols and 0 <= y < rows:
                weight = 1.0 - progress
                if weight > grid[y][x]["weight"]:
                    if progress < 0.2:
                        ch = "●" if i < 4 else "◉"
                    elif progress < 0.55:
                        ch = "○"
                    elif progress < 0.8:
                        ch = "•"
                    else:
                        ch = "·"
                    grid[y][x] = {"char": ch, "weight": weight}

        lines = []
        for r in range(rows):
            line_parts = []
            for c in range(cols):
                cell = grid[r][c]
                w = cell["weight"]
                if w < 0:
                    line_parts.append(" ")
                elif w > 0.78:
                    head_color = "#ffb86c" if self.phase == "READY" else "#ff79c6"
                    line_parts.append(f"[{head_color}]{cell['char']}[/]")
                elif w > 0.55:
                    line_parts.append(f"[#bd93f9]{cell['char']}[/]")
                elif w > 0.32:
                    line_parts.append(f"[#8be9fd]{cell['char']}[/]")
                else:
                    line_parts.append(f"[#6272a4]{cell['char']}[/]")
            lines.append("".join(line_parts))

        return "\n".join(lines)


def main() -> None:
    app = ZenApp()
    app.run()


if __name__ == "__main__":
    main()

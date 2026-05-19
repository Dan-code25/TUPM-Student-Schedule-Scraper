import customtkinter as ctk
import threading
import json
from datetime import datetime
from pathlib import Path
from PIL import Image
from scraper import scrape_schedule

ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# Professional neutral palette with maroon accent
BG_PAGE = "#F3F4F6"
BG_SURFACE = "#FFFFFF"
BG_CARD = "#FCFCFD"
BORDER = "#E5E7EB"
ACCENT = "#7F1D1D"
ACCENT_HOVER = "#991B1B"
TEXT_PRIMARY = "#111827"
TEXT_SECONDARY = "#4B5563"
TEXT_MUTED = "#9CA3AF"
SUCCESS = "#059669"
ERROR = "#E11D48"

DAY_COLORS = {
    "Monday": "#2563EB",
    "Tuesday": "#7C3AED",
    "Wednesday": "#0891B2",
    "Thursday": "#D97706",
    "Friday": "#059669",
    "Saturday": "#DB2777",
    "Sunday": "#DC2626",
}


class SubjectCard(ctk.CTkFrame):
    def __init__(self, master, subject, **kwargs):
        super().__init__(
            master,
            fg_color=BG_SURFACE,
            corner_radius=14,
            border_width=1,
            border_color=BORDER,
            **kwargs,
        )
        self.pack(fill="x", padx=6, pady=8)

        day_color = DAY_COLORS.get(subject["day"], ACCENT)

        bar = ctk.CTkFrame(self, fg_color=day_color, corner_radius=0, width=6)
        bar.pack(side="left", fill="y", pady=1)
        bar.pack_propagate(False)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(side="left", fill="both", expand=True, padx=16, pady=12)

        row1 = ctk.CTkFrame(body, fg_color="transparent")
        row1.pack(fill="x")

        badge = ctk.CTkFrame(row1, fg_color=day_color, corner_radius=6, height=26)
        badge.pack(side="left")
        badge.pack_propagate(False)
        ctk.CTkLabel(
            badge,
            text=f"  {subject['code']}  ",
            font=("Segoe UI", 12, "bold"),
            text_color="#FFFFFF",
        ).pack(padx=3, pady=2)

        ctk.CTkLabel(
            row1,
            text=subject["description"],
            font=("Segoe UI", 15, "bold"),
            text_color=TEXT_PRIMARY,
            anchor="w",
        ).pack(side="left", padx=(10, 0), fill="x", expand=True)

        row2 = ctk.CTkFrame(body, fg_color="transparent")
        row2.pack(fill="x", pady=(10, 0))

        def chip(parent, label, value):
            chip_frame = ctk.CTkFrame(parent, fg_color=BG_CARD, corner_radius=8, border_width=1, border_color=BORDER)
            chip_frame.pack(side="left", padx=(0, 8))
            ctk.CTkLabel(
                chip_frame,
                text=f" {label}: {value} ",
                font=("Segoe UI", 11, "bold"),
                text_color=TEXT_SECONDARY,
            ).pack(padx=6, pady=3)

        chip(row2, "Time", subject["time"])
        chip(row2, "Day", subject["day"])
        chip(row2, "Room", subject["room"])

        divider = ctk.CTkFrame(body, fg_color=BORDER, height=1, corner_radius=0)
        divider.pack(fill="x", pady=(10, 8))

        ctk.CTkLabel(
            body,
            text=f"Faculty: {subject['faculty']}",
            font=("Segoe UI", 12, "bold"),
            text_color=TEXT_SECONDARY,
            anchor="w",
        ).pack(fill="x")


class StyledEntry(ctk.CTkEntry):
    def __init__(self, master, **kwargs):
        super().__init__(
            master,
            fg_color=BG_SURFACE,
            border_color=BORDER,
            border_width=1,
            text_color=TEXT_PRIMARY,
            placeholder_text_color=TEXT_MUTED,
            corner_radius=8,
            height=40,
            **kwargs,
        )


class ScheduleApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("TUPM Student Schedule Scraper")
        self.geometry("760x860")
        self.minsize(700, 760)
        self.configure(fg_color=BG_PAGE)

        self.current_schedule = []

        self._build_topbar()
        self._build_login_panel()
        self._load_saved_credentials()
        self._build_filter_panel()
        self._build_status()
        self._build_scroll_area()
        self._load_saved_schedule()

    def _friendly_error_message(self, raw_error):
        """Convert technical errors into clear, non-technical guidance."""
        if not raw_error:
            return "Something went wrong. Please try again."

        text = str(raw_error).strip()
        lowered = text.lower()

        if any(k in lowered for k in ["invalid", "incorrect", "wrong password", "unauthorized", "401", "403"]):
            return "Your login details look incorrect. Please check your Student ID, password, and birthdate."
        if any(k in lowered for k in ["timeout", "timed out", "connection", "network", "dns", "unreachable"]):
            return "We could not reach the school portal. Please check your internet connection and try again."
        if any(k in lowered for k in ["captcha", "blocked", "rate limit", "too many requests"]):
            return "The portal is temporarily busy. Please wait a moment, then try again."
        if any(k in lowered for k in ["no schedule", "not found", "empty"]):
            return "No schedule was found for this account right now."

        return "We couldn't fetch your schedule right now. Please verify your details and try again."

    def _build_topbar(self):
        shell = ctk.CTkFrame(self, fg_color=BG_SURFACE, corner_radius=0, height=72)
        shell.pack(fill="x")
        shell.pack_propagate(False)

        inner = ctk.CTkFrame(shell, fg_color="transparent")
        inner.place(relx=0.5, rely=0.5, anchor="center")

        try:
            logo_image = Image.open("tup_logo.png")
            logo_image = logo_image.resize((40, 40), Image.Resampling.LANCZOS)
            logo_photo = ctk.CTkImage(light_image=logo_image, dark_image=logo_image, size=(40, 40))
            logo = ctk.CTkLabel(inner, image=logo_photo, text="")
            logo.image = logo_photo
            logo.pack(side="left", padx=(0, 10))
        except Exception:
            ctk.CTkLabel(
                inner,
                text="TUP",
                font=("Segoe UI", 16, "bold"),
                text_color=ACCENT,
            ).pack(side="left", padx=(0, 10))

        ctk.CTkLabel(
            inner,
            text="TUPM Student Schedule Scraper",
            font=("Segoe UI", 20, "bold"),
            text_color=TEXT_PRIMARY,
        ).pack(side="left")

        ctk.CTkFrame(self, fg_color=ACCENT, height=3, corner_radius=0).pack(fill="x")

    def _build_login_panel(self):
        card = ctk.CTkFrame(
            self,
            fg_color=BG_CARD,
            corner_radius=14,
            border_width=1,
            border_color=BORDER,
        )
        card.pack(fill="x", padx=24, pady=(18, 0))

        ctk.CTkLabel(
            card,
            text="SIGN IN",
            font=("Segoe UI", 12, "bold"),
            text_color=ACCENT,
        ).pack(anchor="w", padx=18, pady=(14, 2))

        ctk.CTkLabel(
            card,
            text="Enter your TUP credentials to fetch your latest class schedule",
            font=("Segoe UI", 14),
            text_color=TEXT_SECONDARY,
        ).pack(anchor="w", padx=18, pady=(0, 12))

        form = ctk.CTkFrame(card, fg_color="transparent")
        form.pack(fill="x", padx=18, pady=(0, 16))

        for col in range(4):
            form.columnconfigure(col, weight=1)

        def field_label(text, col):
            ctk.CTkLabel(
                form,
                text=text,
                font=("Segoe UI", 11, "bold"),
                text_color=TEXT_MUTED,
            ).grid(row=0, column=col, sticky="w", padx=(0, 10), pady=(0, 4))

        field_label("STUDENT ID", 0)
        field_label("PASSWORD", 1)
        field_label("BIRTHDATE", 2)

        self.student_id = StyledEntry(form, placeholder_text="e.g. TUPM-XX-XXXX")
        self.student_id.grid(row=1, column=0, sticky="ew", padx=(0, 10))

        self.password = StyledEntry(form, placeholder_text="Password", show="*")
        self.password.grid(row=1, column=1, sticky="ew", padx=(0, 10))

        self.birthdate = StyledEntry(form, placeholder_text="MM/DD/YYYY")
        self.birthdate.grid(row=1, column=2, sticky="ew", padx=(0, 10))

        self.fetch_btn = ctk.CTkButton(
            form,
            text="Fetch",
            command=self.start_scraping,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            text_color="#FFFFFF",
            font=("Segoe UI", 14, "bold"),
            corner_radius=8,
            height=40,
            width=110,
        )
        self.fetch_btn.grid(row=1, column=3, sticky="ew")

        self.save_credentials_var = ctk.BooleanVar(value=False)
        self.save_credentials_checkbox = ctk.CTkCheckBox(
            card,
            text="Save credentials on this device",
            variable=self.save_credentials_var,
            font=("Segoe UI", 12),
            text_color=TEXT_SECONDARY,
            fg_color=ACCENT,
            hover_color=ACCENT_HOVER,
            border_color=BORDER,
            checkmark_color="#FFFFFF",
        )
        self.save_credentials_checkbox.pack(anchor="w", padx=20, pady=(0, 14))

    def _build_filter_panel(self):
        wrap = ctk.CTkFrame(self, fg_color="transparent")
        wrap.pack(fill="x", padx=24, pady=(16, 0))

        ctk.CTkLabel(
            wrap,
            text="FILTER BY DAY",
            font=("Segoe UI", 11, "bold"),
            text_color=TEXT_MUTED,
        ).pack(anchor="w", pady=(0, 6))

        self.filter_var = ctk.StringVar(value="All")
        days = ["All", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

        self.filter_bar = ctk.CTkSegmentedButton(
            wrap,
            values=days,
            variable=self.filter_var,
            command=self._on_filter,
            fg_color=BG_CARD,
            selected_color=ACCENT,
            selected_hover_color=ACCENT_HOVER,
            unselected_color=BG_CARD,
            unselected_hover_color=BG_SURFACE,
            text_color=TEXT_SECONDARY,
            font=("Segoe UI", 12, "bold"),
            corner_radius=8,
            height=34,
        )
        self.filter_bar.pack(fill="x")

        self._day_abbr = {
            "All": "All",
            "Mon": "Monday",
            "Tue": "Tuesday",
            "Wed": "Wednesday",
            "Thu": "Thursday",
            "Fri": "Friday",
            "Sat": "Saturday",
            "Sun": "Sunday",
        }

    def _on_filter(self, abbr):
        self.render_cards(self._day_abbr.get(abbr, abbr))

    def _build_status(self):
        self.status_label = ctk.CTkLabel(
            self,
            text="Enter credentials to fetch your schedule.",
            font=("Segoe UI", 12, "bold"),
            text_color=TEXT_MUTED,
        )
        self.status_label.pack(anchor="w", padx=28, pady=(14, 4))

        ctk.CTkFrame(self, fg_color=BORDER, height=1, corner_radius=0).pack(
            fill="x", padx=24, pady=(4, 0)
        )

    def _build_scroll_area(self):
        self.card_container = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=BORDER,
            scrollbar_button_hover_color=ACCENT,
        )
        self.card_container.pack(fill="both", expand=True, padx=20, pady=(10, 16))

    def _load_saved_schedule(self):
        schedules_dir = Path("saved_schedules")
        if not schedules_dir.exists():
            return

        files = sorted(
            schedules_dir.glob("tupm_student_schedule_*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not files:
            return

        try:
            with open(files[0], "r", encoding="utf-8") as f:
                self.current_schedule = json.load(f)

            self.status_label.configure(
                text=f"Loaded {len(self.current_schedule)} subjects from {files[0].name}",
                text_color=SUCCESS,
            )
            self.render_cards("All")
        except Exception as exc:
            self.status_label.configure(
                text=f"Error loading saved schedule: {exc}",
                text_color=ERROR,
            )

    def _credentials_file(self):
        return Path("saved_credentials.json")

    def _load_saved_credentials(self):
        credentials_file = self._credentials_file()
        if not credentials_file.exists():
            return

        try:
            with open(credentials_file, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception:
            return

        self.student_id.insert(0, data.get("student_id", ""))
        self.password.insert(0, data.get("password", ""))
        self.birthdate.insert(0, data.get("birthdate", ""))
        self.save_credentials_var.set(True)

    def _save_credentials(self, student_id, password, birthdate):
        payload = {
            "student_id": student_id,
            "password": password,
            "birthdate": birthdate,
        }
        with open(self._credentials_file(), "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

    def _clear_saved_credentials(self):
        credentials_file = self._credentials_file()
        if credentials_file.exists():
            credentials_file.unlink()

    def save_schedule(self, schedule, student_id):
        schedules_dir = Path("saved_schedules")
        schedules_dir.mkdir(exist_ok=True)

        for existing_file in schedules_dir.glob("tupm_student_schedule_*.json"):
            existing_file.unlink()

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = schedules_dir / f"tupm_student_schedule_{student_id}_{timestamp}.json"

        with open(filename, "w", encoding="utf-8") as f:
            json.dump(schedule, f, indent=2)

        return filename

    def start_scraping(self):
        self.fetch_btn.configure(state="disabled", text="Loading...")
        self.status_label.configure(
            text="Connecting to TUP ERS portal... (up to 25 seconds)",
            text_color=TEXT_SECONDARY,
        )

        for w in self.card_container.winfo_children():
            w.destroy()

        threading.Thread(target=self.run_scraper, daemon=True).start()

    def run_scraper(self):
        raw_id = self.student_id.get().strip()
        sid = raw_id.replace("@tup.edu.ph", "")
        pwd = self.password.get().strip()
        bdate = self.birthdate.get().strip()

        if self.save_credentials_var.get():
            self._save_credentials(sid, pwd, bdate)
        else:
            self._clear_saved_credentials()

        result = scrape_schedule(sid, pwd, bdate)

        if result["success"]:
            self.current_schedule = result["schedule"]
            saved_file = self.save_schedule(result["schedule"], sid)
            self.status_label.configure(
                text=f"Loaded {len(self.current_schedule)} subjects | Saved to {saved_file.name}",
                text_color=SUCCESS,
            )
            self.render_cards("All")
        else:
            self.current_schedule = []
            friendly_error = self._friendly_error_message(result.get("error"))
            self.status_label.configure(text=friendly_error, text_color=ERROR)

        self.fetch_btn.configure(state="normal", text="Fetch")

    def render_cards(self, selected_day):
        for w in self.card_container.winfo_children():
            w.destroy()

        if not self.current_schedule:
            return

        filtered = self.current_schedule
        if selected_day != "All":
            filtered = [s for s in self.current_schedule if s["day"] == selected_day]

        if not filtered:
            empty = ctk.CTkFrame(self.card_container, fg_color=BG_CARD, corner_radius=12)
            empty.pack(fill="x", padx=6, pady=20)
            ctk.CTkLabel(
                empty,
                text=f"No classes on {selected_day}",
                font=("Segoe UI", 16, "bold"),
                text_color=TEXT_SECONDARY,
            ).pack(pady=28)
            return

        stats = ctk.CTkFrame(self.card_container, fg_color="transparent")
        stats.pack(fill="x", padx=6, pady=(0, 8))

        ctk.CTkLabel(
            stats,
            text=f"{len(filtered)} subject{'s' if len(filtered) != 1 else ''}",
            font=("Segoe UI", 12, "bold"),
            text_color=TEXT_MUTED,
        ).pack(side="left")

        for subject in filtered:
            SubjectCard(self.card_container, subject=subject)


def run_app():
    app = ScheduleApp()
    app.mainloop()


if __name__ == "__main__":
    run_app()

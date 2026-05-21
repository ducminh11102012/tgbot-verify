"""Desktop GUI for direct SheerID verification with real-time logs."""
from __future__ import annotations

import json
import logging
import queue
import threading
import tkinter as tk
from tkinter import messagebox, ttk

from sheerid_cli import TARGETS, run_verification


class QueueLogHandler(logging.Handler):
    """Logging handler that forwards log records into a thread-safe queue."""

    def __init__(self, log_queue: "queue.Queue[str]"):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record: logging.LogRecord) -> None:
        self.log_queue.put(self.format(record))


class SheerIDApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("SheerID Verifier GUI")
        self.root.geometry("900x620")

        self.log_queue: "queue.Queue[str]" = queue.Queue()
        self.is_running = False

        self.target_var = tk.StringVar(value="spotify")
        self.url_var = tk.StringVar()

        self._build_ui()
        self._setup_logging()
        self._poll_logs()

    def _build_ui(self) -> None:
        frame = ttk.Frame(self.root, padding=12)
        frame.pack(fill=tk.BOTH, expand=True)

        ttk.Label(frame, text="Target").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            frame,
            textvariable=self.target_var,
            values=list(TARGETS.keys()),
            state="readonly",
            width=20,
        ).grid(row=0, column=1, sticky="w", padx=8)

        ttk.Label(frame, text="SheerID URL").grid(row=1, column=0, sticky="w", pady=(8, 0))
        ttk.Entry(frame, textvariable=self.url_var, width=95).grid(
            row=1, column=1, columnspan=2, sticky="ew", padx=8, pady=(8, 0)
        )

        self.run_button = ttk.Button(frame, text="Run Verification", command=self._on_run)
        self.run_button.grid(row=2, column=1, sticky="w", padx=8, pady=10)

        self.status_label = ttk.Label(frame, text="Status: Idle")
        self.status_label.grid(row=2, column=2, sticky="w")

        ttk.Label(frame, text="Logs").grid(row=3, column=0, sticky="nw", pady=(8, 0))
        self.log_text = tk.Text(frame, height=22, wrap=tk.WORD)
        self.log_text.grid(row=3, column=1, columnspan=2, sticky="nsew", padx=8, pady=(8, 0))
        scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=self.log_text.yview)
        scrollbar.grid(row=3, column=3, sticky="ns", pady=(8, 0))
        self.log_text.configure(yscrollcommand=scrollbar.set)

        frame.columnconfigure(1, weight=1)
        frame.columnconfigure(2, weight=1)
        frame.rowconfigure(3, weight=1)

    def _setup_logging(self) -> None:
        formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", "%H:%M:%S")
        queue_handler = QueueLogHandler(self.log_queue)
        queue_handler.setFormatter(formatter)

        root_logger = logging.getLogger()
        root_logger.setLevel(logging.INFO)
        root_logger.addHandler(queue_handler)

    def _append_log(self, text: str) -> None:
        self.log_text.insert(tk.END, text + "\n")
        self.log_text.see(tk.END)

    def _poll_logs(self) -> None:
        while True:
            try:
                line = self.log_queue.get_nowait()
            except queue.Empty:
                break
            self._append_log(line)
        self.root.after(120, self._poll_logs)

    def _on_run(self) -> None:
        if self.is_running:
            return

        url = self.url_var.get().strip()
        if not url:
            messagebox.showwarning("Missing URL", "Please paste a SheerID URL.")
            return

        self.is_running = True
        self.run_button.configure(state=tk.DISABLED)
        self.status_label.configure(text="Status: Running...")
        self._append_log("=" * 80)
        self._append_log(f"Starting verification for target={self.target_var.get()}")

        thread = threading.Thread(target=self._run_task, args=(self.target_var.get(), url), daemon=True)
        thread.start()

    def _run_task(self, target: str, url: str) -> None:
        try:
            result = run_verification(target, url)
            self.log_queue.put("Result JSON:\n" + json.dumps(result, ensure_ascii=False, indent=2))
            ok = bool(result.get("success"))
            self.root.after(0, lambda: self.status_label.configure(text=f"Status: {'Success' if ok else 'Failed'}"))
        except Exception as exc:
            self.log_queue.put(f"ERROR: {exc}")
            self.root.after(0, lambda: self.status_label.configure(text="Status: Error"))
        finally:
            self.root.after(0, self._finish_run)

    def _finish_run(self) -> None:
        self.is_running = False
        self.run_button.configure(state=tk.NORMAL)


def launch_gui() -> int:
    root = tk.Tk()
    SheerIDApp(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(launch_gui())

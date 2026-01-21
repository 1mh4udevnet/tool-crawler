import tkinter as tk
from tkinter import messagebox
import threading
import sys
import io
import os
import shutil

from app.crawler import run_crawler
from app.config import STATE_FILE, DATA_FILE, PICTURE_DIR
from app.cleanup import delete_image_and_related


# =========================
# Redirect stdout/stderr -> Text widget
# =========================
class TextRedirector(io.TextIOBase):
    def __init__(self, widget: tk.Text):
        self.widget = widget

    def write(self, s):
        self.widget.config(state="normal")
        self.widget.insert(tk.END, s)
        self.widget.see(tk.END)
        self.widget.config(state="disabled")

    def flush(self):
        pass


# =========================
# MAIN UI
# =========================
class ToolUI:
    def __init__(self, root):
        self.root = root
        root.title("Tool Cào + Tải ảnh")
        root.geometry("840x650")

        # ===== STATE =====
        self.running = False
        self.stop_requested = False

        # ===== INPUT =====
        frame = tk.Frame(root)
        frame.pack(pady=10)

        tk.Label(frame, text="Trang bắt đầu").grid(row=0, column=0, padx=5)
        self.start_entry = tk.Entry(frame, width=8)
        self.start_entry.grid(row=0, column=1, padx=5)

        tk.Label(frame, text="Trang kết thúc").grid(row=0, column=2, padx=5)
        self.end_entry = tk.Entry(frame, width=8)
        self.end_entry.grid(row=0, column=3, padx=5)

        self.run_btn = tk.Button(
            frame, text="Chạy",
            command=self.start_task,
            bg="#4CAF50", fg="white", width=10
        )
        self.run_btn.grid(row=0, column=4, padx=5)

        tk.Button(
            frame, text="Thoát",
            command=self.exit_app,
            bg="#f44336", fg="white", width=10
        ).grid(row=0, column=5, padx=5)

        # ===== CONTROL =====
        control = tk.Frame(root)
        control.pack(pady=5)

        tk.Button(
            control, text="Reset lịch sử ",
            command=self.reset_history,
            bg="#9C27B0", fg="white", width=30
        ).grid(row=0, column=0, padx=5)

        tk.Button(
            control, text="Dọn dẹp ảnh",
            command=self.open_cleanup_popup,
            bg="#FF9800", width=22
        ).grid(row=0, column=1, padx=5)

        tk.Button(
            control, text="Xóa log hiển thị",
            command=self.clear_log,
            bg="#607D8B", fg="white", width=22
        ).grid(row=0, column=2, padx=5)

        self.stop_btn = tk.Button(
            control, text="Dừng",
            command=self.stop_task,
            bg="#f44336", fg="white",
            width=22, state="disabled"
        )
        self.stop_btn.grid(row=0, column=3, padx=5)

        # ===== LOG =====
        self.log = tk.Text(root, state="disabled")
        self.log.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        sys.stdout = TextRedirector(self.log)
        sys.stderr = TextRedirector(self.log)

    # =========================
    # UI STATE
    # =========================
    def set_running_state(self, running: bool):
        self.running = running
        state = "disabled" if running else "normal"

        self.start_entry.config(state=state)
        self.end_entry.config(state=state)
        self.run_btn.config(state="disabled" if running else "normal")
        self.stop_btn.config(state="normal" if running else "disabled")

    # =========================
    # RUN
    # =========================
    def start_task(self):
        if self.running:
            messagebox.showinfo("Đang chạy", "Tool đang chạy, vui lòng chờ hoặc bấm Dừng.")
            return

        try:
            start = int(self.start_entry.get())
            end = int(self.end_entry.get())
        except ValueError:
            messagebox.showerror("Lỗi", "Trang phải là số")
            return

        if start < 1 or start > end:
            messagebox.showerror("Lỗi", "Khoảng trang không hợp lệ")
            return

        print("\n--- BẮT ĐẦU ---\n")
        self.stop_requested = False
        self.set_running_state(True)

        threading.Thread(
            target=self.run_worker,
            args=(start, end),
            daemon=True
        ).start()

    def run_worker(self, start, end):
        try:
            run_crawler(start, end, stop_flag=lambda: self.stop_requested)
        finally:
            self.root.after(0, lambda: self.set_running_state(False))
            print("\n--- KẾT THÚC ---\n")

    def stop_task(self):
        if self.running and messagebox.askokcancel("Dừng", "Bạn có chắc muốn dừng?"):
            self.stop_requested = True
            print("[!] Đã yêu cầu dừng...")

    # =========================
    # RESET
    # =========================
    def reset_history(self):
        if not messagebox.askokcancel(
            "Xác nhận",
            "Reset lịch sử crawl?\n(state.json và data.json sẽ được làm rỗng)"
        ):
            return

        with open(STATE_FILE, "w", encoding="utf-8") as f:
            f.write("[]")
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            f.write("[]")

        print("[OK] Đã reset lịch sử")

    # =========================
    # LOG
    # =========================
    def clear_log(self):
        self.log.config(state="normal")
        self.log.delete("1.0", tk.END)
        self.log.config(state="disabled")

    # =========================
    # CLEANUP (FIX ĐẦY ĐỦ)
    # =========================
    def open_cleanup_popup(self):
        popup = tk.Toplevel(self.root)
        popup.title("Dọn dẹp ảnh")
        popup.geometry("560x480")

        popup.transient(self.root)
        popup.grab_set()
        popup.focus_force()

        folder = PICTURE_DIR
        images = []

        count_label = tk.Label(
            popup, font=("Arial", 10, "bold")
        )
        count_label.pack(anchor="w", padx=10, pady=(10, 5))

        listbox = tk.Listbox(
            popup, selectmode=tk.MULTIPLE,
            width=75, height=16
        )
        listbox.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

        def reload_images():
            nonlocal images
            images = sorted(os.listdir(folder)) if os.path.exists(folder) else []
            listbox.delete(0, tk.END)
            for img in images:
                listbox.insert(tk.END, img)
            count_label.config(text=f"Tổng số ảnh hiện có: {len(images)}")

        reload_images()

        tk.Button(
            popup, text="Chọn tất cả ảnh",
            command=lambda: listbox.select_set(0, tk.END)
        ).pack(pady=5)

        def do_cleanup():
            selected = listbox.curselection()
            if not selected:
                messagebox.showinfo("Thông báo", "Chưa chọn ảnh nào")
                return

            if not messagebox.askokcancel(
                "Xác nhận",
                f"Sẽ xóa {len(selected)} ảnh đã chọn.\nBạn chắc chắn?"
            ):
                return

            for idx in selected:
                filename = listbox.get(idx)
                path = os.path.join(folder, filename)
                if os.path.isfile(path):
                    delete_image_and_related(path)
                    print(f"[OK] Đã xóa {filename}")

            reload_images()

        btn_frame = tk.Frame(popup)
        btn_frame.pack(pady=10)

        tk.Button(
            btn_frame, text="Xóa",
            command=do_cleanup,
            bg="#f44336", fg="white", width=12
        ).grid(row=0, column=0, padx=10)

        tk.Button(
            btn_frame, text="Hủy",
            command=popup.destroy, width=12
        ).grid(row=0, column=1, padx=10)

    # =========================
    # EXIT
    # =========================
    def exit_app(self):
        if self.running:
            messagebox.showinfo("Đang chạy", "Vui lòng dừng trước khi thoát.")
            return
        if messagebox.askokcancel("Thoát", "Bạn có chắc muốn thoát không?"):
            self.root.destroy()


# =========================
# ENTRY
# =========================
if __name__ == "__main__":
    root = tk.Tk()
    app = ToolUI(root)
    root.mainloop()
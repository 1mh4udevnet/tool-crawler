import tkinter as tk
from tkinter import messagebox
import threading
import sys
import io
import os
import shutil

from app.crawler import run_crawler
from app.config import STATE_FILE, DATA_FILE
from app.config import DOWNLOAD_DIR


# =========================
# Redirect stdout/stderr -> Text widget (READ-ONLY)
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

        # ===== INPUT =====
        frame = tk.Frame(root)
        frame.pack(pady=10)

        tk.Label(frame, text="Trang bắt đầu").grid(row=0, column=0, padx=5)
        self.start_entry = tk.Entry(frame, width=8)
        self.start_entry.grid(row=0, column=1, padx=5)

        tk.Label(frame, text="Trang kết thúc").grid(row=0, column=2, padx=5)
        self.end_entry = tk.Entry(frame, width=8)
        self.end_entry.grid(row=0, column=3, padx=5)

        tk.Button(
            frame,
            text="Chạy",
            command=self.start_task,
            bg="#4CAF50",
            fg="white",
            width=10
        ).grid(row=0, column=4, padx=5)

        tk.Button(
            frame,
            text="Thoát",
            command=self.exit_app,
            bg="#f44336",
            fg="white",
            width=10
        ).grid(row=0, column=5, padx=5)

        # ===== CONTROL =====
        control = tk.Frame(root)
        control.pack(pady=5)

        tk.Button(
            control,
            text="Reset lịch sử (state + data)",
            command=self.reset_history,
            bg="#9C27B0",
            fg="white",
            width=30
        ).grid(row=0, column=0, padx=5)

        tk.Button(
            control,
            text="Dọn dẹp ảnh...",
            command=self.open_cleanup_popup,
            bg="#FF9800",
            width=22
        ).grid(row=0, column=1, padx=5)

        tk.Button(
            control,
            text="Xóa log hiển thị",
            command=self.clear_log,
            bg="#607D8B",
            fg="white",
            width=22
        ).grid(row=0, column=2, padx=5)

        # ===== LOG (READ-ONLY) =====
        self.log = tk.Text(root, state="disabled")
        self.log.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        sys.stdout = TextRedirector(self.log)
        sys.stderr = TextRedirector(self.log)

    # =========================
    # RUN CRAWLER
    # =========================
    def start_task(self):
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

        threading.Thread(
            target=lambda: run_crawler(start, end),
            daemon=True
        ).start()

    # =========================
    # RESET HISTORY (KHÔNG XÓA FILE)
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

        print("[OK] Đã reset lịch sử (state + data)")

    # =========================
    # CLEAR LOG (UI ONLY)
    # =========================
    def clear_log(self):
        self.log.config(state="normal")
        self.log.delete("1.0", tk.END)
        self.log.config(state="disabled")

    # =========================
    # CLEANUP POPUP (XÓA ẢNH)
    # =========================
    def open_cleanup_popup(self):
        popup = tk.Toplevel(self.root)
        popup.title("Dọn dẹp ảnh")
        popup.geometry("520x440")

        folder = DOWNLOAD_DIR
        images = sorted(os.listdir(folder)) if os.path.exists(folder) else []

        var_delete_all = tk.BooleanVar()
        
        tk.Label(popup, text="Hoặc chọn ảnh để xóa:").pack(anchor="w", padx=10)

        listbox = tk.Listbox(
            popup,
            selectmode=tk.MULTIPLE,
            width=70,
            height=14
        )
        listbox.pack(padx=10, pady=5, fill=tk.BOTH, expand=True)

        for img in images:
            listbox.insert(tk.END, img)

        tk.Button(
            popup,
            text="Chọn tất cả ảnh",
            command=lambda: listbox.select_set(0, tk.END)
        ).pack(pady=5)

        def do_cleanup():
            if not (var_delete_all.get() or listbox.curselection()):
                messagebox.showinfo("Thông báo", "Chưa chọn ảnh nào")
                return

            if not messagebox.askokcancel(
                "XÁC NHẬN",
                "Ảnh sẽ bị xóa vĩnh viễn.\nBạn chắc chắn?"
            ):
                return

            if var_delete_all.get():
                shutil.rmtree(folder, ignore_errors=True)
                os.makedirs(folder, exist_ok=True)
                print("[OK] Đã xóa toàn bộ ảnh")
            else:
                for idx in listbox.curselection():
                    path = os.path.join(folder, listbox.get(idx))
                    if os.path.isfile(path):
                        os.remove(path)
                        print(f"[OK] Đã xóa {listbox.get(idx)}")

            popup.destroy()

        btn_frame = tk.Frame(popup)
        btn_frame.pack(pady=10)

        tk.Button(
            btn_frame,
            text="Xóa",
            command=do_cleanup,
            bg="#f44336",
            fg="white",
            width=10
        ).grid(row=0, column=0, padx=10)

        tk.Button(
            btn_frame,
            text="Hủy",
            command=popup.destroy,
            width=10
        ).grid(row=0, column=1, padx=10)

    # =========================
    # EXIT
    # =========================
    def exit_app(self):
        if messagebox.askokcancel("Thoát", "Bạn có chắc muốn thoát không?"):
            self.root.destroy()


# =========================
# ENTRY
# =========================
if __name__ == "__main__":
    root = tk.Tk()
    app = ToolUI(root)
    root.mainloop()
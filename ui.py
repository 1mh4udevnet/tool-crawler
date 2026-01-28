import tkinter as tk
from tkinter import messagebox, ttk
import threading
import sys
import io
import os
import shutil
import json
import ctypes

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
        
        # Windows-specific fix for taskbar icon
        try:
            myappid = '1mh4u.crawler.v1'
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)
        except Exception:
            pass
        
        # 1. INITIALIZE CRITICAL STATE FIRST
        self.running = False
        self.stop_requested = False
        
        # 2. DEFINED COLORS (MUST be before any UI calls)
        self.hover_colors = {
            "#48BB78": "#38A169",  # Chạy (Green)
            "#F56565": "#E53E3E",  # Thoát/Xóa/Dừng (Red)
            "#F687B3": "#ED64A6",  # Header/Pink (Cute Pink)
            "#ED8936": "#DD6B20",  # Làm mới ảnh (Orange)
            "#9F7AEA": "#805AD5",  # Reset lịch sử (Purple)
            "#A0AEC0": "#718096",  # Xóa log (Gray)
            "#4299E1": "#3182CE",  # Tất cả (Blue)
            "#718096": "#4A5568",  # Bỏ chọn (Dark Gray)
        }

        # 3. CUSTOM ICONS (Pixel Perfect via PhotoImage.put)
        try:
            # Create PIG icon (16x16)
            self.app_icon = tk.PhotoImage(width=16, height=16)
            self.app_icon.put("#FBB6CE", to=(2, 2, 14, 14))
            self.app_icon.put("#F687B3", to=(2, 1, 5, 4))
            self.app_icon.put("#F687B3", to=(11, 1, 14, 4))
            self.app_icon.put("#2D3748", to=(5, 5, 7, 7))
            self.app_icon.put("#2D3748", to=(9, 5, 11, 7))
            self.app_icon.put("#ED64A6", to=(6, 8, 10, 11))
            self.app_icon.put("#2D3748", to=(7, 9, 8, 10))
            self.app_icon.put("#2D3748", to=(9, 9, 10, 10))

            # Create SKULL icon ( Enlarged to 32x32 for better visibility )
            self.skull_icon_small = tk.PhotoImage(width=16, height=16)
            self.skull_icon_small.put("#A0AEC0", to=(3, 2, 13, 10))
            self.skull_icon_small.put("#A0AEC0", to=(5, 10, 11, 14)) 
            self.skull_icon_small.put("#1A202C", to=(5, 5, 7, 8))
            self.skull_icon_small.put("#1A202C", to=(9, 5, 11, 8))
            self.skull_icon_small.put("#1A202C", to=(7, 8, 9, 10))
            
            # Zoom icon to 32x32
            self.skull_icon = self.skull_icon_small.zoom(2, 2)
            
        except Exception as e:
            print(f"[!] Lỗi tạo icon: {e}")
            self.app_icon = None
            self.skull_icon = None

        # 4. CONFIGURE ROOT WINDOW (Centered on screen)
        root.title("ToolCraw")
        
        # Window dimensions
        window_width = 800
        window_height = 700
        
        # Get screen dimensions
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        
        # Calculate position for center
        center_x = int(screen_width/2 - window_width/2)
        center_y = int(screen_height/2 - window_height/2)
        
        # Set geometry
        root.geometry(f"{window_width}x{window_height}+{center_x}+{center_y}")
        root.configure(bg="#F7FAFC")
        
        if self.app_icon:
            try:
                self.root.iconphoto(True, self.app_icon)
            except Exception:
                pass
        
        # 5. CUSTOM STYLES
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure(
            "Custom.Horizontal.TProgressbar",
            troughcolor='#E2E8F0',
            background='#F687B3',
            thickness=12,
            bordercolor='#E2E8F0',
            lightcolor='#F687B3',
            darkcolor='#F687B3'
        )

        # 6. BUILD UI
        self.setup_ui()
        self.animate_status() # Start pulse animation

    def setup_ui(self):
        # MAIN CONTAINER
        main_container = tk.Frame(self.root, bg="#F7FAFC")
        main_container.pack(fill=tk.BOTH, expand=True)

        # ===== HEADER (Pink) - COMPACT =====
        header = tk.Frame(main_container, bg="#F687B3", height=100)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        # Content Frame
        center_frame = tk.Frame(header, bg="#F687B3")
        center_frame.pack(expand=True)

        # Branding (Larger Skeleton icon + Larger 1mh4uApp)
        branding_row = tk.Frame(center_frame, bg="#F687B3")
        branding_row.pack(pady=(0, 10))

        if self.skull_icon:
            tk.Label(branding_row, image=self.skull_icon, bg="#F687B3").pack(side=tk.LEFT, padx=10)
        
        tk.Label(
            branding_row,
            text="1mh4uApp",
            fg="#FFE4E1",
            bg="#F687B3",
            font=("Consolas", 16, "bold")
        ).pack(side=tk.LEFT)

        # Main Title (The Big Name - EVEN BIGGER)
        tk.Label(
            center_frame,
            text="ToolCraw",
            fg="white",
            bg="#F687B3",
            font=("Segoe UI Emoji", 28, "bold")
        ).pack()

        # ===== CONTENT OVERLAY =====
        content_frame = tk.Frame(main_container, bg="#F7FAFC", padx=15, pady=10)
        content_frame.pack(fill=tk.BOTH, expand=True)

        # --- SECTION: INPUT (Card Design) ---
        input_card = tk.Frame(content_frame, bg="white", relief=tk.FLAT, bd=0, highlightthickness=1, highlightbackground="#EDF2F7")
        input_card.pack(fill=tk.X, pady=(0, 15))
        
        input_inner = tk.Frame(input_card, bg="white", padx=15, pady=10)
        input_inner.pack(fill=tk.X)

        # Bottom Row (Start, End, Buttons)
        bottom_row = tk.Frame(input_inner, bg="white")
        bottom_row.pack(fill=tk.X)

        # Pages container
        pages_box = tk.Frame(bottom_row, bg="white")
        pages_box.pack(side=tk.LEFT)

        tk.Label(pages_box, text="\U0001F4D1 Trang / Cuộn:", bg="white", font=("Segoe UI Emoji", 10, "bold"), fg="#4A5568").pack(side=tk.LEFT, padx=(0, 5))
        
        self.start_entry = tk.Entry(pages_box, width=6, font=("Segoe UI", 11), justify='center', relief=tk.FLAT, highlightthickness=1, highlightbackground="#CBD5E0")
        self.start_entry.pack(side=tk.LEFT)
        self.start_entry.insert(0, "1")

        tk.Label(pages_box, text="→", bg="white", fg="#A0AEC0").pack(side=tk.LEFT, padx=5)
        
        self.end_entry = tk.Entry(pages_box, width=6, font=("Segoe UI", 11), justify='center', relief=tk.FLAT, highlightthickness=1, highlightbackground="#CBD5E0")
        self.end_entry.pack(side=tk.LEFT)
        self.end_entry.insert(0, "1")

        # Action Buttons
        self.run_btn = self.create_styled_button(bottom_row, "\u25B6 Chạy ngay", "#48BB78", self.start_task, width=15)
        self.run_btn.pack(side=tk.RIGHT)
        
        self.exit_btn = self.create_styled_button(bottom_row, "\u2716 Thoát", "#F56565", self.exit_app, width=10)
        self.exit_btn.pack(side=tk.RIGHT, padx=10)
        

        # --- SECTION: CONTROL (Card Design) ---
        control_card = tk.Frame(content_frame, bg="white", relief=tk.FLAT, bd=0, highlightthickness=1, highlightbackground="#EDF2F7")
        control_card.pack(fill=tk.X, pady=(0, 15))
        
        control_inner = tk.Frame(control_card, bg="white", padx=10, pady=10)
        control_inner.pack(anchor=tk.CENTER)

        # Grid of controls
        self.stop_btn = self.create_styled_button(control_inner, "\u23F8 Dừng", "#F56565", self.stop_task, state="disabled")
        self.stop_btn.grid(row=0, column=0, padx=8, pady=5)
 
        self.clear_btn = self.create_styled_button(control_inner, "\U0001F4DD Xóa log", "#A0AEC0", self.clear_log)
        self.clear_btn.grid(row=0, column=1, padx=8, pady=5)
 
        self.reset_btn = self.create_styled_button(control_inner, "\U0001F504 Reset lịch sử", "#9F7AEA", self.reset_history)
        self.reset_btn.grid(row=0, column=2, padx=8, pady=5)
 
        self.refresh_btn = None # Removed as requested

        # --- SECTION: PROGRESS (Card Design) ---
        progress_card = tk.Frame(content_frame, bg="white", relief=tk.FLAT, bd=0, highlightthickness=1, highlightbackground="#EDF2F7")
        progress_card.pack(fill=tk.X, pady=(0, 15))
        
        progress_inner = tk.Frame(progress_card, bg="white", padx=15, pady=10)
        progress_inner.pack(fill=tk.X)

        self.status_label = tk.Label(
            progress_inner,
            text="\u2713 Sẵn sàng",
            bg="white",
            fg="#4A5568",
            font=("Segoe UI Emoji", 10, "bold")
        )
        self.status_label.pack(side=tk.LEFT)

        progress_bar_container = tk.Frame(progress_inner, bg="white")
        progress_bar_container.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(20, 0))

        self.progress_bar = ttk.Progressbar(
            progress_bar_container,
            style="Custom.Horizontal.TProgressbar",
            orient=tk.HORIZONTAL,
            length=100,
            mode='determinate'
        )
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)

        self.progress_percent = tk.Label(
            progress_bar_container,
            text="0%",
            bg="white",
            fg="#F687B3",
            font=("Segoe UI", 10, "bold"),
            width=5
        )
        self.progress_percent.pack(side=tk.LEFT, padx=(10, 0))

        # --- SECTION: OUTPUT (PanedWindow) ---
        self.paned_window = tk.PanedWindow(content_frame, orient=tk.HORIZONTAL, bg="#E2E8F0", sashwidth=4, sashrelief=tk.FLAT)
        self.paned_window.pack(fill=tk.BOTH, expand=True)
        
        # --- LEFT PART: LOG ---
        self.log_container = tk.Frame(self.paned_window, bg="white")
        
        log_header = tk.Frame(self.log_container, bg="#F7FAFC", padx=15, pady=8)
        log_header.pack(fill=tk.X)
        
        tk.Label(
            log_header,
            text="\U0001F4DC Log Output",
            bg="#F7FAFC",
            fg="#2D3748",
            font=("Segoe UI Emoji", 10, "bold")
        ).pack(side=tk.LEFT)

        self.log = tk.Text(
            self.log_container,
            font=("Consolas", 9),
            relief=tk.FLAT,
            padx=15,
            pady=10,
            bg="white",
            fg="#2D3748"
        )
        self.log.pack(fill=tk.BOTH, expand=True)
        self.log.config(state="disabled")
        self.paned_window.add(self.log_container, width=430)

        # --- RIGHT PART: CLEANUP ---
        self.cleanup_container = tk.Frame(self.paned_window, bg="white")
        
        cleanup_header = tk.Frame(self.cleanup_container, bg="#F7FAFC", padx=15, pady=8)
        cleanup_header.pack(fill=tk.X)
        
        tk.Label(
            cleanup_header,
            text="\U0001F5BC\uFE0F Danh sách ảnh",
            bg="#F7FAFC",
            fg="#2D3748",
            font=("Segoe UI Emoji", 10, "bold")
        ).pack(side=tk.LEFT)

        cleanup_top_bar = tk.Frame(self.cleanup_container, bg="white")
        cleanup_top_bar.pack(fill=tk.X, padx=10, pady=5)

        self.cleanup_count_label = tk.Label(
            cleanup_top_bar,
            text="\U0001F4CA 0 ảnh",
            font=("Segoe UI Emoji", 9, "bold"),
            bg="white",
            fg="#F687B3"
        )
        self.cleanup_count_label.pack(side=tk.LEFT)

        self.cleanup_delete_btn = self.create_styled_button(cleanup_top_bar, "Xóa", "#F56565", self.do_cleanup)
        self.cleanup_delete_btn.pack(side=tk.RIGHT)

        self.cleanup_deselect_btn = self.create_styled_button(cleanup_top_bar, "Bỏ chọn", "#718096", self.deselect_all_cleanup)
        self.cleanup_deselect_btn.pack(side=tk.RIGHT, padx=5)

        self.cleanup_select_all_btn = self.create_styled_button(cleanup_top_bar, "Tất cả", "#4299E1", self.select_all_cleanup)
        self.cleanup_select_all_btn.pack(side=tk.RIGHT)

        # --- Middle part: List + Scrollbar wrapped in a frame ---
        cleanup_list_frame = tk.Frame(self.cleanup_container, bg="white")
        cleanup_list_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)

        self.cleanup_listbox = tk.Text(
            cleanup_list_frame,
            font=("Segoe UI", 9),
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground="#E2E8F0",
            bd=0,
            cursor="hand2",
            padx=10,
            pady=5,
            height=10
        )
        self.cleanup_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        cleanup_scroll = tk.Scrollbar(cleanup_list_frame, command=self.cleanup_listbox.yview)
        cleanup_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.cleanup_listbox.config(yscrollcommand=cleanup_scroll.set)

        # Configure tags for selection
        self.cleanup_listbox.tag_configure("selected", background="#EDF2F7", foreground="#2D3748", font=("Segoe UI", 9, "bold"))
        
        # Bind click to toggle selection
        self.cleanup_listbox.bind("<Button-1>", self.on_cleanup_click)
        self.cleanup_listbox.config(state="disabled")

        self.paned_window.add(self.cleanup_container, width=340)

        sys.stdout = TextRedirector(self.log)
        sys.stderr = TextRedirector(self.log)
        
        # Global binds
        self.root.bind('<Return>', lambda e: self.toggle_task())
        self.root.bind('<Escape>', lambda e: self.exit_app())
        
        # Initial load
        self.reload_cleanup_images()

    # =========================
    # VISUAL EFFECTS
    # =========================
    def create_styled_button(self, parent, text, color, command, width=None, state="normal"):
        """Helper to create a button with hover effect"""
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            bg=color,
            fg="white",
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            padx=15,
            pady=6,
            cursor="hand2",
            activebackground=color, # Keep base color, we handle hover via event
            state=state,
            width=width
        )
        
        # Get hover color
        hover_color = self.hover_colors.get(color.upper(), color)
        
        # Bind events
        btn.bind("<Enter>", lambda e: self._on_hover(btn, hover_color))
        btn.bind("<Leave>", lambda e: self._on_hover(btn, color))
        
        return btn

    def _on_hover(self, widget, color):
        if widget['state'] != 'disabled':
            widget.config(bg=color)

    def animate_status(self):
        """Creates a soft pulse effect for status label"""
        colors = ["#4A5568", "#718096", "#A0AEC0", "#718096"] # Gray cycle
        
        if not hasattr(self, '_anim_idx'):
            self._anim_idx = 0
            
        if not self.running:
            self.status_label.config(fg=colors[self._anim_idx % len(colors)])
            self._anim_idx = (self._anim_idx + 1) % len(colors)
        else:
            # When running, pulse pulse between Pink/Gray
            status_colors = ["#ED64A6", "#4A5568"]
            self.status_label.config(fg=status_colors[self._anim_idx % 2])
            self._anim_idx = (self._anim_idx + 1) % (len(colors) * 2) # Keep it reasonably small
            
        self.root.after(800, self.animate_status)

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
        self.exit_btn.config(state="disabled" if running else "normal")
        self.clear_btn.config(state="disabled" if running else "normal")
        self.reset_btn.config(state="disabled" if running else "normal")
        if self.refresh_btn: self.refresh_btn.config(state="disabled" if running else "normal")
        self.cleanup_delete_btn.config(state="disabled" if running else "normal")
        self.cleanup_deselect_btn.config(state="disabled" if running else "normal")
        self.cleanup_select_all_btn.config(state="disabled" if running else "normal")


    # =========================
    # PROGRESS
    # =========================
    def update_progress(self, current, total, status_text):
        """Thread-safe progress update"""
        if total > 0:
            percent = int((current / total) * 100)
            self.root.after(0, lambda: self.progress_bar.config(value=percent))
            self.root.after(0, lambda: self.progress_percent.config(text=f"{percent}%"))
        self.root.after(0, lambda: self.status_label.config(text=status_text))

    def reset_progress(self):
        """Reset progress bar"""
        self.progress_bar.config(value=0)
        self.progress_percent.config(text="0%")
        self.status_label.config(text="Sẵn sàng")

    # =========================
    # TOGGLE
    # =========================
    def toggle_task(self):
        if self.running:
            self.stop_task()
        else:
            self.start_task()

    # =========================
    # RUN
    # =========================
    def start_task(self):
        if self.running:
            messagebox.showinfo("Đang chạy", "Tool đang chạy, vui lòng chờ hoặc bấm Dừng.")
            return

        # Use TARGET_URL from config
        from app.config import TARGET_URL
        url = TARGET_URL

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
        print(f"URL: {url}")
        self.stop_requested = False
        self.reset_progress()
        self.set_running_state(True)

        threading.Thread(
            target=self.run_worker,
            args=(start, end, url),
            daemon=True
        ).start()

    def run_worker(self, start, end, url):
        total_pages = end - start + 1
        
        # Progress callback
        def progress_callback(current_page, status):
            pages_done = current_page - start + 1
            self.update_progress(pages_done, total_pages, status)
        
        try:
            run_crawler(
                start, end, 
                target_url=url, 
                stop_flag=lambda: self.stop_requested,
                progress_callback=progress_callback
            )
        finally:
            self.root.after(0, lambda: self.set_running_state(False))
            if not self.stop_requested:
                self.update_progress(total_pages, total_pages, "Hoàn thành!")
                self.root.after(0, self.reset_page_fields)  # Reset fields after completion
            
            # Auto reload cleanup list
            self.root.after(500, self.reload_cleanup_images)
            print("\n--- KẾT THÚC ---\n")

    def reset_page_fields(self):
        """Reset page input fields after successful completion"""
        self.start_entry.delete(0, tk.END)
        self.end_entry.delete(0, tk.END)

    def stop_task(self):
        if self.running and messagebox.askokcancel("Dừng", "Bạn có chắc muốn dừng?"):
            self.stop_requested = True
            self.reset_progress()
            print("[!] Đã yêu cầu dừng...")

    # =========================
    # RESET
    # =========================
    def reset_history(self):
        # Remove confirmation as requested: "ấn vào là xóa"
        try:
            # Reset state.json
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, 'w', encoding='utf-8') as f:
                    json.dump({"last_page": 0, "processed_count": 0}, f)
            
            # Clear data.json
            if os.path.exists(DATA_FILE):
                with open(DATA_FILE, 'w', encoding='utf-8') as f:
                    json.dump([], f)
                    
            print("[OK] Đã reset lịch sử (state.json & data.json)")
        except Exception as e:
            print(f"[!] Lỗi khi reset: {str(e)}")
            
    # =========================
    # LOG
    # =========================
    def clear_log(self):
        self.log.config(state="normal")
        self.log.delete("1.0", tk.END)
        self.log.config(state="disabled")

    # =========================
    # CLEANUP (INTEGRATED)
    # =========================
    def on_cleanup_click(self, event):
        """Handle click on cleanup text list to toggle selection"""
        # Get line index from click coordinate
        index = self.cleanup_listbox.index(f"@{event.x},{event.y}")
        line_num = index.split('.')[0]
        line_start = f"{line_num}.0"
        line_end = f"{line_num}.end"
        
        # Check current tag
        tags = self.cleanup_listbox.tag_names(line_start)
        
        self.cleanup_listbox.config(state="normal")
        if "selected" in tags:
            self.cleanup_listbox.tag_remove("selected", line_start, line_end + "+1c")
        else:
            self.cleanup_listbox.tag_add("selected", line_start, line_end)
        self.cleanup_listbox.config(state="disabled")
        return "break" # Prevent default behavior

    def select_all_cleanup(self):
        self.cleanup_listbox.config(state="normal")
        # Get total number of lines
        total_lines_str = self.cleanup_listbox.index('end-1c').split('.')[0]
        if total_lines_str:
            total_lines = int(total_lines_str)
            for i in range(1, total_lines + 1):
                self.cleanup_listbox.tag_add("selected", f"{i}.0", f"{i}.end")
        self.cleanup_listbox.config(state="disabled")

    def deselect_all_cleanup(self):
        self.cleanup_listbox.config(state="normal")
        self.cleanup_listbox.tag_remove("selected", "1.0", tk.END)
        self.cleanup_listbox.config(state="disabled")

    def reload_cleanup_images(self):
        folder = PICTURE_DIR
        images = sorted(os.listdir(folder)) if os.path.exists(folder) else []
        self.cleanup_listbox.config(state="normal")
        self.cleanup_listbox.delete(1.0, tk.END)
        for i, img in enumerate(images):
            # Insert text, no default tags (normal state)
            self.cleanup_listbox.insert(tk.END, img + ("\n" if i < len(images)-1 else ""))
        self.cleanup_listbox.config(state="disabled")
        self.cleanup_count_label.config(text=f"📊 {len(images)} ảnh")

    def do_cleanup(self):
        # Find all selected lines
        selected_ranges = self.cleanup_listbox.tag_ranges("selected")
        if not selected_ranges:
            messagebox.showinfo("Thông báo", "Chưa chọn ảnh nào")
            return

        filenames_to_delete = []
        for i in range(0, len(selected_ranges), 2):
            start = selected_ranges[i]
            end = selected_ranges[i+1]
            filenames_to_delete.append(self.cleanup_listbox.get(start, end).strip())

        # Remove confirmation as requested: "ấn vào là xóa"
        folder = PICTURE_DIR
        deleted_count = 0
        for filename in filenames_to_delete:
            path = os.path.join(folder, filename)
            if os.path.isfile(path):
                delete_image_and_related(path)
                deleted_count += 1
        
        if deleted_count > 0:
            print(f"[OK] Đã xóa {deleted_count} ảnh bạn đã chọn.")

        self.reload_cleanup_images()

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
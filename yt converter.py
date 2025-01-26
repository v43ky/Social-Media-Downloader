import os
import threading
from tkinter import filedialog, StringVar, DoubleVar, messagebox
import customtkinter as ctk
from yt_dlp import YoutubeDL
from PIL import Image, ImageTk
import requests
import io
import time

# Initialize global variables
base_dir_toggle_var = None

# Set the custom theme color to green
ctk.set_appearance_mode("System")
ctk.set_default_color_theme("green")

# Function to update logs in the log box
def update_log(log_text):
    log_box.configure(state="normal")
    log_box.insert("end", log_text + "\n")
    log_box.configure(state="disabled")
    log_box.see("end")

# Function to fetch and display thumbnail
def display_thumbnail(link):
    try:
        ydl_opts = {"skip_download": True, "quiet": True}
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(link, download=False)
            thumbnail_url = info.get("thumbnail", None)
            if thumbnail_url:
                response = requests.get(thumbnail_url)
                img_data = response.content
                img = Image.open(io.BytesIO(img_data))
                img = img.resize((200, 150), Image.Resampling.LANCZOS)
                ctk_img = ctk.CTkImage(light_image=img, size=(200, 150))
                thumbnail_label.configure(image=ctk_img)
                thumbnail_label.image = ctk_img
    except Exception as e:
        update_log(f"[ERROR] Unable to fetch thumbnail: {str(e)}")

# Download Manager class for pause/resume/cancel functionality
class DownloadManager:
    def __init__(self):
        self.pause_flag = threading.Event()
        self.pause_flag.set()
        self.stop_flag = False

    def pause_download(self):
        self.pause_flag.clear()
        update_log("Download paused.")

    def resume_download(self):
        self.pause_flag.set()
        update_log("Download resumed.")

    def stop_download(self):
        self.stop_flag = True
        self.pause_flag.set()
        update_log("Download canceled.")

download_manager = DownloadManager()

# Function to handle video/photo download
def download_content(link, platform_choice, format_choice, save_path_label, progress_var):
    def progress_hook(d):
        while not download_manager.pause_flag.is_set():
            time.sleep(0.1)
        if download_manager.stop_flag:
            raise Exception("Download canceled by user.")
        if d['status'] == 'downloading':
            total_bytes = d.get('total_bytes', 1)
            downloaded_bytes = d.get('downloaded_bytes', 0)
            progress = (downloaded_bytes / total_bytes) * 100
            progress_var.set(progress)
            update_log(f"Downloading: {progress:.2f}% complete")
        elif d['status'] == 'finished':
            progress_var.set(100)
            update_log("Download completed!")

    class LogHandler:
        """Custom log handler to redirect yt_dlp logs to the log box."""
        def debug(self, msg):
            if msg.strip():
                update_log(msg)

        def warning(self, msg):
            if msg.strip():
                update_log(f"[WARNING] {msg}")

        def error(self, msg):
            if msg.strip():
                update_log(f"[ERROR] {msg}")

    try:
        save_dir = base_dir if base_dir_toggle_var.get() else filedialog.askdirectory(title="Select Folder to Save")
        if not save_dir:
            save_path_label.set("No folder selected.")
            return

        # Ensure save directory exists
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            update_log(f"Directory created: {save_dir}")

        save_path_label.set("Downloading... Please wait.")
        update_log("Download started.")

        ffmpeg_path = os.path.join(os.path.dirname(__file__), "resources", "ffmpeg", "ffmpeg.exe")
        ffprobe_path = os.path.join(os.path.dirname(__file__), "resources", "ffmpeg", "ffprobe.exe")

        ydl_opts = {
         "outtmpl": os.path.join(save_dir, "%(title)s.%(ext)s"),
         "progress_hooks": [progress_hook],
         "logger": LogHandler(),
         "postprocessor_args": [
            f"-ffmpeg-location={ffmpeg_path}",
            f"-ffprobe-location={ffprobe_path}",
         ],
        }
        if format_choice == "MP4":
            ydl_opts["format"] = "bestvideo+bestaudio/best"
        elif format_choice == "MP3":
            ydl_opts["format"] = "bestaudio"
            ydl_opts["postprocessors"] = [
                {"key": "FFmpegExtractAudio", "preferredcodec": "mp3"}
            ]

        with YoutubeDL(ydl_opts) as ydl:
            ydl.download([link])

        save_path_label.set(f"Download completed! File saved in {save_dir}.")
        update_log("Download finished successfully.")
    except Exception as e:
        if download_manager.stop_flag:
            save_path_label.set("Download canceled.")
        else:
            save_path_label.set(f"Error: {str(e)}")
        update_log(f"[ERROR] {str(e)}")
        progress_var.set(0)

# Function to start the download process
def start_download():
    link = url_var.get().strip()
    if not link:
        save_path_label.set("Please enter a valid URL.")
        return

    platform_choice = platform_var.get()
    if platform_choice not in ["YouTube", "Instagram", "TikTok"]:
        save_path_label.set("Please select a platform.")
        return

    format_choice = format_var.get()
    progress_var.set(0)
    display_thumbnail(link)
    download_manager.stop_flag = False
    threading.Thread(target=download_content, args=(link, platform_choice, format_choice, save_path_label, progress_var), daemon=True).start()

# GUI Setup
app = ctk.CTk()
app.title("SocialMedia Content Downloader")
app.geometry("1000x750")

# Variables
url_var = StringVar()
platform_var = StringVar(value="YouTube")
format_var = StringVar(value="MP4")
save_path_label = StringVar()
progress_var = DoubleVar(value=0)
base_dir = os.path.join(os.path.expanduser("~"), "Documents", "ContentDownloader")

# Ensure default save path directory exists
if not os.path.exists(base_dir):
    os.makedirs(base_dir)
    print(f"Default save directory created: {base_dir}")

base_dir_toggle_var = ctk.BooleanVar(value=True)

# Widgets
ctk.CTkLabel(app, text="SocialMedia Content Downloader", font=("Arial", 18, "bold")).pack(pady=10)

thumbnail_label = ctk.CTkLabel(app, text="", width=200, height=150)
thumbnail_label.pack(pady=5)

ctk.CTkLabel(app, text="Enter URL:", font=("Arial", 14)).pack(pady=5)
url_entry = ctk.CTkEntry(app, textvariable=url_var, width=400)
url_entry.pack(pady=5)

platform_frame = ctk.CTkFrame(app)
platform_frame.pack(pady=10)

ctk.CTkLabel(platform_frame, text="Select Platform:", font=("Arial", 14)).pack(side="left", padx=5)
ctk.CTkRadioButton(platform_frame, text="YouTube", variable=platform_var, value="YouTube").pack(side="left", padx=5)
ctk.CTkRadioButton(platform_frame, text="Instagram", variable=platform_var, value="Instagram").pack(side="left", padx=5)
ctk.CTkRadioButton(platform_frame, text="TikTok", variable=platform_var, value="TikTok").pack(side="left", padx=5)

format_frame = ctk.CTkFrame(app)
format_frame.pack(pady=10)

ctk.CTkLabel(format_frame, text="Select Format:", font=("Arial", 14)).pack(side="left", padx=5)
ctk.CTkRadioButton(format_frame, text="MP4", variable=format_var, value="MP4").pack(side="left", padx=5)
ctk.CTkRadioButton(format_frame, text="MP3", variable=format_var, value="MP3").pack(side="left", padx=5)

ctk.CTkCheckBox(app, text="Save to default location", variable=base_dir_toggle_var).pack(pady=5)

ctk.CTkButton(app, text="Download", command=start_download, font=("Arial", 14)).pack(pady=10)

progress_bar = ctk.CTkProgressBar(app, variable=progress_var, width=400)
progress_bar.pack(pady=10)

save_path_label_display = ctk.CTkLabel(app, textvariable=save_path_label, font=("Arial", 12))
save_path_label_display.pack(pady=10)

button_frame = ctk.CTkFrame(app)
button_frame.pack(pady=10)

ctk.CTkButton(button_frame, text="Pause", command=download_manager.pause_download).pack(side="left", padx=5)
ctk.CTkButton(button_frame, text="Resume", command=download_manager.resume_download).pack(side="left", padx=5)
ctk.CTkButton(button_frame, text="Cancel", command=download_manager.stop_download).pack(side="left", padx=5)

log_box = ctk.CTkTextbox(app, height=200, state="disabled")
log_box.pack(pady=5, fill="both", expand=True)

app.mainloop()

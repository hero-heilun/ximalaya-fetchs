from fetcher.track_fetcher import fetch_album_tracks, Track
from fetcher.album_fetcher import fetch_album, Album
from downloader.downloader import M4ADownloader
from dataclasses import asdict
import tkinter as tk
from tkinter import messagebox
from gui.gui import XimalayaGUI
from gui.login_dialog import check_cookie_exists, show_login_dialog
import os, sys

def main():
    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.getcwd()
    default_download_dir = os.path.join(base_dir, 'AudioBook')
    if not os.path.exists(default_download_dir):
        os.makedirs(default_download_dir, exist_ok=True)
    
    root = tk.Tk()
    
    # 检查Cookie并在主循环启动后显示登录对话框
    def check_and_show_login():
        if not check_cookie_exists():
            # 如果没有Cookie，先隐藏主窗口
            root.withdraw()
            try:
                login_result = show_login_dialog(root)
                if login_result:
                    messagebox.showinfo("登录成功", f"欢迎，{login_result['username']}！\n现在可以下载VIP内容了。")
            except Exception as e:
                print(f"登录对话框错误: {e}")
            finally:
                # 无论登录成功还是失败，都显示主窗口
                root.deiconify()
                root.lift()
                root.focus_force()
        else:
            # 有Cookie，直接显示主窗口
            root.lift()
            root.attributes('-topmost', True)
            root.after_idle(root.attributes, '-topmost', False)
            root.focus_force()
    
    # 创建应用
    app = XimalayaGUI(root, default_download_dir=default_download_dir)
    
    # 在主循环开始后立即检查登录状态
    root.after(100, check_and_show_login)
    
    # 启动主循环
    root.mainloop()

if __name__ == '__main__':
    main()
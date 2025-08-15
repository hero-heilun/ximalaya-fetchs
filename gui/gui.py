import tkinter as tk
from tkinter import messagebox, scrolledtext
import threading
import re
from PIL import Image, ImageTk
import requests
from io import BytesIO
from fetcher.album_fetcher import fetch_album
from fetcher.track_fetcher import fetch_album_tracks, fetch_album_tracks_fast, parse_tracks_concurrent
from downloader.album_download import AlbumDownloader
from downloader.single_track_download import download_single_track
import tkinter.ttk as ttk

class XimalayaGUI:
    def __init__(self, root, default_download_dir=None):
        self.root = root
        self.default_download_dir = default_download_dir
        self.root.title('喜马拉雅批量下载工具 - 增强版')
        self.root.geometry('1200x900')  # 调整窗口大小
        
        # 确保窗口在前台显示并获得焦点
        self.root.lift()
        self.root.focus_force()
        
        self._init_widgets()
        self.setup_log_tags()
        
        # 确保初始化完成后窗口仍在前台
        self.root.after(100, lambda: self.root.lift())

    def _init_widgets(self):
        # 创建主框架
        main_frame = tk.Frame(self.root)
        main_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        # 左侧面板
        left_panel = tk.Frame(main_frame)
        left_panel.pack(side='left', fill='both', expand=True, padx=(0, 10))
        
        # 右侧面板（日志）
        right_panel = tk.Frame(main_frame)
        right_panel.pack(side='right', fill='y')
        
        # 输入区域
        input_frame = tk.LabelFrame(left_panel, text='输入区域', padx=10, pady=10)
        input_frame.pack(fill='x', pady=(0, 10))
        
        # 专辑ID输入
        tk.Label(input_frame, text='专辑ID:').grid(row=0, column=0, sticky='w', padx=(0, 5))
        self.album_id_var = tk.StringVar()
        tk.Entry(input_frame, textvariable=self.album_id_var, width=30).grid(row=0, column=1, sticky='ew', padx=(0, 10))
        
        # 音频ID输入
        tk.Label(input_frame, text='音频ID:').grid(row=0, column=2, sticky='w', padx=(0, 5))
        self.track_id_var = tk.StringVar()
        tk.Entry(input_frame, textvariable=self.track_id_var, width=30).grid(row=0, column=3, sticky='ew')
        
        # 下载延迟输入
        tk.Label(input_frame, text='下载延迟(秒):').grid(row=1, column=0, sticky='w', padx=(0, 5), pady=(10, 0))
        self.delay_var = tk.StringVar(value='5')
        tk.Entry(input_frame, textvariable=self.delay_var, width=10).grid(row=1, column=1, sticky='w', pady=(10, 0))
        
        # 恢复下载按钮
        tk.Button(input_frame, text='恢复下载', command=self.resume_download, bg='lightgreen').grid(row=1, column=2, columnspan=2, sticky='e', pady=(10, 0))
        
        # 设置列权重
        input_frame.grid_columnconfigure(1, weight=1)
        input_frame.grid_columnconfigure(3, weight=1)
        
        # 操作按钮区域
        btn_frame = tk.Frame(left_panel)
        btn_frame.pack(fill='x', pady=(0, 10))
        
        tk.Button(btn_frame, text='获取专辑信息', width=12, command=self.run_album_info).pack(side='left', padx=(0, 5))
        tk.Button(btn_frame, text='解析曲目', width=12, command=self.run_parse_tracks).pack(side='left', padx=(0, 5))
        tk.Button(btn_frame, text='下载专辑', width=12, command=self.run_album_download).pack(side='left', padx=(0, 5))
        tk.Button(btn_frame, text='下载单曲', width=12, command=self.run_track_download).pack(side='left', padx=(0, 5))
        tk.Button(btn_frame, text='登录管理', width=12, command=self.show_login_dialog).pack(side='left')
        # 专辑信息展示区
        info_frame = tk.LabelFrame(left_panel, text='专辑信息', padx=10, pady=10)
        info_frame.pack(fill='x', pady=(0, 10))
        
        # 创建专辑信息的内部框架
        info_content = tk.Frame(info_frame)
        info_content.pack(fill='x')
        
        # 左侧封面
        self.cover_frame = tk.Frame(info_content, width=120, height=120, bg='#f0f0f0')
        self.cover_frame.grid_propagate(False)
        self.cover_frame.grid(row=0, column=0, padx=(0, 15), pady=5, sticky='nw')
        self.cover_label = tk.Label(self.cover_frame, text='无封面', bg='#f0f0f0', relief='groove')
        self.cover_label.place(relx=0.5, rely=0.5, anchor='center')
        
        # 右侧信息
        info_details = tk.Frame(info_content)
        info_details.grid(row=0, column=1, sticky='ew')
        
        self.album_title_var = tk.StringVar()
        self.album_create_var = tk.StringVar()
        self.album_update_var = tk.StringVar()
        self.album_count_var = tk.StringVar()
        
        tk.Label(info_details, text='标题:', font=('Arial', 9, 'bold')).grid(row=0, column=0, sticky='w', pady=2)
        tk.Label(info_details, textvariable=self.album_title_var, wraplength=400, anchor='w', justify='left').grid(row=0, column=1, sticky='w', pady=2)
        
        tk.Label(info_details, text='创建时间:', font=('Arial', 9, 'bold')).grid(row=1, column=0, sticky='w', pady=2)
        tk.Label(info_details, textvariable=self.album_create_var, anchor='w').grid(row=1, column=1, sticky='w', pady=2)
        
        tk.Label(info_details, text='更新时间:', font=('Arial', 9, 'bold')).grid(row=2, column=0, sticky='w', pady=2)
        tk.Label(info_details, textvariable=self.album_update_var, anchor='w').grid(row=2, column=1, sticky='w', pady=2)
        
        tk.Label(info_details, text='曲目数量:', font=('Arial', 9, 'bold')).grid(row=3, column=0, sticky='w', pady=2)
        tk.Label(info_details, textvariable=self.album_count_var, anchor='w').grid(row=3, column=1, sticky='w', pady=2)
        
        # 简介
        tk.Label(info_details, text='简介:', font=('Arial', 9, 'bold')).grid(row=4, column=0, sticky='nw', pady=(10, 0))
        self.intro_text = tk.Text(info_details, width=50, height=4, wrap='word', font=('Arial', 9))
        self.intro_text.grid(row=4, column=1, sticky='ew', pady=(10, 0))
        self.intro_text.config(state='disabled')
        
        # 设置列权重
        info_content.grid_columnconfigure(1, weight=1)
        info_details.grid_columnconfigure(1, weight=1)
        # 曲目列表显示区域
        tracks_frame = tk.LabelFrame(left_panel, text='曲目列表', padx=10, pady=10)
        tracks_frame.pack(fill='both', expand=True, pady=(0, 10))
        
        # 创建曲目列表的Treeview
        tree_frame = tk.Frame(tracks_frame)
        tree_frame.pack(fill='both', expand=True)
        
        self.tracks_tree = ttk.Treeview(tree_frame, columns=('title', 'duration', 'url_status'), show='tree headings')
        self.tracks_tree.pack(side='left', fill='both', expand=True)
        
        # 设置列标题和宽度
        self.tracks_tree.heading('#0', text='序号')
        self.tracks_tree.heading('title', text='标题')
        self.tracks_tree.heading('duration', text='时长')
        self.tracks_tree.heading('url_status', text='解析状态')
        
        self.tracks_tree.column('#0', width=60, minwidth=50)
        self.tracks_tree.column('title', width=400, minwidth=300)
        self.tracks_tree.column('duration', width=80, minwidth=60)
        self.tracks_tree.column('url_status', width=120, minwidth=100)
        
        # 添加滚动条
        tracks_scrollbar = ttk.Scrollbar(tree_frame, orient='vertical', command=self.tracks_tree.yview)
        tracks_scrollbar.pack(side='right', fill='y')
        self.tracks_tree.configure(yscrollcommand=tracks_scrollbar.set)
        
        # 曲目操作按钮
        tracks_btn_frame = tk.Frame(tracks_frame)
        tracks_btn_frame.pack(fill='x', pady=(10, 0))
        
        tk.Button(tracks_btn_frame, text='解析选中URL', command=self.parse_selected_urls).pack(side='left', padx=(0, 5))
        tk.Button(tracks_btn_frame, text='下载选中', command=self.download_selected_tracks).pack(side='left', padx=(0, 5))
        tk.Button(tracks_btn_frame, text='检查文件状态', command=self.check_file_status).pack(side='left', padx=(0, 5))
        tk.Button(tracks_btn_frame, text='缓存统计', command=self.show_cache_stats).pack(side='left', padx=(0, 5))
        tk.Button(tracks_btn_frame, text='全选', command=self.select_all_tracks).pack(side='left', padx=(0, 5))
        tk.Button(tracks_btn_frame, text='清空', command=self.clear_tracks).pack(side='left')
        
        # 存储解析后的曲目数据
        self.parsed_tracks = []
        
        # 下载进度区
        progress_frame = tk.LabelFrame(left_panel, text='下载进度', padx=10, pady=10)
        progress_frame.pack(fill='x')
        
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(progress_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill='x', pady=(0, 5))
        
        self.progress_label = tk.Label(progress_frame, text='', anchor='w')
        self.progress_label.pack(fill='x')
        
        # 右侧日志输出区
        log_frame = tk.LabelFrame(right_panel, text='日志输出', padx=10, pady=10)
        log_frame.pack(fill='both', expand=True)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, width=40, height=30, state='disabled', font=('Consolas', 9))
        self.log_text.pack(fill='both', expand=True)

    def log(self, msg, level='info'):
        if callable(getattr(msg, '__call__', None)):
            msg = str(msg)
        def append():
            self.log_text.config(state='normal')
            tag = level if level in ('info', 'warning', 'error') else 'info'
            self.log_text.insert(tk.END, msg + '\n', tag)
            self.log_text.see(tk.END)
            self.log_text.config(state='disabled')
        self.log_text.after(0, append)

    def log_info(self, msg):
        self.log(msg, level='info')
    def log_warning(self, msg):
        self.log(msg, level='warning')
    def log_error(self, msg):
        self.log(msg, level='error')

    def setup_log_tags(self):
        self.log_text.tag_config('info', foreground='black')
        self.log_text.tag_config('warning', foreground='orange')
        self.log_text.tag_config('error', foreground='red')

    def run_in_thread(self, func):
        threading.Thread(target=func, daemon=True).start()

    def show_cover_image(self, url):
        target_size = (150, 150)
        if not url:
            self.cover_label.config(image='', text='无封面')
            return
        try:
            response = requests.get(url, timeout=10)
            img_data = response.content
            img = Image.open(BytesIO(img_data)).convert('RGBA')
            # 保持比例缩放并居中填充白底
            img.thumbnail(target_size, Image.LANCZOS)
            bg = Image.new('RGBA', target_size, (255, 255, 255, 255))
            offset = ((target_size[0] - img.width) // 2, (target_size[1] - img.height) // 2)
            bg.paste(img, offset, img if img.mode == 'RGBA' else None)
            self.cover_imgtk = ImageTk.PhotoImage(bg)
            self.cover_label.config(image=self.cover_imgtk, text='')
        except Exception:
            self.cover_label.config(image='', text='加载失败')

    def set_progress(self, current, total, filename=None):
        percent = (current / total * 100) if total else 0
        self.progress_var.set(percent)
        if filename:
            self.progress_label.config(text=f'({current}/{total}) {filename}')
        else:
            self.progress_label.config(text=f'({current}/{total})')

    def run_album_info(self):
        album_id = self.album_id_var.get().strip()
        if not album_id:
            self.log_warning('请输入专辑ID')
            messagebox.showwarning('提示', '请输入专辑ID')
            return
        self.log_info(f'获取专辑信息: {album_id}')
        def task():
            album = fetch_album(int(album_id))
            if album:
                self.album_title_var.set(album.albumTitle)
                intro = re.sub('<[^<]+?>', '', album.richIntro or '')
                self.intro_text.config(state='normal')
                self.intro_text.delete('1.0', tk.END)
                self.intro_text.insert(tk.END, intro)
                self.intro_text.config(state='disabled')
                self.album_create_var.set(album.createDate)
                self.album_update_var.set(album.updateDate)
                cover_url = album.cover if album.cover else ''
                try:
                    tracks = fetch_album_tracks(int(album_id), 1, 1, log_func=self.log)
                    total_count = tracks[0].totalCount if tracks and tracks[0].totalCount else ''
                except Exception:
                    total_count = ''
                self.album_count_var.set(str(total_count))
                self.show_cover_image(cover_url)
                self.log_info(f'获取专辑成功: {album.albumTitle}')
            else:
                self.album_title_var.set('')
                self.intro_text.config(state='normal')
                self.intro_text.delete('1.0', tk.END)
                self.intro_text.config(state='disabled')
                self.album_create_var.set('')
                self.album_update_var.set('')
                self.album_count_var.set('')
                self.show_cover_image('')
                self.log_error('获取专辑信息失败')
        self.run_in_thread(task)

    def run_album_download(self):
        album_id = self.album_id_var.get().strip()
        if not album_id:
            self.log_warning('请输入专辑ID')
            messagebox.showwarning('提示', '请输入专辑ID')
            return
        try:
            delay = float(self.delay_var.get())
            if delay < 0:
                delay = 0
        except Exception:
            delay = 1
        self.download_delay = delay
        self.log_info(f'下载专辑: {album_id} (延迟: {delay}s)')
        # 直接传递已获取的album对象和曲目总数
        album_obj = getattr(self, 'album', None) if hasattr(self, 'album') else None
        total_count = None
        if hasattr(self, 'album_count_var'):
            try:
                total_count = int(self.album_count_var.get())
            except Exception:
                total_count = None
        def task():
            try:
                self.log_info('下载线程已启动')
                def progress_hook(current, total, filename=None):
                    self.root.after(0, lambda: self.set_progress(current, total, filename))
                AlbumDownloader(
                    album_id,
                    log_func=self.log,
                    delay=delay,
                    save_dir=self.default_download_dir,
                    progress_func=progress_hook,
                    album=album_obj,
                    total_count=total_count
                ).download_album()
            except Exception as e:
                self.log_error(f'下载线程异常: {e}')
                messagebox.showerror('错误', f'下载线程异常: {e}')
        self.run_in_thread(task)

    def run_track_download(self):
        track_id = self.track_id_var.get().strip()
        if not track_id:
            self.log_warning('请输入音频ID')
            messagebox.showwarning('提示', '请输入音频ID')
            return
        self.log_info(f'下载单曲: track_id={track_id}')
        def task():
            download_single_track(track_id, log_func=self.log, save_dir=self.default_download_dir)
        self.run_in_thread(task)
    
    def run_parse_tracks(self):
        """解析专辑中的所有曲目"""
        album_id = self.album_id_var.get().strip()
        if not album_id:
            self.log_warning('请输入专辑ID')
            messagebox.showwarning('提示', '请输入专辑ID')
            return
            
        self.log_info(f'开始解析专辑曲目: {album_id}')
        self.clear_tracks()
        
        # 显示初始状态
        self.set_progress(0, 100, "准备获取曲目列表...")
        
        def task():
            try:
                # 获取专辑信息
                if not hasattr(self, 'album') or not self.album:
                    album = fetch_album(int(album_id))
                    if album:
                        self.album = album
                        
                # 分页获取所有曲目
                page = 1
                page_size = 20
                all_tracks = []
                
                # 动态更新UI的辅助函数
                def schedule_ui_update(track_obj, track_idx, dur_str, status_str):
                    self.root.after(0, lambda: self.add_track_to_list(track_idx, track_obj, dur_str, status_str))
                
                def update_progress_info(current_page, total_pages, current_count, total_count):
                    self.root.after(0, lambda: self.set_progress(
                        current_count, total_count, 
                        f"获取曲目: 第{current_page}/{total_pages}页, {current_count}/{total_count}首"
                    ))
                
                while True:
                    try:
                        self.log_info(f'正在快速获取第{page}页曲目...')
                        tracks = fetch_album_tracks_fast(int(album_id), page, page_size, log_func=self.log)
                        if not tracks:
                            break
                            
                        all_tracks.extend(tracks)
                        
                        # 批量查询缓存状态（性能优化）
                        cached_tracks = {}
                        try:
                            from utils.sqlite_cache import get_sqlite_cache
                            cache = get_sqlite_cache()
                            track_ids = [track.trackId for track in tracks]
                            cached_tracks = cache.get_tracks_cache_status(track_ids, int(album_id))
                        except Exception:
                            pass  # 静默处理缓存查询错误
                        
                        # 实时更新界面显示
                        for i, track in enumerate(tracks):
                            idx = (page - 1) * page_size + i + 1
                            duration_str = f"{track.duration // 60}:{track.duration % 60:02d}" if track.duration else "未知"
                            
                            # 检查缓存状态
                            url_status = "待解析"
                            if track.trackId in cached_tracks:
                                cache_data = cached_tracks[track.trackId]
                                track.cryptedUrl = cache_data['crypted_url']
                                track.url = cache_data['decrypted_url']
                                url_status = "✅ 已解析"
                            
                            # 立即更新到界面
                            schedule_ui_update(track, idx, duration_str, url_status)
                        
                        # 更新进度信息
                        if hasattr(tracks[0], 'totalCount') and tracks[0].totalCount:
                            total_count = tracks[0].totalCount
                            total_pages = (total_count + page_size - 1) // page_size
                            current_count = len(all_tracks)
                            
                            # 实时更新进度条
                            update_progress_info(page, total_pages, current_count, total_count)
                            
                            self.log_info(f'已获取 {current_count}/{total_count} 首曲目 (第{page}/{total_pages}页)')
                            
                            if page >= total_pages:
                                break
                        else:
                            # 如果没有总数信息，当返回的track数量小于page_size时停止
                            if len(tracks) < page_size:
                                break
                                
                        page += 1
                        
                        # 小延迟让用户看到动态更新效果，但不影响整体速度
                        import time
                        time.sleep(0.1)
                        
                    except Exception as e:
                        self.log_error(f'获取第{page}页时出错: {e}')
                        break
                
                self.parsed_tracks = all_tracks
                self.log_info(f'解析完成，共获取到 {len(all_tracks)} 个曲目')
                
                # SQLite缓存自动保存，无需手动保存
                self.log_info('[缓存] SQLite缓存已自动保存')
                
                # 显示最终完成状态
                self.root.after(0, lambda: self.set_progress(
                    len(all_tracks), len(all_tracks), 
                    f"解析完成! 共{len(all_tracks)}首曲目，请选择曲目并解析URL"
                ))
                
            except Exception as e:
                self.log_error(f'解析曲目失败: {e}')
                
        self.run_in_thread(task)
        
    def add_track_to_list(self, idx, track, duration_str, url_status):
        """在UI线程中添加曲目到列表"""
        item_id = self.tracks_tree.insert('', 'end', text=str(idx), values=(
            track.title,
            duration_str,
            url_status
        ))
        # 根据解析状态设置显示
        if url_status == "解析失败":
            self.tracks_tree.set(item_id, 'url_status', '❌ 解析失败')
        elif url_status == "已解析":
            self.tracks_tree.set(item_id, 'url_status', '✅ 已解析')
        elif url_status == "待解析":
            self.tracks_tree.set(item_id, 'url_status', '⏳ 待解析')
        elif url_status == "解析中":
            self.tracks_tree.set(item_id, 'url_status', '🔄 解析中')
        else:
            self.tracks_tree.set(item_id, 'url_status', url_status)
        
        # 动态滚动到最新添加的项目，但不要过于频繁
        if idx % 5 == 0:  # 每5个项目滚动一次
            self.tracks_tree.see(item_id)
    
    def select_all_tracks(self):
        """全选所有曲目"""
        for item in self.tracks_tree.get_children():
            self.tracks_tree.selection_add(item)
    
    def clear_tracks(self):
        """清空曲目列表"""
        for item in self.tracks_tree.get_children():
            self.tracks_tree.delete(item)
        self.parsed_tracks = []
    
    def parse_selected_urls(self):
        """解析选中曲目的播放URL"""
        selected_items = self.tracks_tree.selection()
        if not selected_items:
            self.log_warning('请先选择要解析URL的曲目')
            messagebox.showwarning('提示', '请先选择要解析URL的曲目')
            return
            
        if not self.parsed_tracks:
            self.log_warning('请先解析曲目列表')
            return
            
        album_id = self.album_id_var.get().strip()
        if not album_id:
            self.log_warning('请输入专辑ID')
            return
        
        # 获取选中的曲目，过滤已解析的
        selected_tracks = []
        selected_indices = []
        skipped_tracks = []
        
        for item in selected_items:
            idx = int(self.tracks_tree.item(item, 'text')) - 1
            if 0 <= idx < len(self.parsed_tracks):
                track = self.parsed_tracks[idx]
                # 检查是否已经解析过URL
                if track.url and track.url.strip():
                    skipped_tracks.append((item, idx, track))
                    self.log_info(f'跳过已解析URL的曲目: {track.title}')
                else:
                    selected_tracks.append(track)
                    selected_indices.append((item, idx))
        
        if skipped_tracks:
            self.log_info(f'跳过 {len(skipped_tracks)} 个已解析URL的曲目')
            # 更新界面显示为已解析状态
            for item, idx, track in skipped_tracks:
                self.root.after(0, lambda i=item: self.tracks_tree.set(i, 'url_status', '✅ 已解析'))
        
        if not selected_tracks:
            if skipped_tracks:
                self.log_info('所有选中曲目的URL都已解析完成')
            else:
                self.log_warning('没有找到有效的选中曲目')
            return
        
        self.log_info(f'开始并发解析 {len(selected_tracks)} 个曲目的播放URL...')
        
        def task():
            try:
                # 先更新状态为"解析中"
                for item, idx in selected_indices:
                    self.root.after(0, lambda i=item: self.tracks_tree.set(i, 'url_status', '🔄 解析中'))
                
                # 进度回调函数
                def progress_callback(completed, total):
                    self.root.after(0, lambda: self.set_progress(completed, total, f"解析URL: {completed}/{total}"))
                
                # 并发解析URL
                parsed_tracks = parse_tracks_concurrent(
                    selected_tracks, 
                    int(album_id), 
                    log_func=self.log, 
                    progress_callback=progress_callback,
                    max_workers=3  # 可调整并发数
                )
                
                # 更新解析结果
                for i, (item, idx) in enumerate(selected_indices):
                    track = parsed_tracks[i]
                    # 更新原始数据
                    self.parsed_tracks[idx] = track
                    
                    # 更新界面显示
                    if track.url:
                        status = '✅ 已解析'
                    else:
                        status = '❌ 解析失败'
                    
                    self.root.after(0, lambda i=item, s=status: self.tracks_tree.set(i, 'url_status', s))
                
                success_count = sum(1 for track in parsed_tracks if track.url)
                self.log_info(f'URL解析完成！成功解析 {success_count}/{len(selected_tracks)} 个曲目')
                
                # SQLite缓存自动保存，无需手动保存
                self.log_info('[缓存] SQLite缓存已自动保存')
                
                self.root.after(0, lambda: self.set_progress(len(selected_tracks), len(selected_tracks), "URL解析完成"))
                
            except Exception as e:
                self.log_error(f'URL解析异常: {e}')
                # 恢复状态
                for item, idx in selected_indices:
                    self.root.after(0, lambda i=item: self.tracks_tree.set(i, 'url_status', '⏳ 待解析'))
                
        self.run_in_thread(task)
    
    def download_selected_tracks(self):
        """下载选中的曲目"""
        selected_items = self.tracks_tree.selection()
        if not selected_items:
            self.log_warning('请先选择要下载的曲目')
            messagebox.showwarning('提示', '请先选择要下载的曲目')
            return
            
        if not self.parsed_tracks:
            self.log_warning('请先解析曲目')
            return
            
        album_id = self.album_id_var.get().strip()
        if not album_id:
            self.log_warning('请输入专辑ID')
            return
            
        try:
            delay = float(self.delay_var.get())
            if delay < 0:
                delay = 0
        except Exception:
            delay = 5
        
        def task():
            try:
                from downloader.downloader import M4ADownloader
                import os
                import re
                
                downloader = M4ADownloader()
                
                # 创建下载目录
                if hasattr(self, 'album') and self.album:
                    safe_album_title = re.sub(r'[\\/:*?"<>|]', '_', self.album.albumTitle)
                    save_dir = os.path.join(self.default_download_dir, safe_album_title)
                else:
                    save_dir = os.path.join(self.default_download_dir, f'Album_{album_id}')
                os.makedirs(save_dir, exist_ok=True)
                
                selected_tracks = []
                for item in selected_items:
                    # 获取序号
                    idx = int(self.tracks_tree.item(item, 'text')) - 1
                    if 0 <= idx < len(self.parsed_tracks):
                        selected_tracks.append((idx + 1, self.parsed_tracks[idx]))
                
                total_selected = len(selected_tracks)
                downloaded = 0
                skipped_existing = 0
                
                # 检查哪些曲目已解析URL
                tracks_with_url = [(idx, track) for idx, track in selected_tracks if track.url]
                tracks_without_url = [(idx, track) for idx, track in selected_tracks if not track.url]
                
                # 进一步检查已存在的文件
                tracks_to_download = []
                for idx, track in tracks_with_url:
                    safe_title = re.sub(r'[\\/:*?"<>|]', '_', track.title)
                    filename = f'{idx:03d}_{safe_title}.m4a'
                    filepath = os.path.join(save_dir, filename)
                    
                    if os.path.exists(filepath) and os.path.getsize(filepath) > 1024 * 10:
                        self.log_info(f'[{idx}] 文件已存在，跳过下载: {filename}')
                        skipped_existing += 1
                    else:
                        tracks_to_download.append((idx, track))
                
                if tracks_without_url:
                    self.log_warning(f'发现 {len(tracks_without_url)} 个曲目未解析URL，将跳过下载')
                    for idx, track in tracks_without_url:
                        self.log_warning(f'[{idx}] 跳过未解析URL的曲目: {track.title}')
                
                if skipped_existing > 0:
                    self.log_info(f'跳过 {skipped_existing} 个已存在的文件')
                
                if not tracks_to_download:
                    if skipped_existing > 0:
                        self.log_info('所有选中文件都已下载完成')
                    else:
                        self.log_error('没有已解析URL的曲目可供下载')
                    return
                
                self.log_info(f'开始下载 {len(tracks_to_download)} 个需要下载的曲目')
                
                for track_idx, track in tracks_to_download:
                    try:
                        self.set_progress(downloaded, len(tracks_to_download), f"准备下载: {track.title}")
                        
                        # 创建安全的文件名
                        safe_title = re.sub(r'[\\/:*?"<>|]', '_', track.title)
                        filename = f'{track_idx:03d}_{safe_title}.m4a'
                        filepath = os.path.join(save_dir, filename)
                        
                        self.log_info(f'[{track_idx}/{len(tracks_to_download)}] 开始下载: {track.title}')
                        
                        downloader.download_from_url(track.url, filepath, log_func=self.log)
                        self.log_info(f'[{track_idx}] 下载完成: {filename}')
                        
                        downloaded += 1
                        self.set_progress(downloaded, len(tracks_to_download), f"已完成: {track.title}")
                        
                        # 延迟避免风控
                        if delay > 0:
                            import time
                            time.sleep(delay)
                            
                    except Exception as e:
                        self.log_error(f'[{track_idx}] 下载失败: {track.title}, 错误: {e}')
                        downloaded += 1
                        
                self.log_info(f'选中曲目下载完成！共 {total_selected} 个，成功 {downloaded} 个')
                self.set_progress(total_selected, total_selected, "下载完成")
                
            except Exception as e:
                self.log_error(f'批量下载异常: {e}')
                
        self.run_in_thread(task)
    
    def check_file_status(self):
        """检查曲目的文件状态（是否已下载）"""
        if not self.parsed_tracks:
            self.log_warning('请先解析曲目列表')
            return
            
        album_id = self.album_id_var.get().strip()
        if not album_id:
            self.log_warning('请输入专辑ID')
            return
        
        def task():
            try:
                import os
                import re
                
                # 创建下载目录路径
                if hasattr(self, 'album') and self.album:
                    safe_album_title = re.sub(r'[\\/:*?"<>|]', '_', self.album.albumTitle)
                    save_dir = os.path.join(self.default_download_dir, safe_album_title)
                else:
                    save_dir = os.path.join(self.default_download_dir, f'Album_{album_id}')
                
                parsed_count = 0
                downloaded_count = 0
                total_count = len(self.parsed_tracks)
                
                self.log_info(f'开始检查 {total_count} 个曲目的文件状态...')
                
                # 遍历所有曲目检查状态
                for idx, track in enumerate(self.parsed_tracks):
                    track_idx = idx + 1
                    
                    # 检查URL解析状态
                    url_parsed = bool(track.url and track.url.strip())
                    if url_parsed:
                        parsed_count += 1
                    
                    # 检查文件下载状态
                    safe_title = re.sub(r'[\\/:*?"<>|]', '_', track.title)
                    filename = f'{track_idx:03d}_{safe_title}.m4a'
                    filepath = os.path.join(save_dir, filename)
                    
                    file_exists = os.path.exists(filepath) and os.path.getsize(filepath) > 1024 * 10
                    if file_exists:
                        downloaded_count += 1
                    
                    # 更新界面显示状态
                    def update_status(idx=idx, url_parsed=url_parsed, file_exists=file_exists):
                        items = self.tracks_tree.get_children()
                        if idx < len(items):
                            item_id = items[idx]
                            if file_exists:
                                status = '📁 已下载'
                            elif url_parsed:
                                status = '✅ 已解析'
                            else:
                                status = '⏳ 待解析'
                            self.tracks_tree.set(item_id, 'url_status', status)
                    
                    self.root.after(0, update_status)
                    
                    # 更新进度
                    if track_idx % 10 == 0 or track_idx == total_count:
                        self.root.after(0, lambda c=track_idx, t=total_count: self.set_progress(c, t, f"检查状态: {c}/{t}"))
                
                # 显示检查结果
                self.log_info(f'文件状态检查完成:')
                self.log_info(f'  总曲目数: {total_count}')
                self.log_info(f'  已解析URL: {parsed_count} ({parsed_count/total_count*100:.1f}%)')
                self.log_info(f'  已下载文件: {downloaded_count} ({downloaded_count/total_count*100:.1f}%)')
                self.log_info(f'  待解析: {total_count - parsed_count}')
                self.log_info(f'  待下载: {parsed_count - downloaded_count}')
                
                self.root.after(0, lambda: self.set_progress(total_count, total_count, "状态检查完成"))
                
            except Exception as e:
                self.log_error(f'检查文件状态异常: {e}')
                
        self.run_in_thread(task)
    
    def show_cache_stats(self):
        """显示URL缓存统计信息"""
        try:
            from utils.sqlite_cache import get_sqlite_cache
            cache = get_sqlite_cache()
            stats = cache.get_cache_stats()
            
            stats_info = f"""SQLite增强缓存统计信息:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🎵 曲目URL缓存:
  📊 总数: {stats['total']} 个
  ✅ 有效: {stats['valid']} 个
  ⚠️ 无效: {stats['invalid']} 个
  ⏰ 过期: {stats['expired']} 个
  📚 专辑: {stats['albums']} 个

📋 专辑页面缓存: (NEW!)
  📊 总页面: {stats['album_pages_total']} 页
  ✅ 有效页面: {stats['album_pages_valid']} 页
  ⏰ 过期页面: {stats['album_pages_expired']} 页
  📚 缓存专辑: {stats['cached_albums']} 个

💾 数据库大小: {stats['db_size_mb']} MB
📁 数据库文件: {stats['db_path']}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🚀 性能优化特性:
• 专辑页面缓存 - 快速解析不再重复请求！
• 高性能索引查询
• 并发访问安全
• 曲目URL缓存: 24小时有效期
• 专辑页面缓存: 6小时有效期"""

            self.log_info("URL缓存统计:")
            self.log_info(stats_info)
            
            # 显示对话框
            from tkinter import messagebox
            messagebox.showinfo("URL缓存统计", stats_info)
            
        except Exception as e:
            self.log_error(f'获取缓存统计失败: {e}')
    
    def resume_download(self):
        """恢复被风控暂停的下载"""
        album_id = self.album_id_var.get().strip()
        if not album_id:
            self.log_warning('请先输入专辑ID')
            messagebox.showwarning('提示', '请先输入专辑ID')
            return
        
        self.log_info('正在尝试恢复下载，将等待更长时间避免风控...')
        
        try:
            delay = max(float(self.delay_var.get()), 10.0)  # 最少10秒延迟
        except Exception:
            delay = 10.0
        
        def task():
            try:
                # 等待一段时间让API冷却
                import time
                self.log_info('等待60秒让API冷却...')
                time.sleep(60)
                
                def progress_hook(current, total, filename=None):
                    self.root.after(0, lambda: self.set_progress(current, total, filename))
                
                self.log_info('开始恢复下载，使用更保守的请求策略')
                AlbumDownloader(
                    album_id,
                    log_func=self.log,
                    delay=delay,
                    save_dir=self.default_download_dir,
                    progress_func=progress_hook
                ).download_album()
                
            except Exception as e:
                self.log_error(f'恢复下载异常: {e}')
                
        self.run_in_thread(task)
    
    def show_login_dialog(self):
        """显示登录管理对话框"""
        try:
            from gui.login_dialog import show_login_dialog, check_cookie_exists
            
            # 确保窗口在前台
            self.root.lift()
            self.root.focus_force()
            
            # 检查当前cookie状态
            if check_cookie_exists():
                if messagebox.askyesno("登录管理", "检测到已有Cookie配置。\n\n是否重新登录？"):
                    result = show_login_dialog(self.root, show_first_time_info=False)
                    if result:
                        messagebox.showinfo("成功", f"重新登录成功！\n用户: {result['username']}")
                    else:
                        messagebox.showinfo("提示", "登录操作已取消")
            else:
                # 没有cookie，显示登录对话框（不显示首次启动信息）
                result = show_login_dialog(self.root, show_first_time_info=False)
                if result:
                    messagebox.showinfo("成功", f"登录成功！\n用户: {result['username']}")
                else:
                    messagebox.showinfo("提示", "登录操作已取消")
                    
        except Exception as e:
            messagebox.showerror("错误", f"登录管理出错: {str(e)}")

if __name__ == '__main__':
    root = tk.Tk()
    app = XimalayaGUI(root)
    root.mainloop()

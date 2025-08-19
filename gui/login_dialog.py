import tkinter as tk
from tkinter import ttk, messagebox
import requests
import base64
import time
import json
import os
from PIL import Image, ImageTk
from io import BytesIO
from dotenv import load_dotenv, set_key
import threading

class XimalayaLoginDialog:
    def __init__(self, parent, show_first_time_info=True):
        self.parent = parent
        self.result = None
        self.qr_id = None
        self.qr_check_thread = None
        self.qr_check_running = False
        self.show_first_time_info = show_first_time_info
        
        
        # 设置请求session
        self.session = requests.Session()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        # 创建并初始化对话框
        self.create_dialog()
        
    def safe_ui_update(self, update_func):
        """安全的UI更新方法，处理线程安全问题"""
        try:
            if hasattr(self, 'dialog') and self.dialog and self.dialog.winfo_exists():
                self.dialog.after(0, update_func)
            else:
                # 如果对话框不存在或已销毁，直接跳过
                pass
        except (RuntimeError, tk.TclError):
            # 如果主循环已结束或对话框已销毁，跳过UI更新
            pass
        
    def create_dialog(self):
        """创建对话框窗口"""
        # 创建对话框窗口
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("喜马拉雅登录")
        self.dialog.geometry("500x600")
        self.dialog.resizable(False, False)
        
        # 立即设置为可见状态
        self.dialog.wm_state('normal')
        
        # 设置窗口关系
        if self.parent:
            self.dialog.transient(self.parent)
        
        # 立即构建UI
        self.setup_ui()
        
        # 强制更新布局
        self.dialog.update_idletasks()
        
        # 居中窗口
        self.center_window()
        
        # 确保窗口显示
        self.dialog.deiconify()
        self.dialog.lift()
        self.dialog.focus_force()
        
        # 设置模态
        self.dialog.grab_set()
        
        # 确保窗口在macOS上正确显示
        if hasattr(self.dialog, 'wm_attributes'):
            try:
                self.dialog.wm_attributes('-topmost', True)
                self.dialog.after(100, lambda: self.dialog.wm_attributes('-topmost', False))
            except:
                pass
        
    def center_window(self):
        """窗口居中"""
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (500 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (600 // 2)
        self.dialog.geometry(f"500x600+{x}+{y}")
        
    def setup_ui(self):
        """设置UI界面"""
        # 主框架
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 标题
        title_label = ttk.Label(main_frame, text="喜马拉雅登录", font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 10))
        
        # 说明信息（仅在首次启动时显示）
        if self.show_first_time_info:
            info_label = ttk.Label(main_frame, 
                                 text="未检测到有效的Cookie配置\n\nCookie用于下载VIP内容和获取收听历史\n请选择登录方式，或点击取消以游客模式启动", 
                                 font=("Arial", 10),
                                 foreground="blue",
                                 justify=tk.CENTER)
            info_label.pack(pady=(0, 15))
        
        # 创建notebook用于选项卡
        self.notebook = ttk.Notebook(main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # 手动输入Cookie选项卡
        self.setup_manual_tab()
        
        # 扫码登录选项卡
        self.setup_qr_tab()
        
        # 底部按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(20, 0))
        
        # 确定按钮
        ok_btn = ttk.Button(button_frame, text="登录", command=self.ok)
        ok_btn.pack(side=tk.RIGHT)
        
        # 取消按钮
        cancel_btn = ttk.Button(button_frame, text="游客模式启动", command=self.cancel)
        cancel_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
    def setup_manual_tab(self):
        """设置手动输入Cookie选项卡"""
        manual_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(manual_frame, text="手动输入Cookie")
        
        # 说明文本
        instruction_text = """获取Cookie步骤：
1. 打开浏览器，访问 https://www.ximalaya.com
2. 登录你的喜马拉雅账号
3. 按F12打开开发者工具，切换到Network标签
4. 刷新页面，找到任意ximalaya.com的请求
5. 在请求头中找到Cookie字段，复制完整内容"""
        
        instruction_label = ttk.Label(manual_frame, text=instruction_text, justify=tk.LEFT)
        instruction_label.pack(anchor=tk.W, pady=(0, 10))
        
        # Cookie输入框
        ttk.Label(manual_frame, text="Cookie内容:").pack(anchor=tk.W)
        self.cookie_text = tk.Text(manual_frame, height=8, wrap=tk.WORD)
        self.cookie_text.pack(fill=tk.X, pady=(5, 10))
        
        # 滚动条
        scrollbar = ttk.Scrollbar(manual_frame, orient="vertical", command=self.cookie_text.yview)
        self.cookie_text.configure(yscrollcommand=scrollbar.set)
        
        # 验证按钮
        validate_btn = ttk.Button(manual_frame, text="验证Cookie", command=self.validate_cookie)
        validate_btn.pack(pady=5)
        
        # 状态标签
        self.manual_status_label = ttk.Label(manual_frame, text="", foreground="blue")
        self.manual_status_label.pack(pady=5)
        
    def setup_qr_tab(self):
        """设置扫码登录选项卡"""
        qr_frame = ttk.Frame(self.notebook, padding="10")
        self.notebook.add(qr_frame, text="扫码登录")
        
        # 说明文本
        instruction_label = ttk.Label(qr_frame, text="请使用喜马拉雅App扫描下方二维码登录", font=("Arial", 12))
        instruction_label.pack(pady=(0, 10))
        
        # 二维码显示区域
        self.qr_label = ttk.Label(qr_frame, text="点击\"获取二维码\"按钮开始", relief="sunken", width=30)
        self.qr_label.pack(pady=10)
        
        # 获取二维码按钮
        self.get_qr_btn = ttk.Button(qr_frame, text="获取二维码", command=self.get_qrcode)
        self.get_qr_btn.pack(pady=5)
        
        # 状态标签
        self.qr_status_label = ttk.Label(qr_frame, text="", foreground="blue")
        self.qr_status_label.pack(pady=5)
        
    def validate_cookie(self):
        """验证Cookie有效性"""
        cookie = self.cookie_text.get("1.0", tk.END).strip()
        if not cookie:
            # 直接更新UI（因为这是在主线程中调用的）
            self.manual_status_label.config(text="请输入Cookie内容", foreground="red")
            return
            
        # 直接更新UI（因为这是在主线程中调用的）
        self.manual_status_label.config(text="验证中...", foreground="blue")
        
        # 在后台线程中验证，避免UI阻塞
        def validate_in_background():
            try:
                # 测试Cookie有效性
                user_url = "https://www.ximalaya.com/revision/main/getCurrentUser"
                headers = self.headers.copy()
                headers['Cookie'] = cookie
                
                response = requests.get(user_url, headers=headers, timeout=10)
                data = response.json()
                
                if data.get('ret') == 200:
                    username = data.get('data', {}).get('nickname', 'Unknown')
                    self.safe_ui_update(lambda: self.manual_status_label.config(text=f"验证成功！用户: {username}", foreground="green"))
                    self.result = {'cookie': cookie, 'username': username}
                else:
                    self.safe_ui_update(lambda: self.manual_status_label.config(text="Cookie无效或已过期", foreground="red"))
                    
            except Exception as e:
                self.safe_ui_update(lambda: self.manual_status_label.config(text=f"验证失败: {str(e)}", foreground="red"))
        
        # 启动后台验证线程
        threading.Thread(target=validate_in_background, daemon=True).start()
            
    def get_qrcode(self):
        """获取并显示二维码"""
        # 直接更新UI状态（因为这是在主线程中调用的）
        self.qr_status_label.config(text="获取二维码中...", foreground="blue")
        self.get_qr_btn.config(state="disabled")
        
        # 在后台线程中获取二维码，避免UI阻塞
        def get_qr_in_background():
            try:
                # 获取二维码接口
                qr_url = "https://passport.ximalaya.com/web/qrCode/gen?level=L"
                response = self.session.get(qr_url, headers=self.headers, timeout=10)
                data = response.json()
                
                if data.get('ret') == 0:
                    self.qr_id = data['qrId']
                    qr_img_data = data['img']
                    
                    print(f"二维码获取成功，qrId: {self.qr_id}")
                    
                    # 使用主窗口的after方法（参考gui.py的实现）
                    if self.parent:
                        try:
                            self.parent.after(0, lambda img=qr_img_data: self.display_qrcode(img))
                            self.parent.after(10, self.start_qr_check)
                            self.parent.after(20, lambda: self.qr_status_label.config(text="请使用喜马拉雅App扫描二维码", foreground="blue"))
                        except Exception as e:
                            print(f"UI更新调度失败: {e}")
                else:
                    self.safe_ui_update(lambda: self.qr_status_label.config(text="获取二维码失败", foreground="red"))
                    self.safe_ui_update(lambda: self.get_qr_btn.config(state="normal"))
                    
            except Exception as e:
                self.safe_ui_update(lambda: self.qr_status_label.config(text=f"获取二维码错误: {str(e)}", foreground="red"))
                self.safe_ui_update(lambda: self.get_qr_btn.config(state="normal"))
        
        # 启动后台线程
        threading.Thread(target=get_qr_in_background, daemon=True).start()
            
    def display_qrcode(self, img_data):
        """在GUI中显示二维码"""
        try:
            print("开始显示二维码...")
            print(f"接收到的base64数据长度: {len(img_data)}")
            print(f"数据前50字符: {img_data[:50]}")
            
            # 解码base64图片
            img_bytes = base64.b64decode(img_data)
            print(f"解码后字节长度: {len(img_bytes)}")
            
            img = Image.open(BytesIO(img_bytes))
            print(f"PIL打开成功，图片大小: {img.size}, 格式: {img.format}")
            
            # 调整图片大小适应显示
            img = img.resize((200, 200), Image.Resampling.LANCZOS)
            print("图片缩放完成")
            
            # 转换为tkinter可显示的格式
            photo = ImageTk.PhotoImage(img)
            print("ImageTk转换完成")
            
            # 显示图片
            self.qr_label.config(image=photo, text="")
            self.qr_label.image = photo  # 保持引用防止被垃圾回收
            print("二维码UI更新完成")
            
        except Exception as e:
            print(f"显示二维码失败: {e}")
            import traceback
            traceback.print_exc()
            self.safe_ui_update(lambda: self.qr_status_label.config(text=f"显示二维码失败: {str(e)}", foreground="red"))
            
    def start_qr_check(self):
        """开始检查扫码状态"""
        self.qr_check_running = True
        self.qr_check_thread = threading.Thread(target=self.check_qr_status, daemon=True)
        self.qr_check_thread.start()
        
    def check_qr_status(self):
        """检查扫码状态（在后台线程运行）"""
        start_time = time.time()
        timeout = 180  # 3分钟超时
        
        print(f"开始检查扫码状态，qr_id: {self.qr_id}")
        
        while self.qr_check_running and time.time() - start_time < timeout:
            try:
                # 使用参考项目的正确格式：添加时间戳
                timestamp = int(time.time() * 1000)
                check_url = f"https://passport.ximalaya.com/web/qrCode/check/{self.qr_id}/{timestamp}"
                
                response = self.session.get(check_url, headers=self.headers)
                print(f"检查状态: {response.status_code}")
                
                # 检查是否有set-cookie响应头（登录成功的标志）
                if 'set-cookie' in response.headers:
                    print("检测到登录成功的cookie!")
                    self.process_qr_login_success(response)
                    break
                
                # 尝试解析JSON响应
                try:
                    data = response.json()
                    if data.get('ret') == 0:
                        # 等待扫码状态
                        pass
                    else:
                        print(f"API返回: {data}")
                except:
                    # 非JSON响应
                    print(f"非JSON响应: {response.text[:100]}...")
                
                time.sleep(3)  # 每3秒检查一次
                
            except Exception as e:
                print(f"检查状态错误: {e}")
                self.safe_ui_update(lambda: self.qr_status_label.config(text=f"检查状态错误: {str(e)}", foreground="red"))
                time.sleep(3)
        
        if self.qr_check_running and time.time() - start_time >= timeout:
            self.safe_ui_update(lambda: self.qr_status_label.config(text="扫码超时，请重新获取二维码", foreground="red"))
            self.safe_ui_update(lambda: self.get_qr_btn.config(state="normal"))
            
    def process_qr_login_success(self, response):
        """处理扫码登录成功"""
        try:
            print("处理登录成功...")
            self.qr_check_running = False
            
            # 从响应头中提取cookies - 使用requests的方式
            cookie_items = []
            
            # 检查是否有Set-Cookie头
            if 'Set-Cookie' in response.headers:
                # 如果只有一个Set-Cookie，直接处理
                set_cookie_value = response.headers.get('Set-Cookie')
                if isinstance(set_cookie_value, str):
                    cookie_parts = set_cookie_value.split(';')[0]
                    cookie_items.append(cookie_parts)
                else:
                    # 如果有多个Set-Cookie头，遍历处理
                    for cookie_header in set_cookie_value:
                        cookie_parts = cookie_header.split(';')[0]
                        cookie_items.append(cookie_parts)
            
            # 也可以直接从session的cookies中获取
            session_cookies = self.session.cookies.get_dict()
            for name, value in session_cookies.items():
                cookie_items.append(f"{name}={value}")
            
            # 去重并合并
            unique_cookies = list(set(cookie_items))
            cookie_str = '; '.join(unique_cookies)
            print(f"提取的cookie: {cookie_str}")
            
            # 获取用户信息
            user_info = self.get_user_info(cookie_str)
            
            if user_info:
                self.result = {
                    'cookie': cookie_str,
                    'username': user_info['username']
                }
                username = user_info['username']
                self.safe_ui_update(lambda: self.qr_status_label.config(text=f"登录成功！用户: {username}", foreground="green"))
                
                # 保存Cookie到.env文件
                if self.save_cookie_to_env(cookie_str):
                    print("Cookie已保存到.env文件")
                    # 延迟1秒后自动关闭对话框
                    if self.parent:
                        self.parent.after(1000, self.dialog.destroy)
                    else:
                        self.dialog.after(1000, self.dialog.destroy)
                else:
                    self.safe_ui_update(lambda: self.qr_status_label.config(text="保存Cookie失败", foreground="red"))
            else:
                self.safe_ui_update(lambda: self.qr_status_label.config(text="获取用户信息失败", foreground="red"))
                
        except Exception as e:
            error_msg = str(e)
            print(f"处理登录成功错误: {error_msg}")
            import traceback
            traceback.print_exc()
            self.safe_ui_update(lambda: self.qr_status_label.config(text=f"处理登录失败: {error_msg}", foreground="red"))
            
    def get_login_info(self):
        """获取登录后的cookie和用户信息"""
        # 在后台线程中获取登录信息，避免UI阻塞
        def get_info_in_background():
            try:
                # 确认登录
                confirm_url = f"https://passport.ximalaya.com/web/qrCode/auth/{self.qr_id}/"
                response = self.session.get(confirm_url, headers=self.headers, timeout=10)
                
                if response.status_code == 200:
                    # 获取cookie
                    cookies = self.session.cookies.get_dict()
                    cookie_str = '; '.join([f"{k}={v}" for k, v in cookies.items()])
                    
                    # 获取用户信息
                    user_info = self.get_user_info(cookie_str)
                    
                    if user_info:
                        self.result = {
                            'cookie': cookie_str,
                            'username': user_info['username']
                        }
                        self.safe_ui_update(lambda: self.qr_status_label.config(text=f"登录成功！用户: {user_info['username']}", foreground="green"))
                        
                        # 保存Cookie到.env文件
                        if self.save_cookie_to_env(cookie_str):
                            # 延迟1秒后自动关闭对话框
                            if self.parent:
                                self.parent.after(1000, self.dialog.destroy)
                            else:
                                self.dialog.after(1000, self.dialog.destroy)
                    else:
                        self.safe_ui_update(lambda: self.qr_status_label.config(text="获取用户信息失败", foreground="red"))
                else:
                    self.safe_ui_update(lambda: self.qr_status_label.config(text="登录确认失败", foreground="red"))
                    
            except Exception as e:
                self.safe_ui_update(lambda: self.qr_status_label.config(text=f"获取登录信息错误: {str(e)}", foreground="red"))
        
        # 启动后台线程
        threading.Thread(target=get_info_in_background, daemon=True).start()
            
    def get_user_info(self, cookie):
        """获取用户信息"""
        try:
            user_url = "https://www.ximalaya.com/revision/main/getCurrentUser"
            headers = self.headers.copy()
            headers['Cookie'] = cookie
            
            response = requests.get(user_url, headers=headers, timeout=10)
            data = response.json()
            
            if data.get('ret') == 200:
                username = data.get('data', {}).get('nickname', 'Unknown')
                return {'username': username}
            
            return None
            
        except Exception as e:
            print(f"获取用户信息错误: {e}")
            return None
            
    def save_cookie_to_env(self, cookie):
        """保存Cookie到.env文件"""
        try:
            # 使用应用程序配置目录中的.env文件
            config_dir = os.environ.get('XIMALAYA_CONFIG_DIR', os.getcwd())
            env_file = os.path.join(config_dir, '.env')
            
            # 确保配置目录存在
            os.makedirs(config_dir, exist_ok=True)
            
            # 确保.env文件存在
            if not os.path.exists(env_file):
                with open(env_file, 'w', encoding='utf-8') as f:
                    pass
            
            # 设置环境变量
            set_key(env_file, "XIMALAYA_COOKIES", f'"{cookie}"')
            return True
            
        except Exception as e:
            print(f"保存Cookie错误: {e}")
            return False
            
    def ok(self):
        """确定按钮处理"""
        if not self.result:
            messagebox.showwarning("提示", "请先完成登录验证")
            return
            
        # 保存Cookie到.env文件
        if self.save_cookie_to_env(self.result['cookie']):
            messagebox.showinfo("成功", f"登录成功！用户: {self.result['username']}\nCookie已保存到.env文件")
        else:
            messagebox.showwarning("警告", f"登录成功，但保存Cookie失败\n用户: {self.result['username']}")
            
        self.dialog.destroy()
        
    def cancel(self):
        """取消按钮处理"""
        self.qr_check_running = False
        self.result = None
        self.dialog.destroy()
        
    def show(self):
        """显示对话框并返回结果"""
        self.dialog.wait_window()
        return self.result

def check_cookie_exists():
    """检查是否存在有效的Cookie"""
    # 使用应用程序配置目录中的.env文件
    config_dir = os.environ.get('XIMALAYA_CONFIG_DIR', os.getcwd())
    env_path = os.path.join(config_dir, '.env')
    load_dotenv(env_path)
    cookie = os.getenv('XIMALAYA_COOKIES')
    
    if not cookie:
        return False
    
    # 去除引号和空格
    cookie = cookie.strip().strip('"').strip("'")
    
    # 检查是否为空
    if not cookie:
        return False
    
    # 简单验证Cookie格式
    if '_token=' in cookie or 'remember_me=' in cookie:
        return True
        
    return False

def show_login_dialog(parent=None, show_first_time_info=True):
    """显示登录对话框"""
    try:
        if parent is None:
            # 创建临时根窗口
            root = tk.Tk()
            root.withdraw()  # 隐藏根窗口
            parent = root
        
        dialog = XimalayaLoginDialog(parent, show_first_time_info)
        result = dialog.show()
        
        # 如果创建了临时根窗口，销毁它
        if 'root' in locals():
            root.destroy()
            
        return result
        
    except Exception as e:
        print(f"登录对话框错误: {e}")
        return None

if __name__ == "__main__":
    # 测试登录对话框
    root = tk.Tk()
    root.withdraw()
    
    result = show_login_dialog(root)
    if result:
        print(f"登录成功: {result}")
    else:
        print("登录取消")
        
    root.destroy()
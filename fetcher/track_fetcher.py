class BlockedException(Exception):
    pass
import requests
import os
from utils.utils import decrypt_url
from dotenv import load_dotenv
from dataclasses import dataclass
from typing import List, Optional
import urllib3
# 忽略 InsecureRequestWarning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

load_dotenv()
XIMALAYA_COOKIES = os.getenv("XIMALAYA_COOKIES", "")

@dataclass
class Track:
    trackId: int
    title: str
    createTime: str
    updateTime: str
    cryptedUrl: str
    url: str
    duration: int
    totalCount: Optional[int] = None  # 专辑下音频总数
    page: Optional[int] = None        # 当前页码
    pageSize: Optional[int] = None    # 每页音频数量
    cover: Optional[str] = None       # 专辑封面

def fetch_track_crypted_url(track_id: int, album_id: int, log_func=None, use_cache: bool = True) -> str:
    import time
    import random
    import json
    
    # 定义日志输出函数
    def log(msg, level='info'):
        if log_func:
            if callable(getattr(log_func, '__call__', None)):
                # 检查log_func是否支持level参数
                try:
                    log_func(msg, level=level)
                except TypeError:
                    # 如果不支持level参数，则只传递消息
                    log_func(msg)
        else:
            print(msg)
    
    # 尝试从缓存获取URL
    if use_cache:
        log(f"[Track解析] 尝试从缓存获取 Track {track_id} URL...", 'info')
        try:
            from utils.sqlite_cache import get_sqlite_cache
            cache = get_sqlite_cache()
            cached_track = cache.get_cached_track(track_id, album_id, log_func)
            if cached_track and cached_track.crypted_url:
                log(f"[Track解析] ✅ 缓存命中！返回缓存URL Track {track_id}", 'info')
                log(f"[Track解析] 返回URL: {cached_track.crypted_url[:50]}{'...' if len(cached_track.crypted_url) > 50 else ''}", 'info')
                return cached_track.crypted_url
            else:
                log(f"[Track解析] ❌ 缓存未命中，需要网络解析 Track {track_id}", 'info')
        except Exception as e:
            log(f"[Track解析] ❌ 缓存读取异常: {e}", 'warning')
    else:
        log(f"[Track解析] 缓存已禁用，直接网络解析 Track {track_id}", 'info')
    
    # 随机延迟2-5秒，避免请求过于频繁
    delay = random.uniform(2.0, 5.0)
    log(f"[Track解析] 等待 {delay:.1f}秒 后请求 track_id={track_id}", 'info')
    time.sleep(delay)
    
    url = f"https://www.ximalaya.com/mobile-playpage/track/v3/baseInfo/{album_id}"
    params = {
        "device": "web",
        "trackId": track_id,
        "trackQualityLevel": 1
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Cookie": XIMALAYA_COOKIES
    }
    
    # 打印请求信息
    log(f"[Track解析] 请求URL: {url}", 'info')
    log(f"[Track解析] 请求参数: {json.dumps(params, ensure_ascii=False)}", 'info')
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            log(f"[Track解析] 响应状态码: {response.status_code}", 'info')
            
            if response.status_code == 200:
                data = response.json()
                # 打印响应数据（限制长度）
                response_str = json.dumps(data, ensure_ascii=False)
                if len(response_str) > 500:
                    log(f"[Track解析] 响应数据(截取): {response_str[:500]}...", 'info')
                else:
                    log(f"[Track解析] 响应数据: {response_str}", 'info')
                
                # 检查风控
                if data.get("ret") == 1001 or "系统繁忙" in data.get("msg", ""):
                    if attempt < max_retries - 1:
                        # 风控触发时等待更长时间再重试
                        wait_time = random.uniform(30.0, 60.0) * (attempt + 1)
                        log(f"[Track解析] 风控触发，等待 {wait_time:.1f} 秒后重试 (第{attempt+1}次): track {track_id}", 'warning')
                        time.sleep(wait_time)
                        continue
                    else:
                        log(f"[Track解析] 风控触发: track {track_id}: {response.status_code}, {response.text}", 'error')
                        raise BlockedException(f"系统繁忙，风控触发: {response.text}")
                
                play_url_list = data.get("trackInfo", {}).get("playUrlList", [])
                if play_url_list:
                    encrypted_url = play_url_list[0].get("url", "")
                    log(f"[Track解析] 获取到加密URL: {encrypted_url[:50]}..." if len(encrypted_url) > 50 else f"[Track解析] 获取到加密URL: {encrypted_url}", 'info')
                    
                    # 缓存URL
                    if use_cache:
                        log(f"[Track解析] 准备缓存解析结果 Track {track_id}...", 'info')
                        try:
                            from utils.sqlite_cache import get_sqlite_cache
                            from utils.utils import decrypt_url
                            cache = get_sqlite_cache()
                            decrypted_url = decrypt_url(encrypted_url)
                            log(f"[Track解析] 开始写入缓存: crypted_len={len(encrypted_url)}, decrypted_len={len(decrypted_url)}", 'info')
                            cache.cache_track(track_id, album_id, 
                                            crypted_url=encrypted_url, 
                                            decrypted_url=decrypted_url, 
                                            log_func=log_func)
                            log(f"[Track解析] ✅ 缓存写入调用完成 Track {track_id}", 'info')
                        except Exception as e:
                            log(f"[Track解析] ❌ 缓存保存失败 Track {track_id}: {e}", 'warning')
                            import traceback
                            log(f"[Track解析] 详细错误: {traceback.format_exc()}", 'warning')
                    
                    return encrypted_url
                else:
                    log(f"[Track解析] 未找到playUrlList，track_id={track_id}", 'warning')
                    
            else:
                log(f"[Track解析] 请求失败 track {track_id}: {response.status_code}, {response.text[:200] if len(response.text) > 200 else response.text}", 'error')
            
            if attempt < max_retries - 1:
                wait_time = random.uniform(5.0, 10.0)
                log(f"[Track解析] 等待 {wait_time:.1f} 秒后重试", 'info')
                time.sleep(wait_time)
                
        except BlockedException:
            raise
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = random.uniform(5.0, 15.0)
                log(f"[Track解析] 请求异常，等待 {wait_time:.1f} 秒后重试: {e}", 'warning')
                time.sleep(wait_time)
            else:
                log(f"[Track解析] 请求失败，放弃重试: {e}", 'error')
                raise
    
    return ""

def fetch_album_tracks(album_id: int, page: int, page_size: int, log_func=None) -> List[Track]:
    import time
    import random
    import json
    
    # 定义日志输出函数
    def log(msg, level='info'):
        if log_func:
            if callable(getattr(log_func, '__call__', None)):
                # 检查log_func是否支持level参数
                try:
                    log_func(msg, level=level)
                except TypeError:
                    # 如果不支持level参数，则只传递消息
                    log_func(msg)
        else:
            print(msg)
    
    # 为专辑曲目列表请求也添加延迟
    delay = random.uniform(1.0, 3.0)
    log(f"[专辑曲目] 等待 {delay:.1f}秒 后请求第{page}页", 'info')
    time.sleep(delay)
    
    url = f"https://m.ximalaya.com/m-revision/common/album/queryAlbumTrackRecordsByPage"
    params = {
        "albumId": album_id,
        "page": page,
        "pageSize": page_size
    }
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Pragma": "no-cache",
        "Referer": f"https://www.ximalaya.com/album/{album_id}",
        "Origin": "https://www.ximalaya.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "Cookie": XIMALAYA_COOKIES,
        "X-Requested-With": "XMLHttpRequest"
    }
    
    # 打印请求信息
    log(f"[专辑曲目] 请求URL: {url}", 'info')
    log(f"[专辑曲目] 请求参数: {json.dumps(params, ensure_ascii=False)}", 'info')
    
    max_retries = 2
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            log(f"[专辑曲目] 响应状态码: {response.status_code}", 'info')
            
            if response.status_code == 200:
                data = response.json()
                
                # 打印响应数据的关键信息
                total_count = data.get("data", {}).get("totalCount", 0)
                track_count = len(data.get("data", {}).get("trackDetailInfos", []))
                log(f"[专辑曲目] 总曲目数: {total_count}, 本页曲目数: {track_count}", 'info')
                
                # 打印部分响应数据
                if track_count > 0:
                    first_track = data.get("data", {}).get("trackDetailInfos", [])[0]
                    log(f"[专辑曲目] 第一个曲目信息: {json.dumps(first_track.get('trackInfo', {}).get('title', ''), ensure_ascii=False)}", 'info')
                
                track_list = data.get("data", {}).get("trackDetailInfos", [])
                tracks = []
                try:
                    for i, track in enumerate(track_list):
                        track_info = track['trackInfo']
                        track_title = track_info.get("title", "未知标题")
                        track_id = track_info.get("id")
                        
                        log(f"[专辑曲目] 正在解析第{(page-1)*page_size + i + 1}个曲目: {track_title} (ID: {track_id})", 'info')
                        
                        try:
                            crypted_url = fetch_track_crypted_url(track_id, album_id, log_func=log_func)
                        except BlockedException as be:
                            log(f"[专辑曲目] 风控终止专辑曲目拉取: {be}", 'error')
                            # 直接抛出到外层
                            raise
                        
                        if not crypted_url:
                            log(f"[专辑曲目] 跳过: {track_title}，无有效播放链接", 'warning')
                            continue
                        
                        # 解密URL
                        decrypted_url = decrypt_url(crypted_url)
                        log(f"[专辑曲目] 解密后URL: {decrypted_url[:100]}..." if len(decrypted_url) > 100 else f"[专辑曲目] 解密后URL: {decrypted_url}", 'info')
                        
                        cover_path = track_info.get("cover")
                        cover_url = f"https://imagev2.xmcdn.com/{cover_path}" if cover_path and not cover_path.startswith("http") else cover_path
                        tracks.append(
                            Track(
                                trackId=track_id,
                                title=track_title,
                                createTime=track_info.get("createdTime", ""),
                                updateTime=track_info.get("updatedTime", ""),
                                cryptedUrl=crypted_url,
                                url=decrypted_url,
                                duration=track_info.get("duration", 0),
                                totalCount=total_count,  # 专辑音频总数
                                page=page,  # 当前页码
                                pageSize=page_size,  # 每页数量
                                cover=cover_url,  # 拼接后的专辑封面
                            )
                        )
                        log(f"[专辑曲目] 成功解析: {track_title}", 'info')
                    
                    log(f"[专辑曲目] 第{page}页解析完成，共{len(tracks)}个曲目", 'info')
                    return tracks
                    
                except BlockedException:
                    # 直接抛出到外层
                    raise
            else:
                log(f"[专辑曲目] 请求失败: {response.status_code}, {response.text[:200] if len(response.text) > 200 else response.text}", 'error')
                if attempt < max_retries - 1:
                    wait_time = random.uniform(10.0, 20.0)
                    log(f"[专辑曲目] 等待 {wait_time:.1f} 秒后重试", 'info')
                    time.sleep(wait_time)
                    
        except BlockedException:
            raise
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = random.uniform(10.0, 20.0)
                log(f"[专辑曲目] 获取专辑曲目异常，等待 {wait_time:.1f} 秒后重试: {e}", 'warning')
                time.sleep(wait_time)
            else:
                log(f"[专辑曲目] 获取专辑曲目失败: {e}", 'error')
                raise
                
    return []


def fetch_album_tracks_fast(album_id: int, page: int, page_size: int, log_func=None) -> List[Track]:
    """快速获取专辑曲目列表，优先使用缓存"""
    import time
    import random
    import json
    
    # 定义日志输出函数
    def log(msg, level='info'):
        if log_func:
            if callable(getattr(log_func, '__call__', None)):
                try:
                    log_func(msg, level=level)
                except TypeError:
                    log_func(msg)
        else:
            print(msg)
    
    # 尝试从专辑页面缓存获取数据
    try:
        from utils.sqlite_cache import get_sqlite_cache
        cache = get_sqlite_cache()
        cached_page = cache.get_cached_album_page(album_id, page, page_size, log_func)
        
        if cached_page:
            log(f"[快速解析] ✅ 专辑页面缓存命中！直接返回第{page}页数据", 'info')
            tracks = []
            for track_data in cached_page['tracks']:
                track = Track(
                    trackId=track_data['trackId'],
                    title=track_data['title'],
                    createTime=track_data.get('createTime', ''),
                    updateTime=track_data.get('updateTime', ''),
                    cryptedUrl='',
                    url='',
                    duration=track_data.get('duration', 0),
                    totalCount=cached_page['total_count'],
                    page=page,
                    pageSize=page_size
                )
                tracks.append(track)
            
            log(f"[快速解析] 从缓存返回 {len(tracks)} 个曲目", 'info')
            return tracks
        else:
            log(f"[快速解析] ❌ 专辑页面缓存未命中，需要网络请求第{page}页", 'info')
    except Exception as e:
        log(f"[快速解析] ❌ 缓存查询异常: {e}", 'warning')
    
    # 缓存未命中，进行网络请求
    delay = random.uniform(0.5, 1.5)
    log(f"[快速解析] 等待 {delay:.1f}秒 后请求第{page}页", 'info')
    time.sleep(delay)
    
    url = f"https://m.ximalaya.com/m-revision/common/album/queryAlbumTrackRecordsByPage"
    params = {
        "albumId": album_id,
        "page": page,
        "pageSize": page_size
    }
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
        "Pragma": "no-cache",
        "Referer": f"https://www.ximalaya.com/album/{album_id}",
        "Origin": "https://www.ximalaya.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "sec-ch-ua": '"Google Chrome";v="131", "Chromium";v="131", "Not_A Brand";v="24"',
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": '"Windows"',
        "Cookie": XIMALAYA_COOKIES,
        "X-Requested-With": "XMLHttpRequest"
    }
    
    log(f"[快速解析] 请求第{page}页曲目列表", 'info')
    
    max_retries = 2
    for attempt in range(max_retries):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                total_count = data.get("data", {}).get("totalCount", 0)
                track_count = len(data.get("data", {}).get("trackDetailInfos", []))
                log(f"[快速解析] 第{page}页: {track_count}个曲目 (总共{total_count})", 'info')
                
                track_list = data.get("data", {}).get("trackDetailInfos", [])
                tracks = []
                
                for i, track in enumerate(track_list):
                    track_info = track['trackInfo']
                    track_title = track_info.get("title", "未知标题")
                    track_id = track_info.get("id")
                    
                    cover_path = track_info.get("cover")
                    cover_url = f"https://imagev2.xmcdn.com/{cover_path}" if cover_path and not cover_path.startswith("http") else cover_path
                    
                    # 快速模式：不解析URL，留空等待后续解析
                    tracks.append(
                        Track(
                            trackId=track_id,
                            title=track_title,
                            createTime=track_info.get("createdTime", ""),
                            updateTime=track_info.get("updatedTime", ""),
                            cryptedUrl="",  # 快速模式不解析
                            url="",  # 快速模式不解析
                            duration=track_info.get("duration", 0),
                            totalCount=total_count,
                            page=page,
                            pageSize=page_size,
                            cover=cover_url,
                        )
                    )
                
                log(f"[快速解析] 第{page}页解析完成，共{len(tracks)}个曲目", 'info')
                
                # 缓存专辑页面数据
                try:
                    from utils.sqlite_cache import get_sqlite_cache
                    cache = get_sqlite_cache()
                    
                    # 准备缓存数据
                    tracks_data = []
                    for track in tracks:
                        tracks_data.append({
                            'trackId': track.trackId,
                            'title': track.title,
                            'createTime': track.createTime,
                            'updateTime': track.updateTime,
                            'duration': track.duration
                        })
                    
                    log(f"[快速解析] 准备缓存专辑 {album_id} 第{page}页数据...", 'info')
                    cache.cache_album_page(album_id, page, page_size, tracks_data, total_count, log_func)
                    log(f"[快速解析] ✅ 专辑页面缓存写入完成", 'info')
                    
                except Exception as e:
                    log(f"[快速解析] ❌ 专辑页面缓存写入失败: {e}", 'warning')
                
                return tracks
                
            else:
                log(f"[快速解析] 请求失败: {response.status_code}", 'error')
                if attempt < max_retries - 1:
                    wait_time = random.uniform(5.0, 10.0)
                    log(f"[快速解析] 等待 {wait_time:.1f} 秒后重试", 'info')
                    time.sleep(wait_time)
                    
        except Exception as e:
            if attempt < max_retries - 1:
                wait_time = random.uniform(5.0, 10.0)
                log(f"[快速解析] 请求异常，等待 {wait_time:.1f} 秒后重试: {e}", 'warning')
                time.sleep(wait_time)
            else:
                log(f"[快速解析] 请求失败: {e}", 'error')
                raise
                
    return []


class SmartConcurrentParser:
    """智能并发解析器，支持动态延迟调整"""
    
    def __init__(self, album_id: int, log_func=None, max_workers: int = 3):
        self.album_id = album_id
        self.log_func = log_func
        self.max_workers = max_workers
        
        # 智能延迟参数
        self.base_delay = 2.0  # 基础延迟
        self.success_count = 0
        self.total_count = 0
        self.current_delay = self.base_delay
        
    def log(self, msg, level='info'):
        if self.log_func:
            try:
                self.log_func(msg, level=level)
            except TypeError:
                self.log_func(msg)
        else:
            print(msg)
    
    def update_delay_strategy(self, success: bool):
        """根据成功率动态调整延迟策略"""
        self.total_count += 1
        if success:
            self.success_count += 1
        
        success_rate = self.success_count / self.total_count if self.total_count > 0 else 0
        
        # 动态调整延迟
        if success_rate > 0.8:  # 成功率高，减少延迟
            self.current_delay = max(1.0, self.current_delay * 0.9)
        elif success_rate < 0.5:  # 成功率低，增加延迟
            self.current_delay = min(10.0, self.current_delay * 1.5)
        
        self.log(f"[智能延迟] 成功率: {success_rate:.1%} ({self.success_count}/{self.total_count}), 当前延迟: {self.current_delay:.1f}秒", 'info')
    
    def parse_single_track_url(self, track_id: int) -> tuple:
        """解析单个曲目的URL，返回(track_id, crypted_url, decrypted_url, success)"""
        import time
        import random
        import json
        
        try:
            # 尝试从缓存获取URL
            try:
                from utils.sqlite_cache import get_sqlite_cache
                cache = get_sqlite_cache()
                cached_track = cache.get_cached_track(track_id, self.album_id, self.log_func)
                if cached_track and cached_track.crypted_url:
                    self.log(f"[并发解析] Track {track_id} 使用缓存URL", 'info')
                    self.update_delay_strategy(True)
                    return track_id, cached_track.crypted_url, cached_track.decrypted_url, True
            except Exception as e:
                self.log(f"[缓存] 读取缓存失败: {e}", 'warning')
            # 使用智能延迟
            delay = random.uniform(self.current_delay * 0.8, self.current_delay * 1.2)
            time.sleep(delay)
            
            url = f"https://www.ximalaya.com/mobile-playpage/track/v3/baseInfo/{self.album_id}"
            params = {
                "device": "web",
                "trackId": track_id,
                "trackQualityLevel": 1
            }
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Accept": "application/json",
                "Cookie": XIMALAYA_COOKIES
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            
            if response.status_code == 200:
                data = response.json()
                
                # 检查风控
                if data.get("ret") == 1001 or "系统繁忙" in data.get("msg", ""):
                    self.log(f"[并发解析] Track {track_id} 风控触发", 'warning')
                    self.update_delay_strategy(False)
                    return track_id, "", "", False
                
                play_url_list = data.get("trackInfo", {}).get("playUrlList", [])
                if play_url_list:
                    crypted_url = play_url_list[0].get("url", "")
                    decrypted_url = decrypt_url(crypted_url)
                    
                    # 缓存新解析的URL
                    self.log(f"[并发解析] 准备缓存解析结果 Track {track_id}...", 'info')
                    try:
                        from utils.sqlite_cache import get_sqlite_cache
                        cache = get_sqlite_cache()
                        self.log(f"[并发解析] 开始写入缓存: crypted_len={len(crypted_url)}, decrypted_len={len(decrypted_url)}", 'info')
                        cache.cache_track(track_id, self.album_id, 
                                        crypted_url=crypted_url, 
                                        decrypted_url=decrypted_url, 
                                        log_func=self.log_func)
                        self.log(f"[并发解析] ✅ 缓存写入调用完成 Track {track_id}", 'info')
                    except Exception as e:
                        self.log(f"[并发解析] ❌ 缓存保存失败 Track {track_id}: {e}", 'warning')
                        import traceback
                        self.log(f"[并发解析] 详细错误: {traceback.format_exc()}", 'warning')
                    
                    self.log(f"[并发解析] Track {track_id} 解析成功", 'info')
                    self.update_delay_strategy(True)
                    return track_id, crypted_url, decrypted_url, True
                else:
                    self.log(f"[并发解析] Track {track_id} 无播放链接", 'warning')
                    self.update_delay_strategy(False)
                    return track_id, "", "", False
            else:
                self.log(f"[并发解析] Track {track_id} HTTP错误: {response.status_code}", 'error')
                self.update_delay_strategy(False)
                return track_id, "", "", False
                
        except Exception as e:
            self.log(f"[并发解析] Track {track_id} 异常: {e}", 'error')
            self.update_delay_strategy(False)
            return track_id, "", "", False
    
    def parse_tracks_concurrent(self, tracks: List[Track], progress_callback=None) -> List[Track]:
        """并发解析多个曲目的URL"""
        import concurrent.futures
        import threading
        
        if not tracks:
            return tracks
        
        self.log(f"[并发解析] 开始并发解析 {len(tracks)} 个曲目，并发数: {self.max_workers}", 'info')
        
        # 准备需要解析的track_id列表
        track_ids = [track.trackId for track in tracks]
        track_dict = {track.trackId: track for track in tracks}
        
        completed = 0
        lock = threading.Lock()
        
        def update_progress():
            nonlocal completed
            with lock:
                completed += 1
                if progress_callback:
                    progress_callback(completed, len(tracks))
        
        # 使用线程池并发处理
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 提交所有任务
            future_to_track_id = {
                executor.submit(self.parse_single_track_url, track_id): track_id 
                for track_id in track_ids
            }
            
            # 收集结果
            for future in concurrent.futures.as_completed(future_to_track_id):
                track_id, crypted_url, decrypted_url, success = future.result()
                
                # 更新track对象
                if track_id in track_dict:
                    track = track_dict[track_id]
                    track.cryptedUrl = crypted_url
                    track.url = decrypted_url
                
                update_progress()
        
        success_count = sum(1 for track in tracks if track.url)
        self.log(f"[并发解析] 完成！成功解析 {success_count}/{len(tracks)} 个曲目", 'info')
        
        return tracks


def parse_tracks_concurrent(tracks: List[Track], album_id: int, log_func=None, progress_callback=None, max_workers: int = 3) -> List[Track]:
    """并发解析曲目URL的便捷函数"""
    parser = SmartConcurrentParser(album_id, log_func, max_workers)
    return parser.parse_tracks_concurrent(tracks, progress_callback)

import sqlite3
import time
import json
import os
from dataclasses import dataclass, asdict
from typing import Dict, Optional, List, Any
import requests
from datetime import datetime, timedelta
import threading

@dataclass
class CachedTrack:
    """缓存的曲目信息"""
    track_id: int
    album_id: int
    title: str = ""
    duration: int = 0
    crypted_url: str = ""
    decrypted_url: str = ""
    file_size: int = 0
    cache_time: float = 0.0
    last_verified: float = 0.0
    is_valid: bool = True
    verify_count: int = 0
    extra_data: str = ""  # JSON格式存储额外数据

class SqliteCache:
    """SQLite缓存管理器"""
    
    def __init__(self, cache_dir: str = None, db_name: str = "track_cache.db"):
        if cache_dir is None:
            cache_dir = os.path.join(os.getcwd(), 'cache')
        
        self.cache_dir = cache_dir
        self.db_path = os.path.join(cache_dir, db_name)
        
        # 缓存配置
        self.cache_expire_hours = 24  # 缓存24小时后过期
        self.verify_expire_hours = 12  # 12小时后重新验证URL有效性
        self.max_verify_attempts = 3  # 最多验证3次失败后标记为无效
        
        # 线程锁
        self._lock = threading.Lock()
        
        os.makedirs(cache_dir, exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """初始化数据库表"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute('''
                CREATE TABLE IF NOT EXISTS track_cache (
                    track_id INTEGER NOT NULL,
                    album_id INTEGER NOT NULL,
                    title TEXT DEFAULT '',
                    duration INTEGER DEFAULT 0,
                    crypted_url TEXT DEFAULT '',
                    decrypted_url TEXT DEFAULT '',
                    file_size INTEGER DEFAULT 0,
                    cache_time REAL NOT NULL,
                    last_verified REAL NOT NULL,
                    is_valid BOOLEAN DEFAULT 1,
                    verify_count INTEGER DEFAULT 0,
                    extra_data TEXT DEFAULT '',
                    PRIMARY KEY (track_id, album_id)
                )
            ''')
            
            # 创建专辑页面缓存表
            conn.execute('''
                CREATE TABLE IF NOT EXISTS album_page_cache (
                    album_id INTEGER NOT NULL,
                    page INTEGER NOT NULL,
                    page_size INTEGER NOT NULL,
                    tracks_data TEXT NOT NULL,
                    total_count INTEGER DEFAULT 0,
                    cache_time REAL NOT NULL,
                    PRIMARY KEY (album_id, page, page_size)
                )
            ''')
            
            # 创建索引
            conn.execute('CREATE INDEX IF NOT EXISTS idx_cache_time ON track_cache(cache_time)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_last_verified ON track_cache(last_verified)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_album_id ON track_cache(album_id)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_is_valid ON track_cache(is_valid)')
            
            # 专辑页面缓存索引
            conn.execute('CREATE INDEX IF NOT EXISTS idx_album_page_cache_time ON album_page_cache(cache_time)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_album_page_album_id ON album_page_cache(album_id)')
            
            conn.commit()
    
    def _is_url_expired(self, cache_time: float) -> bool:
        """检查URL是否过期"""
        current_time = time.time()
        cache_age = current_time - cache_time
        return cache_age > (self.cache_expire_hours * 3600)
    
    def _should_verify_url(self, last_verified: float) -> bool:
        """检查是否需要验证URL有效性"""
        current_time = time.time()
        verify_age = current_time - last_verified
        return verify_age > (self.verify_expire_hours * 3600)
    
    def _verify_url_validity(self, url: str) -> bool:
        """验证URL是否仍然有效"""
        if not url:
            return False
            
        try:
            # 发送HEAD请求检查URL是否可访问
            response = requests.head(url, timeout=10, allow_redirects=True)
            return response.status_code == 200
        except Exception:
            return False
    
    def get_cached_track(self, track_id: int, album_id: int, log_func=None) -> Optional[CachedTrack]:
        """获取缓存的曲目信息"""
        def log(msg, level='info'):
            if log_func:
                try:
                    log_func(msg, level=level)
                except TypeError:
                    log_func(msg)
            else:
                print(msg)
        
        log(f"[缓存-读取] 查询 Track {track_id} (Album {album_id}) 缓存...", 'info')
        
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    
                    log(f"[缓存-读取] 执行数据库查询...", 'info')
                    cursor.execute('''
                        SELECT * FROM track_cache 
                        WHERE track_id = ? AND album_id = ?
                    ''', (track_id, album_id))
                    
                    row = cursor.fetchone()
                    if not row:
                        log(f"[缓存-读取] ❌ Track {track_id} 无缓存记录", 'info')
                        return None
                    
                    log(f"[缓存-读取] ✅ 找到缓存记录 Track {track_id}", 'info')
                    log(f"[缓存-读取] 记录详情: is_valid={row['is_valid']}, cache_time={row['cache_time']}, crypted_url_len={len(row['crypted_url'])}", 'info')
                    
                    # 转换为CachedTrack对象
                    cached_track = CachedTrack(
                        track_id=row['track_id'],
                        album_id=row['album_id'],
                        title=row['title'],
                        duration=row['duration'],
                        crypted_url=row['crypted_url'],
                        decrypted_url=row['decrypted_url'],
                        file_size=row['file_size'],
                        cache_time=row['cache_time'],
                        last_verified=row['last_verified'],
                        is_valid=bool(row['is_valid']),
                        verify_count=row['verify_count'],
                        extra_data=row['extra_data']
                    )
                    
                    # 检查缓存是否过期
                    if self._is_url_expired(cached_track.cache_time):
                        log(f"[缓存] Track {track_id} 缓存已过期", 'warning')
                        self._delete_cached_track(track_id, album_id)
                        return None
                    
                    # 检查是否需要验证URL有效性
                    if (self._should_verify_url(cached_track.last_verified) and 
                        cached_track.is_valid and cached_track.decrypted_url):
                        
                        log(f"[缓存] 验证 Track {track_id} URL有效性", 'info')
                        
                        if self._verify_url_validity(cached_track.decrypted_url):
                            # URL仍然有效，更新验证时间
                            self._update_verify_info(track_id, album_id, True, 0)
                            cached_track.last_verified = time.time()
                            cached_track.verify_count = 0
                            log(f"[缓存] Track {track_id} URL验证通过", 'info')
                        else:
                            # URL无效，增加验证计数
                            new_verify_count = cached_track.verify_count + 1
                            
                            if new_verify_count >= self.max_verify_attempts:
                                # 超过最大验证次数，标记为无效
                                self._update_verify_info(track_id, album_id, False, new_verify_count)
                                log(f"[缓存] Track {track_id} URL多次验证失败，标记为无效", 'warning')
                                return None
                            else:
                                self._update_verify_info(track_id, album_id, True, new_verify_count)
                                log(f"[缓存] Track {track_id} URL验证失败 ({new_verify_count}/{self.max_verify_attempts})", 'warning')
                                return None
                    
                    # 返回有效的缓存
                    if cached_track.is_valid:
                        cache_age_hours = (time.time() - cached_track.cache_time) / 3600
                        log(f"[缓存-读取] ✅ 返回有效缓存 Track {track_id} (缓存时间: {cache_age_hours:.1f}小时)", 'info')
                        log(f"[缓存-读取] 返回数据: crypted_url={cached_track.crypted_url[:50]}{'...' if len(cached_track.crypted_url) > 50 else ''}", 'info')
                        log(f"[缓存-读取] 返回数据: decrypted_url={cached_track.decrypted_url[:50]}{'...' if len(cached_track.decrypted_url) > 50 else ''}", 'info')
                        return cached_track
                    else:
                        log(f"[缓存-读取] ❌ 缓存无效 Track {track_id} (is_valid={cached_track.is_valid})", 'warning')
                    
                    return None
                    
            except Exception as e:
                log(f"[缓存-读取] ❌ 获取缓存失败 Track {track_id}: {e}", 'error')
                import traceback
                log(f"[缓存-读取] 详细错误: {traceback.format_exc()}", 'error')
                return None
    
    def cache_track(self, track_id: int, album_id: int, title: str = "", 
                   duration: int = 0, crypted_url: str = "", decrypted_url: str = "",
                   file_size: int = 0, extra_data: Dict = None, log_func=None):
        """缓存曲目信息"""
        def log(msg, level='info'):
            if log_func:
                try:
                    log_func(msg, level=level)
                except TypeError:
                    log_func(msg)
            else:
                print(msg)
        
        log(f"[缓存-写入] 准备缓存 Track {track_id} (Album {album_id})", 'info')
        log(f"[缓存-写入] 数据: title='{title}', duration={duration}, crypted_url_len={len(crypted_url)}, decrypted_url_len={len(decrypted_url)}", 'info')
        
        with self._lock:
            try:
                current_time = time.time()
                extra_json = json.dumps(extra_data or {}, ensure_ascii=False)
                
                log(f"[缓存-写入] 开始数据库操作...", 'info')
                
                with sqlite3.connect(self.db_path) as conn:
                    # 检查是否已存在
                    cursor = conn.cursor()
                    cursor.execute('SELECT COUNT(*) FROM track_cache WHERE track_id = ? AND album_id = ?', 
                                 (track_id, album_id))
                    exists = cursor.fetchone()[0] > 0
                    action = "更新" if exists else "新增"
                    
                    conn.execute('''
                        INSERT OR REPLACE INTO track_cache 
                        (track_id, album_id, title, duration, crypted_url, decrypted_url, 
                         file_size, cache_time, last_verified, is_valid, verify_count, extra_data)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0, ?)
                    ''', (track_id, album_id, title, duration, crypted_url, decrypted_url,
                          file_size, current_time, current_time, extra_json))
                    
                    conn.commit()
                    
                    # 验证写入结果
                    cursor.execute('SELECT COUNT(*) FROM track_cache WHERE track_id = ? AND album_id = ?', 
                                 (track_id, album_id))
                    write_success = cursor.fetchone()[0] > 0
                
                if write_success:
                    log(f"[缓存-写入] ✅ {action}缓存成功 Track {track_id} (Album {album_id})", 'info')
                    log(f"[缓存-写入] 缓存内容: crypted_url={crypted_url[:50]}{'...' if len(crypted_url) > 50 else ''}", 'info')
                else:
                    log(f"[缓存-写入] ❌ 写入验证失败 Track {track_id}", 'error')
                
            except Exception as e:
                log(f"[缓存-写入] ❌ 保存缓存失败 Track {track_id}: {e}", 'error')
                import traceback
                log(f"[缓存-写入] 详细错误: {traceback.format_exc()}", 'error')
    
    def _update_verify_info(self, track_id: int, album_id: int, is_valid: bool, verify_count: int):
        """更新验证信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    UPDATE track_cache 
                    SET last_verified = ?, is_valid = ?, verify_count = ?
                    WHERE track_id = ? AND album_id = ?
                ''', (time.time(), is_valid, verify_count, track_id, album_id))
                conn.commit()
        except Exception:
            pass
    
    def _delete_cached_track(self, track_id: int, album_id: int):
        """删除缓存的曲目"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    DELETE FROM track_cache 
                    WHERE track_id = ? AND album_id = ?
                ''', (track_id, album_id))
                conn.commit()
        except Exception:
            pass
    
    def get_album_cached_tracks(self, album_id: int) -> List[CachedTrack]:
        """获取专辑的所有缓存曲目"""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    
                    cursor.execute('''
                        SELECT * FROM track_cache 
                        WHERE album_id = ? AND is_valid = 1
                        ORDER BY track_id
                    ''', (album_id,))
                    
                    tracks = []
                    for row in cursor.fetchall():
                        if not self._is_url_expired(row['cache_time']):
                            tracks.append(CachedTrack(
                                track_id=row['track_id'],
                                album_id=row['album_id'],
                                title=row['title'],
                                duration=row['duration'],
                                crypted_url=row['crypted_url'],
                                decrypted_url=row['decrypted_url'],
                                file_size=row['file_size'],
                                cache_time=row['cache_time'],
                                last_verified=row['last_verified'],
                                is_valid=bool(row['is_valid']),
                                verify_count=row['verify_count'],
                                extra_data=row['extra_data']
                            ))
                    
                    return tracks
                    
            except Exception as e:
                print(f"获取专辑缓存失败: {e}")
                return []
    
    def cleanup_expired_cache(self):
        """清理过期缓存"""
        with self._lock:
            try:
                current_time = time.time()
                expire_time = self.cache_expire_hours * 3600
                
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        DELETE FROM track_cache 
                        WHERE ? - cache_time > ?
                    ''', (current_time, expire_time))
                    
                    deleted_count = cursor.rowcount
                    conn.commit()
                    
                    if deleted_count > 0:
                        print(f"[缓存] 清理了 {deleted_count} 个过期缓存")
                        
            except Exception as e:
                print(f"清理过期缓存失败: {e}")
    
    def get_cache_stats(self) -> Dict:
        """获取缓存统计信息"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 总数
                cursor.execute('SELECT COUNT(*) FROM track_cache')
                total_count = cursor.fetchone()[0]
                
                # 有效数
                cursor.execute('SELECT COUNT(*) FROM track_cache WHERE is_valid = 1')
                valid_count = cursor.fetchone()[0]
                
                # 过期数
                current_time = time.time()
                expire_time = self.cache_expire_hours * 3600
                cursor.execute('SELECT COUNT(*) FROM track_cache WHERE ? - cache_time > ?', 
                             (current_time, expire_time))
                expired_count = cursor.fetchone()[0]
                
                # 专辑数
                cursor.execute('SELECT COUNT(DISTINCT album_id) FROM track_cache WHERE is_valid = 1')
                album_count = cursor.fetchone()[0]
                
                # 专辑页面缓存统计
                cursor.execute('SELECT COUNT(*) FROM album_page_cache')
                album_page_total = cursor.fetchone()[0]
                
                # 过期的专辑页面缓存
                album_page_expire_time = 6 * 3600  # 6小时
                cursor.execute('SELECT COUNT(*) FROM album_page_cache WHERE ? - cache_time > ?',
                             (current_time, album_page_expire_time))
                album_page_expired = cursor.fetchone()[0]
                
                # 专辑页面缓存的专辑数
                cursor.execute('SELECT COUNT(DISTINCT album_id) FROM album_page_cache')
                cached_albums = cursor.fetchone()[0]
                
                # 数据库大小
                db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0
                
                return {
                    'total': total_count,
                    'valid': valid_count,
                    'expired': expired_count,
                    'invalid': total_count - valid_count,
                    'albums': album_count,
                    'album_pages_total': album_page_total,
                    'album_pages_valid': album_page_total - album_page_expired,
                    'album_pages_expired': album_page_expired,
                    'cached_albums': cached_albums,
                    'db_path': self.db_path,
                    'db_size_mb': round(db_size / 1024 / 1024, 2)
                }
                
        except Exception as e:
            print(f"获取缓存统计失败: {e}")
            return {'error': str(e)}
    
    def clear_cache(self):
        """清空所有缓存"""
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.execute('DELETE FROM track_cache')
                    conn.commit()
                print("[缓存] 已清空所有缓存")
            except Exception as e:
                print(f"清空缓存失败: {e}")
    
    def migrate_from_json_cache(self, json_cache_file: str):
        """从JSON缓存迁移数据"""
        if not os.path.exists(json_cache_file):
            return
            
        try:
            with open(json_cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            migrated_count = 0
            for key, item in data.items():
                try:
                    self.cache_track(
                        track_id=item['track_id'],
                        album_id=item['album_id'],
                        crypted_url=item['crypted_url'],
                        decrypted_url=item['decrypted_url']
                    )
                    migrated_count += 1
                except Exception as e:
                    print(f"迁移缓存项失败 {key}: {e}")
            
            print(f"[缓存] 从JSON迁移了 {migrated_count} 个缓存项")
            
        except Exception as e:
            print(f"迁移JSON缓存失败: {e}")
    
    def cache_album_page(self, album_id: int, page: int, page_size: int, 
                        tracks_data: List[Dict], total_count: int, log_func=None):
        """缓存专辑页面数据"""
        def log(msg, level='info'):
            if log_func:
                try:
                    log_func(msg, level=level)
                except TypeError:
                    log_func(msg)
            else:
                print(msg)
        
        log(f"[专辑缓存-写入] 准备缓存专辑 {album_id} 第{page}页 (每页{page_size}个)", 'info')
        log(f"[专辑缓存-写入] 数据: tracks_count={len(tracks_data)}, total_count={total_count}", 'info')
        
        with self._lock:
            try:
                current_time = time.time()
                tracks_json = json.dumps(tracks_data, ensure_ascii=False)
                
                log(f"[专辑缓存-写入] 开始数据库操作...", 'info')
                
                with sqlite3.connect(self.db_path) as conn:
                    # 检查是否已存在
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT COUNT(*) FROM album_page_cache 
                        WHERE album_id = ? AND page = ? AND page_size = ?
                    ''', (album_id, page, page_size))
                    exists = cursor.fetchone()[0] > 0
                    action = "更新" if exists else "新增"
                    
                    conn.execute('''
                        INSERT OR REPLACE INTO album_page_cache 
                        (album_id, page, page_size, tracks_data, total_count, cache_time)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (album_id, page, page_size, tracks_json, total_count, current_time))
                    
                    conn.commit()
                    
                    # 验证写入结果
                    cursor.execute('''
                        SELECT COUNT(*) FROM album_page_cache 
                        WHERE album_id = ? AND page = ? AND page_size = ?
                    ''', (album_id, page, page_size))
                    write_success = cursor.fetchone()[0] > 0
                
                if write_success:
                    log(f"[专辑缓存-写入] ✅ {action}专辑页面缓存成功 Album {album_id} 第{page}页", 'info')
                else:
                    log(f"[专辑缓存-写入] ❌ 写入验证失败 Album {album_id} 第{page}页", 'error')
                
            except Exception as e:
                log(f"[专辑缓存-写入] ❌ 保存专辑页面缓存失败 Album {album_id} 第{page}页: {e}", 'error')
                import traceback
                log(f"[专辑缓存-写入] 详细错误: {traceback.format_exc()}", 'error')
    
    def get_cached_album_page(self, album_id: int, page: int, page_size: int, 
                             log_func=None) -> Optional[Dict]:
        """获取缓存的专辑页面数据"""
        def log(msg, level='info'):
            if log_func:
                try:
                    log_func(msg, level=level)
                except TypeError:
                    log_func(msg)
            else:
                print(msg)
        
        log(f"[专辑缓存-读取] 查询专辑 {album_id} 第{page}页缓存 (每页{page_size}个)...", 'info')
        
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    
                    log(f"[专辑缓存-读取] 执行数据库查询...", 'info')
                    cursor.execute('''
                        SELECT * FROM album_page_cache 
                        WHERE album_id = ? AND page = ? AND page_size = ?
                    ''', (album_id, page, page_size))
                    
                    row = cursor.fetchone()
                    if not row:
                        log(f"[专辑缓存-读取] ❌ 专辑 {album_id} 第{page}页无缓存记录", 'info')
                        return None
                    
                    log(f"[专辑缓存-读取] ✅ 找到专辑页面缓存记录", 'info')
                    log(f"[专辑缓存-读取] 记录详情: cache_time={row['cache_time']}, total_count={row['total_count']}", 'info')
                    
                    # 检查缓存是否过期 (专辑页面缓存6小时过期)
                    cache_age = time.time() - row['cache_time']
                    if cache_age > (6 * 3600):  # 6小时过期
                        log(f"[专辑缓存-读取] ❌ 专辑页面缓存已过期 (缓存时间: {cache_age/3600:.1f}小时)", 'warning')
                        # 删除过期缓存
                        conn.execute('''
                            DELETE FROM album_page_cache 
                            WHERE album_id = ? AND page = ? AND page_size = ?
                        ''', (album_id, page, page_size))
                        conn.commit()
                        return None
                    
                    # 解析tracks数据
                    tracks_data = json.loads(row['tracks_data'])
                    
                    cache_age_hours = cache_age / 3600
                    log(f"[专辑缓存-读取] ✅ 返回有效专辑页面缓存 (缓存时间: {cache_age_hours:.1f}小时)", 'info')
                    log(f"[专辑缓存-读取] 返回数据: tracks_count={len(tracks_data)}, total_count={row['total_count']}", 'info')
                    
                    return {
                        'tracks': tracks_data,
                        'total_count': row['total_count'],
                        'cache_time': row['cache_time']
                    }
                    
            except Exception as e:
                log(f"[专辑缓存-读取] ❌ 获取专辑页面缓存失败: {e}", 'error')
                import traceback
                log(f"[专辑缓存-读取] 详细错误: {traceback.format_exc()}", 'error')
                return None
    
    def cleanup_expired_album_pages(self):
        """清理过期的专辑页面缓存"""
        with self._lock:
            try:
                current_time = time.time()
                expire_time = 6 * 3600  # 6小时过期
                
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                        DELETE FROM album_page_cache 
                        WHERE ? - cache_time > ?
                    ''', (current_time, expire_time))
                    
                    deleted_count = cursor.rowcount
                    conn.commit()
                    
                    if deleted_count > 0:
                        print(f"[专辑缓存] 清理了 {deleted_count} 个过期专辑页面缓存")
                        
            except Exception as e:
                print(f"清理过期专辑页面缓存失败: {e}")
    
    def get_tracks_cache_status(self, track_ids: List[int], album_id: int) -> Dict[int, Dict]:
        """批量获取曲目缓存状态（性能优化）"""
        if not track_ids:
            return {}
            
        with self._lock:
            try:
                with sqlite3.connect(self.db_path) as conn:
                    conn.row_factory = sqlite3.Row
                    cursor = conn.cursor()
                    
                    # 批量查询
                    placeholders = ','.join('?' * len(track_ids))
                    query = f'''
                        SELECT track_id, crypted_url, decrypted_url, is_valid
                        FROM track_cache 
                        WHERE track_id IN ({placeholders}) AND album_id = ? AND is_valid = 1
                    '''
                    
                    cursor.execute(query, track_ids + [album_id])
                    rows = cursor.fetchall()
                    
                    result = {}
                    for row in rows:
                        if row['crypted_url']:  # 只返回有URL的缓存
                            result[row['track_id']] = {
                                'crypted_url': row['crypted_url'],
                                'decrypted_url': row['decrypted_url'],
                                'is_valid': bool(row['is_valid'])
                            }
                    
                    return result
                    
            except Exception as e:
                return {}

# 全局缓存实例
_global_cache = None

def get_sqlite_cache() -> SqliteCache:
    """获取全局SQLite缓存实例"""
    global _global_cache
    if _global_cache is None:
        _global_cache = SqliteCache()
        # 尝试从旧的JSON缓存迁移
        json_cache_path = os.path.join(_global_cache.cache_dir, 'url_cache.json')
        if os.path.exists(json_cache_path):
            _global_cache.migrate_from_json_cache(json_cache_path)
    return _global_cache
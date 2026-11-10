#!/usr/bin/env python3
"""用带护栏的一键删除 API 提供存储报告服务（macOS + Windows + Linux）。

服务启动在 127.0.0.1、随机端口和随机会话 token 上，提供交互式报告，
并暴露 POST /action，执行报告允许的操作。按 Ctrl+C 停止；连续 30 分钟无请求也会自动退出。

用法：
    server.py <analysis.json>

安全模型，修改前必须阅读：
- 白名单：绿灯 `trash_paths` 允许删除或移入废纸篓；黄灯 `trash_paths` 只允许移入废纸篓。
  删除目标必须位于 HOME 内，且不能是受保护的数据根目录、链接、Git 工作区及其父/子目录。
  打开报告列出的应用时，额外允许平台的应用目录。
- 只绑定 127.0.0.1；每个 POST 都必须带会话 token；Host header 必须是
  127.0.0.1（阻断恶意页面的 DNS rebinding）。
- 两种模式："trash"（Finder / gio 进废纸篓，可恢复）和 "rm"
  （立即删除，不可恢复）。浏览器在发送请求前会二次确认。
- 条目标记 "clear_contents"：获准的目录逐个清空子项并保留目录本身，
  这样指向它的符号链接（例如 ~/.cache -> ~/.dev-cache/cache）不会悬空。
  没有该标记时整个目录被移除（原行为）。
"""
import json
import os
import secrets
import stat
from pathlib import Path
import shutil
import subprocess
import sys
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "..", "assets", "report_template.html")
HOME = os.path.realpath(os.path.expanduser("~"))
TOKEN = secrets.token_urlsafe(24)
LAST_ACTIVITY = time.monotonic()

DATA = {}
TPL = ""
RM_ALLOW = set()
TRASH_ALLOW = set()
OPEN_ALLOW = set()
MAX_BODY_BYTES = 64 * 1024
MAX_PATHS = 100


def json_for_script(value):
    """Serialize JSON without allowing data to close the script element."""
    return (
        json.dumps(value, ensure_ascii=False)
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


CLEAR_CONTENTS = set()  # realpath'd dirs whose CONTENTS are cleared, dir kept


def expand(p):
    return os.path.realpath(os.path.expanduser(p))


def load(src):
    with open(src, encoding="utf-8-sig") as f:
        data = json.load(f)
    with open(TEMPLATE, encoding="utf-8-sig") as f:
        tpl = f.read()
    # 三套白名单，权限从严到宽：
    #   rm    = 仅绿灯 trash_paths（可直接删的纯缓存）
    #   trash = 绿灯 + 橙灯 trash_paths（橙灯只准移废纸篓，不准直接删）
    #   open  = trash 全集 + 橙灯 path + 红灯 app_paths（仅"在文件管理器打开"，非破坏性）
    # clear_contents: 带该标志的条目，删除时只清目录内容、保留目录本身。
    rm_allow, trash_allow, open_allow = set(), set(), set()
    CLEAR_CONTENTS.clear()
    for it in data.get("green", []):
        clear = bool(it.get("clear_contents"))
        for p in (it.get("trash_paths") or []):
            rp = expand(p)
            rm_allow.add(rp); trash_allow.add(rp); open_allow.add(rp)
            if clear:
                CLEAR_CONTENTS.add(rp)
    for it in data.get("yellow", []):
        clear = bool(it.get("clear_contents"))
        for p in (it.get("trash_paths") or []):
            rp = expand(p)
            trash_allow.add(rp); open_allow.add(rp)
            if clear:
                CLEAR_CONTENTS.add(rp)
        if it.get("path"):
            rp = expand(it["path"])
            if os.path.exists(rp):
                open_allow.add(rp)
    # 红灯只允许"打开"（应用本体在 /Applications，删除让用户在访达里自己卸）
    for it in data.get("red", []):
        for p in (it.get("app_paths") or []):
            rp = expand(p)
            if os.path.exists(rp):
                open_allow.add(rp)
    return data, tpl, rm_allow, trash_allow, open_allow


def clear_contents(directory, action):
    """对 `directory` 的每个子项执行 `action`，保留目录本身。

    该目录可能被符号链接引用（例如 ~/.cache -> ~/.dev-cache/cache），
    整体删除会让这些链接悬空。用 scandir 枚举子项（含隐藏文件），
    每个子项原样交给 `action`——链接仍是链接（绝不跟随），
    与 hard_delete / move_to_trash 的语义一致。
    """
    for entry in sorted(os.scandir(directory), key=lambda e: e.name):
        if not os.path.lexists(entry.path):
            continue
        action(entry.path)


def move_to_trash(path):
    if sys.platform == "darwin":
        _trash_macos(path)
    elif sys.platform.startswith("win"):
        _trash_windows(path)
    elif sys.platform.startswith("linux"):
        _trash_linux(path)
    else:
        raise OSError("移到废纸篓仅支持 macOS / Windows / Linux")


def _trash_macos(path):
    # 通过 osascript 让 Finder 删除 -> macOS 废纸篓，可恢复。首次运行可能弹出
    # Finder 自动化权限请求。失败时回退为移动到 ~/.Trash。
    script = 'tell application "Finder" to delete (POSIX file %s as alias)' % json.dumps(path)
    r = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    if r.returncode != 0:
        dest = os.path.join(HOME, ".Trash",
                            os.path.basename(path.rstrip("/")) + "." + time.strftime("%H%M%S"))
        shutil.move(path, dest)


def _trash_windows(path):
    # 通过 SHFileOperationW + FOF_ALLOWUNDO 送进回收站（stdlib ctypes）。
    # CI 无法点击桌面回收站，这部分需在真实 Windows 机器上验证。
    import ctypes
    from ctypes import wintypes

    class SHFILEOPSTRUCTW(ctypes.Structure):
        _fields_ = [
            ("hwnd", wintypes.HWND),
            ("wFunc", wintypes.UINT),
            ("pFrom", wintypes.LPCWSTR),
            ("pTo", wintypes.LPCWSTR),
            ("fFlags", ctypes.c_uint16),
            ("fAnyOperationsAborted", wintypes.BOOL),
            ("hNameMappings", ctypes.c_void_p),
            ("lpszProgressTitle", wintypes.LPCWSTR),
        ]

    FO_DELETE = 3
    FOF_ALLOWUNDO = 0x0040
    FOF_NOCONFIRMATION = 0x0010
    FOF_SILENT = 0x0004
    op = SHFILEOPSTRUCTW()
    op.wFunc = FO_DELETE
    op.pFrom = os.path.abspath(path) + "\x00\x00"  # double-null terminated list
    op.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT
    rc = ctypes.windll.shell32.SHFileOperationW(ctypes.byref(op))
    if op.fAnyOperationsAborted:
        raise OSError("回收站操作已取消，未完成")
    if rc != 0 and not (rc == 2 and not os.path.exists(path)):
        raise OSError("SHFileOperation failed (code %d)" % rc)


def _trash_linux(path):
    # gio trash -> XDG 废纸篓（~/.local/share/Trash），可恢复。需要 GIO
    # （GNOME 和多数桌面自带）；没有时回退到 trash-cli 的 `trash`。
    if shutil.which("gio"):
        r = subprocess.run(["gio", "trash", path], capture_output=True, text=True)
        if r.returncode == 0:
            return
        err = (r.stderr or r.stdout or "").strip()
    elif shutil.which("trash"):
        r = subprocess.run(["trash", path], capture_output=True, text=True)
        if r.returncode == 0:
            return
        err = (r.stderr or "").strip()
    else:
        err = "未找到 gio 或 trash 命令"
    raise OSError(err or "gio trash 失败")


def is_link(path):
    st = os.lstat(path)
    return stat.S_ISLNK(st.st_mode) or getattr(st, "st_reparse_tag", 0) in (0xA0000003, 0xA000000C)


def validate_path(path, mode, allow):
    raw = os.path.abspath(os.path.expanduser(path))
    rp = expand(path)
    if rp not in allow:
        raise ValueError("路径不在白名单：" + path)
    roots = [HOME]
    if mode == "open":
        if sys.platform == "darwin":
            roots.append("/Applications")
        elif sys.platform.startswith("win"):
            roots.extend(os.path.realpath(os.environ[k]) for k in ("ProgramFiles", "ProgramFiles(x86)") if k in os.environ)
    if not any(rp == base or rp.startswith(base + os.sep) for base in roots):
        raise ValueError("路径越界：" + path)
    if mode != "open":
        protected = {HOME, os.path.join(HOME, "Library"), os.path.join(HOME, "AppData")}
        if rp in protected or (os.path.lexists(raw) and is_link(raw)):
            raise ValueError("不能清理主目录、数据根目录或链接：" + path)
        # A git checkout/worktree is not disposable cache, including its children.
        if any((parent / ".git").exists() or parent.name == ".git" for parent in (Path(rp), *Path(rp).parents)):
            raise ValueError("项目或工作区请使用项目自身的清理流程：" + path)
        def fail(error):
            raise error
        if os.path.isdir(rp):
            for base, dirs, files in os.walk(rp, followlinks=False, onerror=fail):
                if ".git" in dirs or ".git" in files:
                    raise ValueError("目录包含项目或工作区：" + path)
                dirs[:] = [d for d in dirs if not is_link(os.path.join(base, d))]
    return rp


def hard_delete(path):
    def readonly_retry(func, target, exc_info):
        if not isinstance(exc_info[1], PermissionError):
            raise exc_info[1]
        if is_link(target):
            raise exc_info[1]
        os.chmod(target, os.stat(target).st_mode | stat.S_IWUSR)
        func(target)
    if os.path.isdir(path) and not is_link(path):
        # Go caches contain read-only directories; unlink requires a writable parent.
        def fail(error):
            raise error
        for base, dirs, files in os.walk(path, followlinks=False, onerror=fail):
            os.chmod(base, os.stat(base).st_mode | stat.S_IRWXU)
            dirs[:] = [d for d in dirs if not is_link(os.path.join(base, d))]
        shutil.rmtree(path, onerror=readonly_retry)
    else:
        try:
            os.remove(path)
        except PermissionError:
            readonly_retry(os.remove, path, sys.exc_info())


def open_in_file_manager(path):
    # 非破坏性：在访达 / 资源管理器里打开该位置，方便用户自己审查删除
    target = path if os.path.isdir(path) else os.path.dirname(path)
    if sys.platform == "darwin":
        # .app 是 bundle，对它用 open 会"启动应用"而非显示；必须用 open -R 在访达里选中。
        if target.rstrip("/").endswith(".app"):
            r = subprocess.run(["open", "-R", target], capture_output=True, text=True)
            if r.returncode != 0:
                raise OSError((r.stderr or "open -R 失败").strip())
            return
        # 普通文件夹：先试直接打开看内容；沙盒容器（如微信）open 会报 -10814，
        # 退回 open -R 在父目录里选中它。两者都失败才算错。
        r = subprocess.run(["open", target], capture_output=True, text=True)
        if r.returncode != 0:
            r2 = subprocess.run(["open", "-R", target], capture_output=True, text=True)
            if r2.returncode != 0:
                raise OSError((r.stderr or r2.stderr or "open 失败").strip())
    elif sys.platform.startswith("win"):
        subprocess.run(["explorer", target])  # explorer 退出码不可靠，不据此判成败
    elif sys.platform.startswith("linux"):
        r = subprocess.run(["xdg-open", target], capture_output=True, text=True)
        if r.returncode != 0:
            raise OSError((r.stderr or "xdg-open 失败").strip())
    else:
        raise OSError("打开文件夹仅支持 macOS / Windows / Linux")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _send(self, code, body, ctype="application/json"):
        b = body.encode("utf-8") if isinstance(body, str) else body
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def valid_host(self):
        global LAST_ACTIVITY
        host = (self.headers.get("Host") or "").split(":")[0]
        if host not in ("127.0.0.1", "localhost"):
            self._send(403, json.dumps({"ok": False, "error": "host 不被允许"}))
            return False
        LAST_ACTIVITY = time.monotonic()
        return True

    def do_GET(self):
        if not self.valid_host():
            return
        if self.path in ("/", "/index.html"):
            blob = json_for_script(DATA)
            cfg = json_for_script({"token": TOKEN, "endpoint": "/action"})
            html = TPL.replace("__REPORT_DATA__", blob).replace("__DELETE_CONFIG__", cfg)
            self._send(200, html, "text/html; charset=utf-8")
        else:
            self._send(404, "未找到", "text/plain")

    def do_POST(self):
        if self.path != "/action":
            self._send(404, json.dumps({"ok": False, "error": "未找到"}))
            return
        if not self.valid_host():
            return
        raw_length = self.headers.get("Content-Length")
        try:
            n = int(raw_length)
        except (TypeError, ValueError):
            self._send(400, json.dumps({"ok": False, "error": "Content-Length 无效"}))
            return
        if n <= 0:
            self._send(400, json.dumps({"ok": False, "error": "请求体不能为空"}))
            return
        if n > MAX_BODY_BYTES:
            self._send(413, json.dumps({"ok": False, "error": "请求体过大"}))
            return
        try:
            raw = self.rfile.read(n)
            if len(raw) != n:
                raise ValueError("请求体长度不完整")
            req = json.loads(raw)
        except Exception:
            self._send(400, json.dumps({"ok": False, "error": "请求格式错误"}))
            return
        if not isinstance(req, dict):
            self._send(400, json.dumps({"ok": False, "error": "请求必须是对象"}))
            return
        if req.get("token") != TOKEN:
            self._send(403, json.dumps({"ok": False, "error": "token 校验失败"}))
            return
        mode = req.get("mode")
        allow = {"rm": RM_ALLOW, "trash": TRASH_ALLOW, "open": OPEN_ALLOW}.get(mode)
        if allow is None:
            self._send(400, json.dumps({"ok": False, "error": "未知操作"}))
            return
        paths = req.get("paths")
        if not isinstance(paths, list) or not paths or not all(isinstance(p, str) for p in paths):
            self._send(400, json.dumps({"ok": False, "error": "paths 必须是非空路径数组"}))
            return
        if len(paths) > MAX_PATHS:
            self._send(413, json.dumps({"ok": False, "error": "单次请求路径过多"}))
            return
        try:
            resolved = [validate_path(p, mode, allow) for p in paths]
        except (ValueError, OSError) as e:
            self._send(403, json.dumps({"ok": False, "error": str(e)}))
            return
        done = []
        for p, rp in zip(paths, resolved):
            try:
                if mode == "open":
                    open_in_file_manager(rp)
                elif not os.path.exists(rp):
                    pass  # 已不存在，视作成功
                elif mode == "trash":
                    if rp in CLEAR_CONTENTS and os.path.isdir(rp):
                        clear_contents(rp, move_to_trash)
                    else:
                        move_to_trash(rp)
                else:
                    if rp in CLEAR_CONTENTS and os.path.isdir(rp):
                        clear_contents(rp, hard_delete)
                    else:
                        hard_delete(rp)
                done.append(p)
            except Exception as e:
                self._send(500, json.dumps({"ok": False, "error": str(e), "done": done}))
                return
        self._send(200, json.dumps({"ok": True, "done": done}))


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)
    global DATA, TPL, RM_ALLOW, TRASH_ALLOW, OPEN_ALLOW
    DATA, TPL, RM_ALLOW, TRASH_ALLOW, OPEN_ALLOW = load(sys.argv[1])
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    port = srv.server_address[1]
    url = "http://127.0.0.1:%d/" % port
    print("报告服务已启动：" + url, flush=True)
    print("绿灯可删 %d 项 | 橙灯可移废纸篓/打开文件夹 %d 项 | 页面上点" % (len(RM_ALLOW), len(TRASH_ALLOW) - len(RM_ALLOW)))
    print("用完按 Ctrl+C 停止；连续 30 分钟无请求自动退出。", flush=True)
    webbrowser.open(url)
    srv.timeout = 1
    try:
        while time.monotonic() - LAST_ACTIVITY < 1800:
            srv.handle_request()
    except KeyboardInterrupt:
        print("\n已停止服务。")
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()

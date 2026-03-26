"""半自动扫码进群 - 发图到文件传输助手，用户手机端识别进群，程序自动检测

扫描所有日期文件夹的二维码，每10张一批发送，用户扫完按回车继续下一批。
退出后记录进度，下次从未处理过的二维码开始。
"""

import sys
import os
import json
import time
import random
import pyautogui
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qr_scanner import scan_qr_from_image, _parse_filename
from wxauto import WeChat
from config import (
    GROUP_DB_FILE, MAX_GROUPS_PER_ACCOUNT,
    SEND_INTERVAL_MIN_DAYS, SEND_INTERVAL_MAX_DAYS,
    QR_CODE_ROOT, SUPPORTED_IMAGE_EXTS,
)

BATCH_SIZE = 10
START_FROM = 30  # 从第几条二维码开始（1-based），设为1则从头开始


def load_group_db():
    if os.path.isfile(GROUP_DB_FILE):
        with open(GROUP_DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"groups": []}


def save_group_db(db):
    with open(GROUP_DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


def get_known_qr_files(db):
    return {g["qr_file"] for g in db["groups"]}


import ctypes
import win32gui, win32con


def bring_wechat_front():
    hwnd = win32gui.FindWindow('WeChatMainWndForPC', None)
    if hwnd:
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
        except Exception:
            ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)
            win32gui.SetForegroundWindow(hwnd)
            ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)
        time.sleep(0.5)


def get_session_set(wx):
    """获取当前微信会话列表（滚动到顶部获取最新的会话）"""
    try:
        bring_wechat_front()
        time.sleep(0.3)
        # 点击会话列表区域
        wx.SessionBox.Click()
        time.sleep(0.3)
        # 滚到最顶部，确保新群可见
        pyautogui.press('home')
        time.sleep(0.5)
        sessions = wx.GetSessionList()
        return set(sessions) if sessions else set()
    except Exception:
        return set()


def scan_all_folders():
    """扫描最近日期文件夹的二维码图片信息"""
    all_items = []
    if not os.path.isdir(QR_CODE_ROOT):
        return all_items

    date_dirs = sorted(
        [d for d in os.listdir(QR_CODE_ROOT)
         if os.path.isdir(os.path.join(QR_CODE_ROOT, d))],
        reverse=True,
    )

    # 只扫描最近的日期文件夹
    if not date_dirs:
        return all_items

    latest_date_dir = date_dirs[0]
    folder = os.path.join(QR_CODE_ROOT, latest_date_dir)
    files = sorted(os.listdir(folder))
    for filename in files:
        ext = os.path.splitext(filename)[1].lower()
        if ext not in SUPPORTED_IMAGE_EXTS:
            continue
        filepath = os.path.join(folder, filename)
        group_name, author = _parse_filename(filename)
        # 用 日期/文件名 作为唯一标识
        qr_key = f"{latest_date_dir}/{filename}"
        all_items.append({
            "file": qr_key,
            "path": filepath,
            "group_name": group_name,
            "author": author,
            "date_dir": latest_date_dir,
        })

    return all_items


def detect_joined(wx, batch, db, known_files, account_name, before_sessions):
    """对比前后会话列表，检测新进的群并记录"""
    try:
        wx = WeChat()
    except Exception:
        pass

    after_sessions = get_session_set(wx)
    new_groups = after_sessions - before_sessions

    success = 0
    if new_groups:
        print(f"\n  检测到 {len(new_groups)} 个新群:")
        for new_name in new_groups:
            # 尝试匹配到哪张二维码
            matched = None
            for r in batch:
                gname = r.get("group_name") or ""
                if gname and (gname in new_name or new_name in gname):
                    matched = r
                    break

            tomorrow = datetime.now() + timedelta(days=1)
            next_send = tomorrow.replace(
                hour=random.randint(9, 20),
                minute=random.randint(0, 59),
                second=0, microsecond=0,
            )
            db["groups"].append({
                "qr_file": matched["file"] if matched else "unknown",
                "group_name": new_name,
                "wechat_name": new_name,
                "account": account_name,
                "joined_at": datetime.now().isoformat(timespec="seconds"),
                "last_sent": None,
                "next_send": next_send.isoformat(timespec="seconds"),
                "send_count": 0, "status": "active",
            })
            if matched:
                known_files.add(matched["file"])
            success += 1
            print(f"  + {new_name} — 已进群! 首发: {next_send.strftime('%m-%d %H:%M')}")
    else:
        print("\n  未检测到新群")

    # 把本批未匹配的也标记为已处理
    for r in batch:
        if r["file"] not in known_files:
            db["groups"].append({
                "qr_file": r["file"],
                "group_name": r.get("group_name") or r["file"],
                "wechat_name": None,
                "account": account_name,
                "joined_at": datetime.now().isoformat(timespec="seconds"),
                "last_sent": None, "next_send": None,
                "send_count": 0, "status": "skipped",
            })
            known_files.add(r["file"])

    save_group_db(db)
    return success, after_sessions


def main():
    pyautogui.FAILSAFE = False

    print("=" * 50)
    print("  半自动扫码进群（批量模式）")
    print(f"  每 {BATCH_SIZE} 张一批，扫完按回车继续")
    print("=" * 50)

    # 连接微信
    print("\n连接微信...")
    wx = WeChat()
    account_name = wx.nickname
    print(f"已连接: {account_name}")

    # 加载数据库
    db = load_group_db()
    known_files = get_known_qr_files(db)

    # 扫描所有文件夹
    print("\n扫描所有二维码文件夹...")
    all_items = scan_all_folders()
    pending = [r for r in all_items if r["file"] not in known_files]
    # 从指定位置开始
    if START_FROM > 1:
        pending = pending[START_FROM - 1:]
        print(f"从第 {START_FROM} 条开始")
    print(f"总计: {len(all_items)} 张, 待处理: {len(pending)} 张\n")

    if not pending:
        print("没有新的二维码需要处理。")
        return

    total_success = 0
    total_sent = 0
    batch_num = 0

    # 获取初始会话列表快照
    before_sessions = get_session_set(wx)

    # 按批次处理
    for start in range(0, len(pending), BATCH_SIZE):
        batch = pending[start:start + BATCH_SIZE]
        batch_num += 1
        end = start + len(batch)

        print(f"\n{'=' * 50}")
        print(f"  第 {batch_num} 批 ({start+1}-{end}/{len(pending)})")
        print(f"{'=' * 50}")

        # 发送这一批二维码到文件传输助手
        sent_batch = []
        for i, r in enumerate(batch, 1):
            gname = r.get("group_name") or r["file"]
            print(f"  [{start+i}/{len(pending)}] 发送: {gname}")
            try:
                wx.SendFiles(r["path"], "文件传输助手")
                sent_batch.append(r)
                total_sent += 1
                time.sleep(1.5)
            except Exception as e:
                print(f"    发送失败: {e}")
                try:
                    wx = WeChat()
                except Exception:
                    pass

        print(f"\n  本批已发 {len(sent_batch)} 张到文件传输助手")
        print("  -" * 25)
        print("  请在手机微信【文件传输助手】中逐张长按识别进群")
        print("  扫完后按回车继续 | 输入 q 退出")
        print("  -" * 25)

        user_input = input("\n>>> ").strip().lower()
        if user_input == "q":
            print("\n用户退出，保存进度...")
            for r in sent_batch:
                if r["file"] not in known_files:
                    db["groups"].append({
                        "qr_file": r["file"],
                        "group_name": r.get("group_name") or r["file"],
                        "wechat_name": None,
                        "account": account_name,
                        "joined_at": datetime.now().isoformat(timespec="seconds"),
                        "last_sent": None, "next_send": None,
                        "send_count": 0, "status": "skipped",
                    })
                    known_files.add(r["file"])
            save_group_db(db)
            break

        # 检测本批进群情况
        print("\n检测进群情况...")
        batch_success, before_sessions = detect_joined(
            wx, sent_batch, db, known_files, account_name, before_sessions
        )
        total_success += batch_success
        print(f"\n  本批结果: 进群 {batch_success}/{len(sent_batch)}")

    print(f"\n{'=' * 50}")
    print(f"全部完成! 总进群={total_success}, 总发送={total_sent}")
    active = [g for g in db["groups"] if g.get("status") == "active"]
    print(f"活跃群总数: {len(active)}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()

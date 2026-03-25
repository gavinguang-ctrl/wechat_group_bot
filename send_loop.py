"""定时轮换发消息 - 读取 group_db.json，对到期的群发送 AI 改写消息"""

import sys
import os
import json
import time
import random
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from message_gen import generate_message, load_template
from wxauto import WeChat
from config import (
    GROUP_DB_FILE, SEND_DELAY_MIN, SEND_DELAY_MAX,
    SEND_INTERVAL_MIN_DAYS, SEND_INTERVAL_MAX_DAYS,
    WORK_HOUR_START, WORK_HOUR_END,
)


def load_group_db():
    if os.path.isfile(GROUP_DB_FILE):
        with open(GROUP_DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"groups": []}


def save_group_db(db):
    with open(GROUP_DB_FILE, "w", encoding="utf-8") as f:
        json.dump(db, f, ensure_ascii=False, indent=2)


def get_due_groups(db):
    """筛选出到了发送时间的活跃群"""
    now = datetime.now()
    due = []
    for g in db["groups"]:
        if g.get("status") != "active":
            continue
        if not g.get("wechat_name"):
            continue
        next_send = g.get("next_send")
        if not next_send:
            continue
        if datetime.fromisoformat(next_send) <= now:
            due.append(g)
    # 按 next_send 排序，最早的先发
    due.sort(key=lambda g: g["next_send"])
    return due


def main():
    now = datetime.now()

    # 检查工作时间
    if not (WORK_HOUR_START <= now.hour < WORK_HOUR_END):
        print(f"当前 {now.strftime('%H:%M')} 不在工作时间 ({WORK_HOUR_START}:00-{WORK_HOUR_END}:00)，退出。")
        return

    print("=" * 50)
    print("  定时轮换发消息")
    print(f"  {now.strftime('%Y-%m-%d %H:%M')}")
    print("=" * 50)

    # 加载数据库
    db = load_group_db()
    due = get_due_groups(db)

    if not due:
        # 找下一个最近的发送时间
        active = [g for g in db["groups"] if g.get("status") == "active" and g.get("next_send")]
        if active:
            next_time = min(g["next_send"] for g in active)
            print(f"\n当前没有需要发送的群。下次最早: {next_time}")
        else:
            print("\n没有活跃的群。请先运行 scan_join.py 进群。")
        return

    print(f"\n待发送: {len(due)} 个群\n")

    # 连接微信
    print("连接微信...")
    wx = WeChat()
    print(f"已连接: {wx.nickname}\n")

    # 加载模板
    template = load_template()

    sent = 0
    failed = 0

    for i, g in enumerate(due, 1):
        gname = g["group_name"]
        wname = g["wechat_name"]
        print(f"--- [{i}/{len(due)}] {gname} (微信名: {wname}) ---")

        # AI 改写
        print("  AI 改写消息...")
        try:
            msg = generate_message(template=template, group_name=gname)
        except Exception as e:
            print(f"  AI 改写失败: {e}，跳过")
            failed += 1
            continue
        print(f"  消息: {msg[:80]}...")

        # 发送
        print(f"  发送到 [{wname}]...")
        try:
            wx.SendMsg(msg, wname)
            print("  发送成功!")
            sent += 1

            # 更新数据库
            g["last_sent"] = datetime.now().isoformat(timespec="seconds")
            g["send_count"] = g.get("send_count", 0) + 1

            # 随机 1-3 天后再发，时间也随机
            days = random.uniform(SEND_INTERVAL_MIN_DAYS, SEND_INTERVAL_MAX_DAYS)
            next_dt = datetime.now() + timedelta(days=days)
            next_dt = next_dt.replace(
                hour=random.randint(max(WORK_HOUR_START, 9), min(WORK_HOUR_END - 1, 20)),
                minute=random.randint(0, 59),
                second=0, microsecond=0,
            )
            g["next_send"] = next_dt.isoformat(timespec="seconds")
            print(f"  下次发送: {next_dt.strftime('%m-%d %H:%M')}")

            # 保存（每条发完就保存，防中断丢失）
            save_group_db(db)

        except Exception as e:
            print(f"  发送失败: {e}")
            failed += 1

        # 风控间隔
        if i < len(due):
            delay = random.uniform(SEND_DELAY_MIN, SEND_DELAY_MAX)
            print(f"  等待 {delay:.0f}s...\n")
            time.sleep(delay)

    print(f"\n{'=' * 50}")
    print(f"完成! 发送={sent}, 失败={failed}")

    # 显示下次发送时间
    active = [g for g in db["groups"] if g.get("status") == "active" and g.get("next_send")]
    if active:
        next_time = min(g["next_send"] for g in active)
        print(f"下次最早发送: {next_time}")
    print(f"{'=' * 50}")


if __name__ == "__main__":
    main()

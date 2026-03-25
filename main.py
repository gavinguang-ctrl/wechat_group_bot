"""微信扫码进群 + 群聊自动发消息工具

使用方法：
1. 将群二维码图片放入 qrcodes/ 文件夹
2. 编辑 templates/default.txt 设置消息模板
3. 确保微信 PC 版已登录并保持前台
4. 运行: python main.py
"""

import sys
import os
import time
from datetime import datetime

# 修复 Windows 终端中文/特殊字符输出
os.environ.setdefault("PYTHONIOENCODING", "utf-8")

from config import QR_CODE_DIR, TEMPLATE_DIR, DEFAULT_TEMPLATE, ACCOUNTS
from qr_scanner import scan_qr_folder
from message_gen import generate_message, load_template
from account_manager import AccountManager
from wechat_ops import WeChatOps


def print_banner():
    print("=" * 55)
    print("  微信扫码进群 + 群聊自动发消息工具")
    print("  技术路线: wxauto (UI自动化, 零封号风险)")
    print("=" * 55)
    print()


def check_prerequisites():
    """检查运行前提条件。"""
    errors = []

    if not os.path.isdir(QR_CODE_DIR):
        os.makedirs(QR_CODE_DIR, exist_ok=True)
        print(f"[提示] 已创建二维码文件夹: {QR_CODE_DIR}")

    if not os.path.isdir(TEMPLATE_DIR):
        os.makedirs(TEMPLATE_DIR, exist_ok=True)

    if not os.path.isfile(DEFAULT_TEMPLATE):
        errors.append(f"消息模板不存在: {DEFAULT_TEMPLATE}")
        errors.append("请创建模板文件，写入要发送的文字内容。")

    qr_files = [f for f in os.listdir(QR_CODE_DIR)
                if os.path.splitext(f)[1].lower() in {".png", ".jpg", ".jpeg", ".bmp", ".webp"}]
    if not qr_files:
        errors.append(f"二维码文件夹为空: {QR_CODE_DIR}")
        errors.append("请将群二维码图片放入该文件夹。")

    if errors:
        print("[错误] 运行前检查未通过:")
        for e in errors:
            print(f"  - {e}")
        return False

    print(f"[ok] 二维码文件夹: {QR_CODE_DIR} ({len(qr_files)} 张图片)")
    print(f"[ok] 消息模板: {DEFAULT_TEMPLATE}")
    print(f"[ok] 账号数量: {len(ACCOUNTS)} 个")
    return True


def run_main_flow():
    """主执行流程。"""
    # Step 1: 扫描二维码
    print("\n--- 第一步: 扫描二维码 ---")
    qr_results = scan_qr_folder()

    if not qr_results:
        print("[结束] 没有找到任何图片文件。")
        return

    # 分离成功和失败的
    valid_qrs = [r for r in qr_results if r["data"]]
    failed_qrs = [r for r in qr_results if not r["data"]]

    print(f"\n扫描结果: {len(valid_qrs)} 个成功, {len(failed_qrs)} 个识别失败")

    if failed_qrs:
        print("识别失败的图片将通过直接发图方式处理（发送到文件传输助手识别）。")

    # 合并待处理列表：成功识别的用URL方式，失败的用图片方式
    tasks = []
    for r in valid_qrs:
        tasks.append({
            "file": r["file"], "path": r["path"],
            "method": "url", "data": r["data"],
            "group_name": r.get("group_name"), "author": r.get("author"),
        })
    for r in failed_qrs:
        tasks.append({
            "file": r["file"], "path": r["path"],
            "method": "image", "data": None,
            "group_name": r.get("group_name"), "author": r.get("author"),
        })

    if not tasks:
        print("[结束] 没有待处理的二维码。")
        return

    # Step 2: 加载消息模板
    print("\n--- 第二步: 加载消息模板 ---")
    try:
        template = load_template()
        print(f"模板内容预览: {template[:80]}...")
    except FileNotFoundError as e:
        print(f"[错误] {e}")
        return

    # Step 3: 初始化
    print("\n--- 第三步: 连接微信 ---")
    try:
        wx_ops = WeChatOps()
    except Exception:
        print("[终止] 无法连接微信，请确保微信 PC 版已登录。")
        return

    acct_mgr = AccountManager()
    print(f"当前账号: 【{acct_mgr.current_name}】")

    # Step 4: 执行进群 + 发消息
    print(f"\n--- 第四步: 开始进群并发消息 (共 {len(tasks)} 个) ---\n")

    success_count = 0
    fail_count = 0

    for i, task in enumerate(tasks, 1):
        # 检查工作时间
        wx_ops.wait_for_work_hours()

        # 检查是否需要切换账号
        if acct_mgr.need_switch():
            if not acct_mgr.prompt_switch():
                print("[结束] 所有账号已用完。")
                break
            # 重新连接微信（用户已切换账号）
            try:
                wx_ops = WeChatOps()
            except Exception:
                print("[终止] 切换账号后无法连接微信。")
                break

        # 检查是否已处理过
        identifier = task["data"] or task["file"]
        if acct_mgr.is_already_joined(identifier):
            print(f"[{i}/{len(tasks)}] 跳过（已处理）: {task['file']}")
            continue

        print(f"[{i}/{len(tasks)}] 处理: {task['file']}  (账号: {acct_mgr.current_name})")

        # 进群
        joined = False
        if task["method"] == "url":
            joined = wx_ops.join_group_by_url(task["data"])
        else:
            joined = wx_ops.join_group_by_image(task["path"])

        if joined:
            acct_mgr.record_join(identifier)
            success_count += 1

            # 进群后等待
            wx_ops.random_join_delay()

            # 用文件名中解析出的群名做 AI 个性化改写
            group_name = task.get("group_name")
            print(f"  [群名] {group_name or '未知'}")

            # 获取最新加入的群（用于发送消息）
            sessions = wx_ops.get_group_list()
            if sessions:
                newest_session = sessions[0]

                # 尝试获取群公告作为额外上下文
                group_notice = None
                try:
                    group_info = wx_ops.get_group_info(newest_session)
                    group_notice = group_info.get("notice")
                except Exception:
                    pass

                # 生成个性化消息（AI 根据群名 + 群公告改写）
                message = generate_message(
                    template=template,
                    group_name=group_name or newest_session,
                    group_notice=group_notice,
                )

                sent = wx_ops.send_message_to_group(newest_session, message)
                if sent:
                    acct_mgr.record_send()
                wx_ops.random_send_delay()
        else:
            fail_count += 1

        print()

    # Step 5: 汇总
    print("\n--- 执行完毕 ---")
    print(f"成功进群: {success_count}, 失败: {fail_count}, 跳过: {len(tasks) - success_count - fail_count}")
    print(acct_mgr.get_summary())


def main():
    print_banner()

    if not check_prerequisites():
        print("\n请按照上述提示准备好文件后重新运行。")
        sys.exit(1)

    print()
    # 支持 --auto 参数跳过确认（用于非交互终端）
    if "--auto" not in sys.argv:
        input("一切就绪，按回车键开始运行...")
    print()

    try:
        run_main_flow()
    except KeyboardInterrupt:
        print("\n\n[中断] 用户手动停止。")
    except Exception as e:
        print(f"\n[异常] 程序出错: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

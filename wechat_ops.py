"""微信操作模块 - 扫码进群、发送消息的核心逻辑"""

import os
import time
import random
import pyautogui
import pyperclip
from datetime import datetime
from wxauto import WeChat
from config import (
    JOIN_DELAY_MIN, JOIN_DELAY_MAX,
    SEND_DELAY_MIN, SEND_DELAY_MAX,
    UI_STEP_DELAY,
    WORK_HOUR_START, WORK_HOUR_END,
)


class WeChatOps:
    """封装微信 PC 端的自动化操作。"""

    def __init__(self):
        self.wx = None
        self._connect()

    def _connect(self):
        """连接微信 PC 客户端。"""
        try:
            self.wx = WeChat()
            print(f"[成功] 已连接微信客户端")
        except Exception as e:
            print(f"[错误] 无法连接微信客户端: {e}")
            print("请确保微信 PC 版已登录并保持在前台。")
            raise

    def is_work_hours(self) -> bool:
        """检查当前是否在允许的工作时间段内。"""
        hour = datetime.now().hour
        return WORK_HOUR_START <= hour < WORK_HOUR_END

    def wait_for_work_hours(self):
        """如果不在工作时间，等待到工作时间开始。"""
        if self.is_work_hours():
            return
        print(f"[等待] 当前不在工作时间({WORK_HOUR_START}:00-{WORK_HOUR_END}:00)，暂停中...")
        while not self.is_work_hours():
            time.sleep(60)
        print("[继续] 已进入工作时间，继续运行。")

    def join_group_by_image(self, qr_image_path: str) -> bool:
        """通过发送二维码图片到文件传输助手，然后识别进群。

        流程：
        1. 将二维码图片发送到「文件传输助手」
        2. 在聊天中点击图片放大
        3. 右键识别二维码
        4. 点击加入群聊

        Args:
            qr_image_path: 二维码图片的完整路径

        Returns:
            True 如果操作成功执行，False 如果出错
        """
        if not os.path.isfile(qr_image_path):
            print(f"  [跳过] 图片不存在: {qr_image_path}")
            return False

        try:
            # Step 1: 发送图片到文件传输助手
            print(f"  [操作] 发送二维码图片到文件传输助手...")
            self.wx.SendFiles(qr_image_path, "文件传输助手")
            time.sleep(UI_STEP_DELAY * 2)

            # Step 2: 切换到文件传输助手聊天窗口
            self.wx.ChatWith("文件传输助手")
            time.sleep(UI_STEP_DELAY)

            # Step 3: 获取最后一条消息（应该是刚发的图片），点击它
            # 使用 pyautogui 在聊天区域找到并点击图片
            # 先获取微信窗口位置
            time.sleep(UI_STEP_DELAY)

            # 点击聊天区域最后的图片（通常在窗口中下部偏右）
            # 获取微信窗口，双击最后的图片以放大查看
            self._click_last_image()
            time.sleep(UI_STEP_DELAY * 2)

            # Step 4: 图片放大后，右键点击识别二维码
            # 在图片查看器中右键
            pyautogui.rightClick()
            time.sleep(UI_STEP_DELAY)

            # Step 5: 点击「识别图中二维码」菜单项
            self._click_menu_item("识别图中二维码")
            time.sleep(UI_STEP_DELAY * 2)

            # Step 6: 在弹出的页面中点击「加入群聊」或「进入群聊」
            time.sleep(2)  # 等待页面加载
            self._click_join_button()
            time.sleep(UI_STEP_DELAY * 2)

            print(f"  [成功] 扫码进群操作已执行")
            return True

        except Exception as e:
            print(f"  [错误] 扫码进群失败: {e}")
            return False

    def join_group_by_url(self, qr_url: str) -> bool:
        """通过二维码解析出的 URL 进群（备选方案）。

        将 URL 发送到文件传输助手，点击链接触发微信内置浏览器打开。

        Args:
            qr_url: 二维码解码后的 URL

        Returns:
            True 如果操作成功
        """
        try:
            print(f"  [操作] 通过链接进群...")

            # 发送链接到文件传输助手
            self.wx.SendMsg(qr_url, "文件传输助手")
            time.sleep(UI_STEP_DELAY * 2)

            # 切换到文件传输助手
            self.wx.ChatWith("文件传输助手")
            time.sleep(UI_STEP_DELAY)

            # 点击链接（最后一条消息）
            self._click_last_link()
            time.sleep(3)  # 等待内置浏览器加载

            # 点击「加入群聊」
            self._click_join_button()
            time.sleep(UI_STEP_DELAY * 2)

            print(f"  [成功] 链接进群操作已执行")
            return True

        except Exception as e:
            print(f"  [错误] 链接进群失败: {e}")
            return False

    def send_message_to_group(self, group_name: str, message: str) -> bool:
        """向指定群聊发送消息。

        Args:
            group_name: 群聊名称
            message: 要发送的消息内容

        Returns:
            True 如果发送成功
        """
        try:
            self.wx.SendMsg(message, group_name)
            print(f"  [已发送] -> {group_name}")
            return True
        except Exception as e:
            print(f"  [失败] 发送到 {group_name} 失败: {e}")
            return False

    def get_group_list(self) -> list[str]:
        """获取当前微信的群聊列表。"""
        try:
            sessions = self.wx.GetSessionList()
            return [s for s in sessions if s]
        except Exception as e:
            print(f"[错误] 获取会话列表失败: {e}")
            return []

    def get_group_info(self, group_name: str) -> dict:
        """获取群聊的名称和公告/简介信息。

        通过 wxauto 切换到群聊窗口，尝试读取群公告。

        Returns:
            {"name": 群名, "notice": 群公告或None}
        """
        info = {"name": group_name, "notice": None}
        try:
            self.wx.ChatWith(group_name)
            time.sleep(UI_STEP_DELAY)
            # wxauto 部分版本支持获取群公告，尝试调用
            try:
                msgs = self.wx.GetAllMessage()
                # 从最近消息中提取群公告（群公告通常以系统消息形式出现）
                for msg in reversed(msgs):
                    content = str(msg) if not isinstance(msg, str) else msg
                    if "群公告" in content or "群简介" in content:
                        info["notice"] = content
                        break
            except Exception:
                pass
        except Exception as e:
            print(f"  [警告] 获取群信息失败: {e}")
        return info

    def random_join_delay(self):
        """进群后的随机等待。"""
        delay = random.uniform(JOIN_DELAY_MIN, JOIN_DELAY_MAX)
        print(f"  [等待] 风控间隔 {delay:.1f} 秒...")
        time.sleep(delay)

    def random_send_delay(self):
        """发消息后的随机等待。"""
        delay = random.uniform(SEND_DELAY_MIN, SEND_DELAY_MAX)
        print(f"  [等待] 发送间隔 {delay:.1f} 秒...")
        time.sleep(delay)

    # ==================== 内部 UI 操作辅助方法 ====================

    def _click_last_image(self):
        """点击聊天窗口中最后一张图片。

        通过 pyautogui 在微信聊天区域定位并双击最后的图片消息。
        """
        # 获取当前鼠标位置作为参考，或使用屏幕中心偏右下方
        screen_w, screen_h = pyautogui.size()
        # 微信聊天窗口中，最后一条消息通常在窗口中下部
        # 这里使用相对位置，实际使用时可能需要根据分辨率调整
        click_x = screen_w * 0.55
        click_y = screen_h * 0.65
        pyautogui.doubleClick(int(click_x), int(click_y))

    def _click_menu_item(self, item_text: str):
        """在右键菜单中查找并点击指定项。

        使用 pyautogui 截图匹配或坐标偏移点击菜单项。
        """
        # 右键菜单出现后，「识别图中二维码」通常在菜单中部
        # 从当前鼠标位置向下偏移查找
        current_x, current_y = pyautogui.position()
        # 菜单项通常每项高度约30px，「识别图中二维码」一般在第3-5项
        for offset_y in range(30, 180, 30):
            target_y = current_y + offset_y
            # 尝试使用 pyautogui 的 locateOnScreen（如果有截图资源）
            # 降级方案：直接点击偏移位置
            pyautogui.click(current_x + 10, target_y)
            time.sleep(0.3)
            # 简单判断菜单是否消失（说明点击成功）
            break  # 实际使用中可能需要更精确的定位

    def _click_last_link(self):
        """点击聊天中最后一条链接消息。"""
        screen_w, screen_h = pyautogui.size()
        click_x = screen_w * 0.55
        click_y = screen_h * 0.65
        pyautogui.click(int(click_x), int(click_y))

    def _click_join_button(self):
        """点击「加入群聊」或「进入群聊」按钮。

        微信内置浏览器或小窗口中的加群确认按钮。
        """
        screen_w, screen_h = pyautogui.size()
        # 「加入群聊」按钮通常在弹出页面的中下部
        click_x = screen_w * 0.5
        click_y = screen_h * 0.7
        pyautogui.click(int(click_x), int(click_y))
        time.sleep(1)
        # 二次点击确认（有时需要确认弹窗）
        pyautogui.click(int(click_x), int(click_y))

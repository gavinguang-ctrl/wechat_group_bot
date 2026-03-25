"""多账号管理模块 - 跟踪账号状态、控制切换流程"""

import json
import os
from config import ACCOUNTS, PROCESSED_FILE


class AccountManager:
    """管理多个微信账号的操作状态和切换逻辑。"""

    def __init__(self, accounts: list[dict] = None):
        self.accounts = accounts or ACCOUNTS
        self.current_index = 0
        # 每个账号的状态：{name, groups_joined: int, groups_sent: int, joined_groups: set}
        self.states = []
        for acc in self.accounts:
            self.states.append({
                "name": acc["name"],
                "groups_limit": acc["groups_limit"],
                "groups_joined": 0,
                "groups_sent": 0,
                "joined_groups": set(),
            })
        # 加载已处理记录
        self._load_processed()

    @property
    def current(self) -> dict:
        """当前账号状态。"""
        return self.states[self.current_index]

    @property
    def current_name(self) -> str:
        return self.current["name"]

    def can_join_more(self) -> bool:
        """当前账号是否还能继续进群。"""
        return self.current["groups_joined"] < self.current["groups_limit"]

    def record_join(self, group_identifier: str):
        """记录当前账号成功进入一个群。"""
        self.current["groups_joined"] += 1
        self.current["joined_groups"].add(group_identifier)
        self._save_processed()

    def record_send(self):
        """记录当前账号成功发送一条消息。"""
        self.current["groups_sent"] += 1

    def is_already_joined(self, group_identifier: str) -> bool:
        """检查某个群是否已经被任何账号加入过。"""
        for state in self.states:
            if group_identifier in state["joined_groups"]:
                return True
        return False

    def need_switch(self) -> bool:
        """是否需要切换到下一个账号。"""
        return not self.can_join_more()

    def switch_to_next(self) -> bool:
        """切换到下一个账号。

        Returns:
            True 如果成功切换，False 如果没有更多可用账号。
        """
        next_index = self.current_index + 1
        if next_index >= len(self.states):
            return False
        self.current_index = next_index
        return True

    def prompt_switch(self) -> bool:
        """提示用户切换微信号，等待确认。

        Returns:
            True 如果用户确认切换完成，False 如果没有更多账号。
        """
        if not self.switch_to_next():
            print("\n" + "=" * 50)
            print("所有账号已用完，无法继续。")
            print("=" * 50)
            return False

        next_name = self.current_name
        print("\n" + "=" * 50)
        print(f"当前账号已达到进群上限！")
        print(f"请切换到微信号: 【{next_name}】")
        print(f"操作步骤:")
        print(f"  1. 退出当前微信账号")
        print(f"  2. 登录 【{next_name}】")
        print(f"  3. 确保微信主窗口已打开")
        print("=" * 50)
        input("切换完成后，按回车键继续...")
        print(f"已切换到 【{next_name}】，继续运行。\n")
        return True

    def get_summary(self) -> str:
        """返回所有账号的操作统计摘要。"""
        lines = ["\n===== 账号操作统计 ====="]
        for state in self.states:
            lines.append(
                f"  {state['name']}: "
                f"进群 {state['groups_joined']}/{state['groups_limit']}, "
                f"发消息 {state['groups_sent']} 条"
            )
        lines.append("========================")
        return "\n".join(lines)

    def _load_processed(self):
        """从文件加载已处理记录。"""
        if not os.path.isfile(PROCESSED_FILE):
            return
        try:
            with open(PROCESSED_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            for state in self.states:
                name = state["name"]
                if name in data:
                    state["joined_groups"] = set(data[name].get("joined_groups", []))
                    state["groups_joined"] = len(state["joined_groups"])
        except (json.JSONDecodeError, KeyError):
            pass

    def _save_processed(self):
        """保存已处理记录到文件。"""
        data = {}
        for state in self.states:
            data[state["name"]] = {
                "joined_groups": list(state["joined_groups"]),
            }
        with open(PROCESSED_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

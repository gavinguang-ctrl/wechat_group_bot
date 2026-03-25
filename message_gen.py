"""消息生成模块 - 基于模板微调消息内容，支持 AI 个性化改写"""

import io
import os
import sys
import random
from datetime import datetime
from openai import OpenAI
from config import (
    DEFAULT_TEMPLATE,
    AI_BASE_URL, AI_API_KEY, AI_MODEL, AI_REWRITE_PROMPT,
)

# 修复 Windows 终端中文/特殊字符输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

# 零宽字符集（不可见，但让每条消息哈希不同）
ZERO_WIDTH_CHARS = [
    "\u200b",  # 零宽空格
    "\u200c",  # 零宽非连接符
    "\u200d",  # 零宽连接符
    "\ufeff",  # 零宽不换行空格
]


def load_template(template_path: str = None) -> str:
    """加载消息模板文件内容。"""
    path = template_path or DEFAULT_TEMPLATE
    if not os.path.isfile(path):
        raise FileNotFoundError(f"模板文件不存在: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def generate_message(
    template: str = None,
    template_path: str = None,
    group_name: str = None,
    group_notice: str = None,
) -> str:
    """基于模板生成一条个性化消息。

    如果提供了群名/群简介且 AI API 已配置，则使用 AI 做个性化改写。
    否则回退到本地微调（同义词替换 + 零宽字符）。

    Args:
        template: 直接传入模板文本
        template_path: 或从文件加载模板
        group_name: 群聊名称
        group_notice: 群公告/简介
    """
    if template is None:
        template = load_template(template_path)

    # 替换动态占位符
    msg = _replace_placeholders(template)

    # 尝试 AI 个性化改写
    if group_name and AI_API_KEY:
        ai_result = _ai_rewrite(msg, group_name, group_notice)
        if ai_result:
            msg = ai_result

    # 插入零宽字符（无论是否 AI 改写，都加上，确保每条消息哈希不同）
    msg = _insert_zero_width(msg)

    return msg


def _ai_rewrite(template: str, group_name: str, group_notice: str = None) -> str | None:
    """调用 AI 接口，根据群信息个性化改写消息。

    Returns:
        改写后的消息文本，失败时返回 None（回退到本地微调）
    """
    group_info = f"群名: {group_name}"
    if group_notice:
        group_info += f"\n群公告/简介: {group_notice}"

    user_prompt = f"""以下是群的信息：
{group_info}

以下是需要改写的原始文案：
---
{template}
---

请根据这个群的信息，对文案进行个性化改写。"""

    try:
        client = OpenAI(base_url=AI_BASE_URL, api_key=AI_API_KEY, timeout=60)
        response = client.chat.completions.create(
            model=AI_MODEL,
            messages=[
                {"role": "system", "content": AI_REWRITE_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.8,
            max_tokens=1000,
        )
        result = response.choices[0].message.content.strip()
        print(f"  [AI改写] 已生成个性化消息 (长度: {len(result)})")
        return result
    except Exception as e:
        print(f"  [AI改写失败] {e}，回退到本地微调")
        return None


def _replace_placeholders(text: str) -> str:
    """替换模板中的动态占位符。"""
    now = datetime.now()
    replacements = {
        "{date}": now.strftime("%Y年%m月%d日"),
        "{time}": now.strftime("%H:%M"),
        "{weekday}": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"][now.weekday()],
        "{month}": str(now.month),
        "{day}": str(now.day),
    }
    for placeholder, value in replacements.items():
        text = text.replace(placeholder, value)
    return text


def _insert_zero_width(text: str, count: int = 3) -> str:
    """在随机位置插入零宽字符（不影响显示，但改变文本哈希值）。"""
    if len(text) < 5:
        return text
    text_list = list(text)
    for _ in range(count):
        pos = random.randint(1, len(text_list) - 1)
        char = random.choice(ZERO_WIDTH_CHARS)
        text_list.insert(pos, char)
    return "".join(text_list)


if __name__ == "__main__":
    test_template = load_template()
    print("=== AI 个性化改写测试 ===\n")
    print(f"原始模板:\n{test_template}\n")
    print("-" * 40)

    test_groups = [
        {"name": "TK跨境电商交流群", "notice": "本群用于TikTok跨境电商经验分享"},
        {"name": "东南亚直播带货联盟", "notice": "聚焦东南亚市场直播电商"},
        {"name": "独立站卖家资源群", "notice": None},
    ]
    for g in test_groups:
        print(f"\n群名: {g['name']}")
        msg = generate_message(template=test_template, group_name=g["name"], group_notice=g.get("notice"))
        print(f"改写结果:\n{msg}\n")
        print("-" * 40)

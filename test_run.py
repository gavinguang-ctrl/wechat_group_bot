"""完整进群+发消息脚本 - 大图右键识别二维码进群"""
import sys, os, time, random, ctypes
import pyautogui
import win32gui, win32con

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from qr_scanner import scan_qr_folder
from message_gen import generate_message, load_template
from wxauto import WeChat
from wxauto import uiautomation as uia

pyautogui.FAILSAFE = False
LIMIT = 52  # 处理所有群，过期的自动跳过


def connect_wx():
    return WeChat()


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


def bring_imagepreview_front():
    """置顶大图查看器窗口，返回窗口中心坐标"""
    hwnd = win32gui.FindWindow('ImagePreviewWnd', None)
    if not hwnd:
        return None, None
    try:
        win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(hwnd)
    except Exception:
        ctypes.windll.user32.keybd_event(0x12, 0, 0, 0)
        win32gui.SetForegroundWindow(hwnd)
        ctypes.windll.user32.keybd_event(0x12, 0, 2, 0)
    time.sleep(0.5)
    r = win32gui.GetWindowRect(hwnd)
    return (r[0] + r[2]) // 2, (r[1] + r[3]) // 2


def find_image_center(wx):
    """找聊天列表中最后一条图片消息的图片区域中心"""
    msg_list = wx.C_MsgList
    children = msg_list.GetChildren()
    for msg in reversed(children):
        if msg.Name and '[图片]' in msg.Name:
            pane = msg.GetChildren()[0]
            img = pane.GetChildren()[0]
            r = img.BoundingRectangle
            if r.width() > 50 and r.height() > 50:
                return (r.left + r.right) // 2, (r.top + r.bottom) // 2
    return None, None


def join_group(wx, qr_image_path):
    """发送二维码图片 → 打开大图 → 置顶大图 → 右键识别二维码 → 加入群聊

    如果二维码已过期（右键没有「识别图中二维码」选项），自动跳过。
    """

    # 1. 发送图片到文件传输助手
    print('    [1] 发送图片...')
    wx.SendFiles(qr_image_path, '文件传输助手')
    time.sleep(3)
    wx.ChatWith('文件传输助手')
    time.sleep(2)

    # 2. 用键盘打开最后一张图片的大图
    print('    [2] 用Enter打开大图...')
    bring_wechat_front()
    time.sleep(0.5)
    # 先点击消息列表区域让它获得焦点
    msg_list = wx.C_MsgList
    msg_list.Click()
    time.sleep(0.5)
    # 按End跳到最后一条消息，然后按Enter打开
    pyautogui.press('end')
    time.sleep(0.5)
    pyautogui.press('enter')
    time.sleep(3)

    # 3. 置顶大图查看器窗口
    print('    [3] 置顶大图...')
    img_cx, img_cy = None, None
    for _ in range(3):
        img_cx, img_cy = bring_imagepreview_front()
        if img_cx:
            break
        time.sleep(1)
    if img_cx is None:
        print('    [跳过] 大图窗口未打开')
        return False
    time.sleep(0.5)

    # 4. 在大图上右键
    print('    [4] 右键菜单...')
    pyautogui.rightClick(img_cx, img_cy)
    time.sleep(1.5)

    # 5. 查找右键菜单中的「识别图中二维码」
    #    如果找不到说明二维码已过期，跳过
    try:
        menu_item = uia.MenuItemControl(Name='识别图中二维码', searchDepth=5, searchWaitTime=3)
        if menu_item.Exists(2):
            print('    [5] 点击识别图中二维码...')
            menu_item.Click()
            time.sleep(5)  # 等待加群页面加载

            # 6. 点击「加入群聊」按钮
            print('    [6] 点击加入群聊...')
            join_btn = uia.ButtonControl(Name='加入群聊', searchDepth=8, searchWaitTime=5)
            if join_btn.Exists(3):
                join_btn.Click()
                time.sleep(3)
                print('    进群成功!')
                # 关闭大图
                pyautogui.press('escape')
                time.sleep(1)
                return True
            else:
                print('    [跳过] 未找到加入按钮（可能已在群里或群已满）')
                pyautogui.press('escape')
                time.sleep(1)
                return False
        else:
            print('    [跳过] 无「识别图中二维码」选项（二维码已过期）')
            # 关闭右键菜单和大图
            pyautogui.press('escape')
            time.sleep(0.5)
            pyautogui.press('escape')
            time.sleep(0.5)
            return False
    except Exception as e:
        print(f'    [跳过] 菜单异常: {e}')
        pyautogui.press('escape')
        time.sleep(0.5)
        pyautogui.press('escape')
        time.sleep(0.5)
        return False


# === 主流程 ===
print('=' * 50)
print('  微信扫码进群 + AI个性化发消息')
print('  方式: 大图右键识别二维码')
print('=' * 50)

print('\n连接微信...')
wx = connect_wx()
print(f'已连接: {wx.nickname}')

print('\n扫描二维码...')
results = scan_qr_folder()
valid = [r for r in results if r['data'] and r.get('group_name')][:LIMIT]
print(f'\n处理 {len(valid)} 个群: {[r["group_name"] for r in valid]}\n')

template = load_template()
success = 0
fail = 0
skipped = 0

for i, r in enumerate(valid, 1):
    gname = r['group_name']
    print(f'--- [{i}/{LIMIT}] {gname} ---')

    # 进群
    print('  [进群]')
    wx = connect_wx()
    joined = join_group(wx, r['path'])

    if joined:
        # AI改写消息
        print('  [消息] AI改写...')
        msg = generate_message(template=template, group_name=gname)
        print(f'  [消息] {msg[:80]}...')

        # 发消息到最新会话
        print('  [发送]')
        try:
            wx2 = connect_wx()
            sessions = wx2.GetSessionList()
            if sessions:
                target = sessions[0]
                print(f'    -> {target}')
                wx2.SendMsg(msg, target)
                print('    发送成功!')
                success += 1
        except Exception as e:
            print(f'    发送失败: {e}')
            fail += 1
        # 第一个成功就停止
        print('\n  首个未过期二维码已完成全流程，停止。')
        break
    else:
        skipped += 1

    # 风控间隔
    if i < len(valid):
        delay = random.uniform(25, 40)
        print(f'\n  风控等待 {delay:.0f}s...\n')
        time.sleep(delay)

print(f'\n{"=" * 50}')
print(f'完成! 成功={success}, 跳过={skipped}, 失败={fail}')
print(f'{"=" * 50}')

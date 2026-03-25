"""二维码识别模块 - 使用 OpenCV 自带 QRCodeDetector，无需额外 DLL"""

import os
import cv2
import numpy as np
from config import QR_CODE_DIR, SUPPORTED_IMAGE_EXTS


def _imread_unicode(image_path: str) -> np.ndarray | None:
    """支持中文/emoji路径的图片读取（cv2.imread不支持非ASCII路径）。"""
    try:
        data = np.fromfile(image_path, dtype=np.uint8)
        img = cv2.imdecode(data, cv2.IMREAD_COLOR)
        return img
    except Exception:
        return None


def scan_qr_from_image(image_path: str) -> str | None:
    """从单张图片中识别二维码，返回解码后的数据（URL）。

    先尝试直接识别，失败后进行图像预处理再重试。
    """
    img = _imread_unicode(image_path)
    if img is None:
        return None

    detector = cv2.QRCodeDetector()

    # 第一次尝试：直接识别
    data, _, _ = detector.detectAndDecode(img)
    if data:
        return data

    # 第二次尝试：预处理后重试
    return _scan_with_preprocessing(img, detector)


def _scan_with_preprocessing(img: np.ndarray, detector: cv2.QRCodeDetector) -> str | None:
    """用 OpenCV 预处理图片后重新识别二维码。

    适用于截图、模糊图片等直接识别失败的场景。
    """
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    strategies = [
        # 策略1：自适应二值化
        lambda g: cv2.adaptiveThreshold(
            g, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 11, 2
        ),
        # 策略2：OTSU 二值化
        lambda g: cv2.threshold(g, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1],
        # 策略3：放大2倍 + 锐化
        lambda g: _enlarge_and_sharpen(g),
        # 策略4：放大2倍 + OTSU
        lambda g: cv2.threshold(
            cv2.resize(g, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC),
            0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU,
        )[1],
    ]

    for strategy in strategies:
        processed = strategy(gray)
        data, _, _ = detector.detectAndDecode(processed)
        if data:
            return data

    return None


def _enlarge_and_sharpen(gray: np.ndarray) -> np.ndarray:
    """放大并锐化灰度图像。"""
    enlarged = cv2.resize(gray, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    kernel = np.array([[-1, -1, -1], [-1, 9, -1], [-1, -1, -1]])
    return cv2.filter2D(enlarged, -1, kernel)


def scan_qr_folder(folder: str = None) -> list[dict]:
    """扫描文件夹中所有图片，返回识别结果列表。

    文件名格式约定：序号_用户名_群名.png
    例如：001_比比BB_一起学习交流跨境知识 纯分享.png

    返回格式：[{"file": 文件名, "path": 完整路径, "data": 二维码数据或None,
               "group_name": 从文件名提取的群名, "author": 发布者}]
    """
    folder = folder or QR_CODE_DIR
    results = []

    if not os.path.isdir(folder):
        print(f"[错误] 文件夹不存在: {folder}")
        return results

    files = sorted(os.listdir(folder))
    for filename in files:
        ext = os.path.splitext(filename)[1].lower()
        if ext not in SUPPORTED_IMAGE_EXTS:
            continue

        filepath = os.path.join(folder, filename)
        qr_data = scan_qr_from_image(filepath)

        # 从文件名提取群名：格式为 序号_用户名_群名.ext
        group_name, author = _parse_filename(filename)

        results.append({
            "file": filename,
            "path": filepath,
            "data": qr_data,
            "group_name": group_name,
            "author": author,
        })

        status = "成功" if qr_data else "识别失败"
        print(f"  [{status}] {filename}  ->  群名: {group_name or '未知'}")

    return results


def _parse_filename(filename: str) -> tuple[str | None, str | None]:
    """从文件名解析群名和作者。

    格式：序号_用户名_群名.ext
    例如：001_比比BB_一起学习交流跨境知识 纯分享.png

    Returns:
        (group_name, author)
    """
    name = os.path.splitext(filename)[0]
    parts = name.split("_", 2)
    if len(parts) >= 3:
        author = parts[1]
        group_name = parts[2] if parts[2] != "untitled" else None
        return group_name, author
    elif len(parts) == 2:
        return parts[1], None
    return None, None


if __name__ == "__main__":
    print("=== 二维码扫描测试 ===")
    items = scan_qr_folder()
    ok = sum(1 for r in items if r["data"])
    print(f"\n共扫描 {len(items)} 张图片，成功识别 {ok} 个二维码")

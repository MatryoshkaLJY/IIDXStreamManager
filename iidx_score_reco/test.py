#!/usr/bin/env python3
"""
IIDX 数字识别测试脚本
支持单图识别、批量测试、ROI测试
"""
import sys
import cv2
from pathlib import Path
from recognizer import IIDXDigitRecognizer


def test_recognizer():
    recognizer = IIDXDigitRecognizer("font")

    if len(sys.argv) < 2:
        print("用法:")
        print(f"  python {sys.argv[0]} <screenshot.png>        # 识别所有4个ROI")
        print(f"  python {sys.argv[0]} <screenshot.png> roi    # 识别所有ROI并显示调试信息")
        print(f"  python {sys.argv[0]} <screenshot.png> x1 y1 x2 y2  # 识别指定区域")
        print(f"  python {sys.argv[0]} --test-font             # 测试模板自匹配")
        return

    if sys.argv[1] == "--test-font":
        print("模板自匹配测试:")
        for i in range(10):
            template = recognizer.templates[i]
            # 添加一些噪声测试鲁棒性
            best_digit, score = recognizer._match_template(template)
            status = "✓" if best_digit == i else "✗"
            print(f"  数字 {i}: 识别为 {best_digit}, 置信度 {score:.4f} {status}")
        return

    image_path = sys.argv[1]

    # 默认的4个ROI坐标
    default_rois = [
        ((1547, 488), (1700, 517)),  # 右上1
        ((1547, 549), (1700, 581)),  # 右上2
        ((1400, 488), (1547, 517)),  # 左上1
        ((1400, 549), (1547, 581)),  # 左上2
    ]

    # 解析参数
    if len(sys.argv) == 6:
        # 自定义ROI: x1 y1 x2 y2
        x1, y1, x2, y2 = map(int, sys.argv[2:6])
        print(f"识别区域 ({x1},{y1})-({x2},{y2}):")
        result = recognizer.recognize(image_path, (x1, y1, x2, y2), debug=True)
        print(f"结果: {result}")
    elif len(sys.argv) == 3 and sys.argv[2] == "roi":
        # 识别所有ROI并显示调试信息
        print(f"识别图片: {image_path}")
        results = recognizer.recognize_all_rois(image_path, default_rois, debug=True)
        print("\n========== 最终识别结果 ==========")
        for roi_name, result in results.items():
            print(f"  {roi_name}: {result}")
    else:
        # 识别所有ROI（简洁模式）
        print(f"识别图片: {image_path}")
        results = recognizer.recognize_all_rois(image_path, default_rois)
        print("识别结果:")
        for roi_name, result in results.items():
            print(f"  {roi_name}: {result}")


if __name__ == "__main__":
    test_recognizer()

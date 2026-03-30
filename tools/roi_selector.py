#!/usr/bin/env python3
"""
交互式 ROI 选择工具
使用方法: python roi_selector.py <图片路径>

操作:
- 鼠标左键拖拽: 绘制矩形框
- 回车/空格: 确认选择并输出坐标
- c: 清空选择
- q/ESC: 退出
"""

import cv2
import sys


class ROISelector:
    def __init__(self, image_path):
        self.image = cv2.imread(image_path)
        if self.image is None:
            print(f"无法加载图片: {image_path}")
            sys.exit(1)

        self.clone = self.image.copy()
        self.drawing = False
        self.start_x, self.start_y = -1, -1
        self.end_x, self.end_y = -1, -1
        self.roi = None

    def mouse_callback(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            self.drawing = True
            self.start_x, self.start_y = x, y

        elif event == cv2.EVENT_MOUSEMOVE:
            if self.drawing:
                self.end_x, self.end_y = x, y
                # 实时显示
                img_copy = self.clone.copy()
                cv2.rectangle(img_copy, (self.start_x, self.start_y),
                             (self.end_x, self.end_y), (0, 255, 0), 2)
                # 显示坐标
                text = f"({self.start_x}, {self.start_y}) -> ({x}, {y})"
                cv2.putText(img_copy, text, (10, 30),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.imshow("ROI Selector", img_copy)

        elif event == cv2.EVENT_LBUTTONUP:
            self.drawing = False
            self.end_x, self.end_y = x, y
            # 绘制最终矩形
            cv2.rectangle(self.clone, (self.start_x, self.start_y),
                         (self.end_x, self.end_y), (0, 255, 0), 2)
            self.roi = (self.start_x, self.start_y,
                       abs(self.end_x - self.start_x),
                       abs(self.end_y - self.start_y))

    def run(self):
        cv2.namedWindow("ROI Selector", cv2.WINDOW_NORMAL)
        cv2.setMouseCallback("ROI Selector", self.mouse_callback)

        print("操作说明:")
        print("  鼠标左键拖拽: 绘制矩形框")
        print("  回车/空格: 确认并输出坐标")
        print("  c: 清空选择")
        print("  q/ESC: 退出")
        print()

        while True:
            cv2.imshow("ROI Selector", self.clone)
            key = cv2.waitKey(1) & 0xFF

            if key == ord('q') or key == 27:  # q 或 ESC
                break

            elif key == ord('c'):  # 清空
                self.clone = self.image.copy()
                self.roi = None
                print("已清空选择")

            elif key == 13 or key == 32:  # 回车 或 空格
                if self.roi:
                    x, y, w, h = self.roi
                    print(f"\nROI 坐标: x={x}, y={y}, width={w}, height={h}")
                    print(f"格式1 (x y w h): {x} {y} {w} {h}")
                    print(f"格式2 (x1 y1 x2 y2): {x} {y} {x+w} {y+h}")
                    print(f"Python切片 [y:y+h, x:x+w]")
                else:
                    print("请先选择一个区域")

        cv2.destroyAllWindows()


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(f"用法: python {sys.argv[0]} <图片路径>")
        print(f"示例: python {sys.argv[0]} iidx_score_reco/data/test.webp")
        sys.exit(1)

    selector = ROISelector(sys.argv[1])
    selector.run()

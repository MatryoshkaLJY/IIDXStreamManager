#!/usr/bin/env python3
"""
字体二值化处理脚本
将 font/ 目录下的数字图片转换为纯黑白
"""

import os
from PIL import Image
import numpy as np

def binarize_font(input_path, output_path, threshold=200):
    """
    二值化字体图片
    - 白色主体保留为白色(255)
    - 描边和背景转为黑色(0)
    """
    img = Image.open(input_path).convert('L')  # 转为灰度
    arr = np.array(img)

    # 二值化：高于阈值为白色，低于为黑色
    # 由于数字是白色主体，描边是深色，背景是黑色
    binary = np.where(arr > threshold, 255, 0).astype(np.uint8)

    result = Image.fromarray(binary, mode='L')
    result.save(output_path)
    print(f"✓ {os.path.basename(input_path)} -> {os.path.basename(output_path)}")
    return result

def main():
    font_dir = "iidx_score_reco/font"

    # 处理 0-9 所有数字
    for i in range(10):
        input_file = os.path.join(font_dir, f"{i}.png")
        output_file = os.path.join(font_dir, f"{i}_binary.png")

        if os.path.exists(input_file):
            binarize_font(input_file, output_file)
        else:
            print(f"✗ 未找到: {input_file}")

    print("\n二值化完成！")
    print("原始文件: 0.png ~ 9.png")
    print("二值化文件: 0_binary.png ~ 9_binary.png")

if __name__ == "__main__":
    main()

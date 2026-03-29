import cv2
import numpy as np
from pathlib import Path
from typing import List, Tuple, Optional, Dict


class IIDXDigitRecognizer:
    """
    IIDX 游戏分数数字识别器
    支持多颜色数字识别，使用二值化模板匹配
    """

    def __init__(self, font_dir: str = "font"):
        """
        加载数字模板 (0-9)

        Args:
            font_dir: 模板图片所在目录（使用二值化模板）
        """
        self.font_dir = Path(font_dir)
        self.templates: Dict[int, np.ndarray] = {}
        self.template_size = (20, 30)  # 统一模板尺寸 (宽, 高)

        self._load_templates()

    def _load_templates(self):
        """加载二值化模板并缩放到统一尺寸"""
        for i in range(10):
            # 优先使用二值化模板
            template_path = self.font_dir / f"{i}_binary.png"
            if not template_path.exists():
                template_path = self.font_dir / f"{i}.png"

            if not template_path.exists():
                raise FileNotFoundError(f"模板文件不存在: {template_path}")

            template = cv2.imread(str(template_path), cv2.IMREAD_GRAYSCALE)
            if template is None:
                raise ValueError(f"无法读取模板: {template_path}")

            # 二值化确保是黑白图
            _, binary = cv2.threshold(template, 127, 255, cv2.THRESH_BINARY)

            # 裁剪到内容区域
            binary = self._crop_to_content(binary)

            # 缩放到统一尺寸
            resized = cv2.resize(binary, self.template_size)

            self.templates[i] = resized

        print(f"已加载 {len(self.templates)} 个数字模板，尺寸: {self.template_size}")

    def _crop_to_content(self, img: np.ndarray) -> np.ndarray:
        """裁剪到非零内容的边界框"""
        coords = cv2.findNonZero(img)
        if coords is None:
            return img
        x, y, w, h = cv2.boundingRect(coords)
        return img[y:y+h, x:x+w]

    def _extract_digit_mask(self, img: np.ndarray) -> np.ndarray:
        """
        提取数字掩码，支持多种颜色
        数字通常是图片中最亮的部分
        """
        if len(img.shape) == 3:
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        else:
            gray = img.copy()

        # 使用固定高阈值提取亮像素（数字通常是亮的）
        _, binary = cv2.threshold(gray, 180, 255, cv2.THRESH_BINARY)

        # 如果提取不到足够像素，降低阈值
        if np.count_nonzero(binary) < 50:
            _, binary = cv2.threshold(gray, 150, 255, cv2.THRESH_BINARY)

        # 形态学操作连接断开的笔画
        kernel = np.ones((3, 3), np.uint8)
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)

        return binary

    def _segment_digits(self, binary_img: np.ndarray,
                        min_width: int = 5, max_width: int = 50,
                        min_gap: int = 3) -> List[Tuple[np.ndarray, int]]:
        """
        分割单个数字，返回数字图像和中心x坐标
        """
        h, w = binary_img.shape

        # 垂直投影
        projection = np.sum(binary_img > 0, axis=0)

        digits = []
        in_digit = False
        start = 0

        for i, val in enumerate(projection):
            if val > 0 and not in_digit:
                start = i
                in_digit = True
            elif val == 0 and in_digit:
                gap = i - start
                if gap >= min_gap:
                    digit = binary_img[:, start:i]
                    digit = self._crop_to_content(digit)
                    if digit.size > 0 and min_width <= digit.shape[1] <= max_width:
                        center_x = (start + i) // 2
                        digits.append((digit, center_x))
                in_digit = False

        # 处理最后一个数字
        if in_digit:
            digit = binary_img[:, start:w]
            digit = self._crop_to_content(digit)
            if digit.size > 0 and min_width <= digit.shape[1] <= max_width:
                center_x = (start + w) // 2
                digits.append((digit, center_x))

        # 按中心x坐标排序（从左到右）
        digits.sort(key=lambda x: x[1])

        return [d[0] for d in digits]

    def _match_template(self, digit_img: np.ndarray) -> Tuple[Optional[int], float]:
        """
        模板匹配，返回最佳匹配数字和分数
        """
        # 裁剪并调整大小
        digit_clean = self._crop_to_content(digit_img)
        if digit_clean.size == 0:
            return None, 0.0

        # 缩放到模板尺寸
        resized = cv2.resize(digit_clean, self.template_size)

        best_score = -1
        best_digit = None

        for digit, template in self.templates.items():
            # 使用归一化相关系数
            result = cv2.matchTemplate(resized, template, cv2.TM_CCOEFF_NORMED)
            score = result[0, 0]

            if score > best_score:
                best_score = score
                best_digit = digit

        # 阈值过滤
        if best_score < 0.5:
            return None, best_score

        return best_digit, best_score

    def recognize(self, image_path: str, roi: Optional[Tuple[int, int, int, int]] = None,
                  debug: bool = False) -> str:
        """
        识别图片中的数字

        Args:
            image_path: 截图路径
            roi: 数字区域 (x1, y1, x2, y2)
            debug: 是否输出调试信息

        Returns:
            识别出的数字字符串
        """
        img = cv2.imread(image_path, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"无法读取图片: {image_path}")

        if roi:
            x1, y1, x2, y2 = roi
            img = img[y1:y2, x1:x2]

        # 提取数字掩码
        binary = self._extract_digit_mask(img)

        if debug:
            cv2.imwrite('/tmp/debug_binary.png', binary)
            print(f"二值图非零像素: {np.count_nonzero(binary)}")

        # 分割数字
        digits = self._segment_digits(binary)

        if debug:
            print(f"分割到 {len(digits)} 个数字区域")

        # 匹配每个数字
        result = ""
        for i, digit_img in enumerate(digits):
            best_digit, score = self._match_template(digit_img)
            if debug:
                print(f"  数字 {i}: 识别为 {best_digit}, 置信度 {score:.4f}")
            if best_digit is not None:
                result += str(best_digit)

        return result

    def recognize_all_rois(self, image_path: str,
                           rois: List[Tuple[str, int, int, int, int]],
                           debug: bool = False) -> Dict[str, str]:
        """
        识别多个ROI区域的数字

        Args:
            image_path: 截图路径
            rois: ROI列表，每个ROI为 (name, x1, y1, x2, y2)
            debug: 是否输出调试信息

        Returns:
            字典，键为ROI名称，值为识别结果
        """
        img = cv2.imread(image_path, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError(f"无法读取图片: {image_path}")

        results = {}
        for roi in rois:
            name, x1, y1, x2, y2 = roi
            roi_img = img[y1:y2, x1:x2]

            if debug:
                print(f"\nROI {name}: ({x1},{y1})-({x2},{y2})")

            # 提取数字掩码
            binary = self._extract_digit_mask(roi_img)

            if debug:
                cv2.imwrite(f'/tmp/debug_{name}_binary.png', binary)

            # 分割数字
            digits = self._segment_digits(binary)

            if debug:
                print(f"  分割到 {len(digits)} 个数字")

            # 匹配
            result = ""
            for j, digit_img in enumerate(digits):
                best_digit, score = self._match_template(digit_img)
                if debug:
                    print(f"    数字区域 {j}: 识别为 {best_digit}, 置信度 {score:.4f}")
                if best_digit is not None:
                    result += str(best_digit)

            results[name] = result

        return results


if __name__ == "__main__":
    import sys

    recognizer = IIDXDigitRecognizer("font")

    if len(sys.argv) > 1:
        image_path = sys.argv[1]

        # 测试四个标准ROI
        rois = [
            ((1547, 488), (1700, 517)),
            ((1547, 549), (1700, 581)),
            ((1400, 488), (1547, 517)),
            ((1400, 549), (1547, 581)),
        ]

        results = recognizer.recognize_all_rois(image_path, rois, debug=True)
        print("\n最终识别结果:")
        for roi_name, result in results.items():
            print(f"  {roi_name}: {result}")
    else:
        print("用法: python recognizer.py <screenshot.png>")

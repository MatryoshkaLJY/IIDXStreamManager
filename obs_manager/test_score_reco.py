#!/usr/bin/env python3
"""
测试 obs_manager 的高分区域 ROI 识别功能
支持 rois.csv 配置的 ROI 区域
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from obs_manager import OBSManager


def test_capture_and_recognize_score():
    """测试抓取并识别高分区域"""
    print("="*50)
    print("测试: 抓取高分区域并识别 ROI")
    print("="*50)

    # 从 CSV 加载 ROI 配置
    csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rois.csv")
    rois = OBSManager.load_rois_from_csv(csv_path)
    print(f"从 CSV 加载了 {len(rois)} 个 ROI")

    with OBSManager(host="localhost", port=4455) as obs:
        print(f"可用视频源: {obs.get_sources()}")

        # 确定视频源
        source_name = "video" if "video" in obs.get_sources() else obs.get_sources()[0]
        print(f"\n使用视频源: {source_name}")

        # 抓取并识别
        print("\n[*] 抓取 1920x1080 图像并识别 ROI...")
        try:
            results = obs.capture_and_recognize_score(
                source_name=source_name,
                infer_addr=("127.0.0.1", 9877),
                target_size=(1920, 1080),
                rois=rois
            )
            print(f"[✓] 识别结果:")
            for roi_name, value in results.items():
                print(f"    {roi_name}: {value}")
        except Exception as e:
            print(f"[✗] 识别失败: {e}")
            import traceback
            traceback.print_exc()


def test_capture_score_regions():
    """测试抓取高分区域并保存 ROI"""
    print("\n" + "="*50)
    print("测试: 抓取高分区域并裁剪 ROI")
    print("="*50)

    # 从 CSV 加载 ROI 配置
    csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "rois.csv")
    rois = OBSManager.load_rois_from_csv(csv_path)
    print(f"从 CSV 加载了 {len(rois)} 个 ROI")

    with OBSManager(host="localhost", port=4455) as obs:
        source_name = "video" if "video" in obs.get_sources() else obs.get_sources()[0]
        print(f"使用视频源: {source_name}")

        # 抓取并裁剪 ROI
        print("\n[*] 抓取 1920x1080 图像...")
        results = obs.capture_score_regions(
            source_name=source_name,
            output_dir="/tmp/score_rois",
            target_size=(1920, 1080),
            rois=rois
        )

        print(f"[✓] 抓取完成:")
        print(f"    完整图像: {results['full'].size}")
        for roi_name in list(results.keys())[1:]:  # 跳过 'full'
            print(f"    {roi_name}: {results[roi_name].size}")

        print(f"\n[✓] ROI 图像已保存到: /tmp/score_rois/")


if __name__ == "__main__":
    test_capture_score_regions()
    test_capture_and_recognize_score()
    print("\n" + "="*50)
    print("测试完成")
    print("="*50)

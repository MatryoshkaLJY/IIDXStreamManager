#!/usr/bin/env python3
"""
推理脚本：对单帧/目录/视频流进行实时分类
用法：
  python3 infer.py --model classifier.pth image.jpg
  python3 infer.py --model classifier.pth frames_dir/
  python3 infer.py --model classifier.pth --benchmark   # 测速
"""

import os
import sys
import time
import argparse
from pathlib import Path

import torch
import torch.nn.functional as F
from torchvision import transforms, models
from PIL import Image

INPUT_SIZE = 224
TRANSFORM = transforms.Compose([
    transforms.Resize((INPUT_SIZE, INPUT_SIZE)),
    transforms.ToTensor(),
    transforms.Normalize([0.485, 0.456, 0.406],
                         [0.229, 0.224, 0.225]),
])


def load_labels(labels_path: str) -> list[str]:
    labels = {}
    with open(labels_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            idx, name = line.split("\t", 1)
            labels[int(idx)] = name
    return [labels[i] for i in range(len(labels))]


def build_model(num_classes: int, weights_path: str, device):
    from torchvision.models import efficientnet_b3
    import torch.nn as nn
    model = efficientnet_b3(weights=None)
    in_features = model.classifier[1].in_features
    model.classifier[1] = nn.Linear(in_features, num_classes)
    model.load_state_dict(torch.load(weights_path, map_location=device))
    model.to(device).eval()
    return model


@torch.no_grad()
def predict(model, img: Image.Image, device) -> torch.Tensor:
    x = TRANSFORM(img).unsqueeze(0).to(device)
    return F.softmax(model(x), dim=1)[0]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="classifier.pth 路径")
    parser.add_argument("--labels", default=None, help="标签文件（默认同模型名.labels.txt）")
    parser.add_argument("--no-cuda", action="store_true")
    parser.add_argument("--top", type=int, default=3, help="显示 top-N 预测")
    parser.add_argument("--benchmark", action="store_true", help="对随机图像测速")
    parser.add_argument("targets", nargs="*", help="图像文件或目录")
    args = parser.parse_args()

    device = torch.device("cpu" if args.no_cuda or not torch.cuda.is_available() else "cuda")
    labels_path = args.labels or str(Path(args.model).with_suffix(".labels.txt"))
    labels = load_labels(labels_path)
    model = build_model(len(labels), args.model, device)
    print(f"模型加载完成，{len(labels)} 类，设备: {device}")

    if args.benchmark:
        import torch
        dummy = torch.randn(1, 3, INPUT_SIZE, INPUT_SIZE).to(device)
        # warmup
        for _ in range(10):
            model(dummy)
        N = 200
        t0 = time.perf_counter()
        for _ in range(N):
            model(dummy)
        if device.type == "cuda":
            torch.cuda.synchronize()
        elapsed = time.perf_counter() - t0
        print(f"测速: {N} 次推理, 总耗时 {elapsed*1000:.1f}ms, "
              f"单帧 {elapsed/N*1000:.2f}ms, "
              f"最大吞吐 {N/elapsed:.0f} FPS")
        return

    # 收集目标文件
    files = []
    for target in args.targets:
        p = Path(target)
        if p.is_dir():
            files.extend(sorted(p.glob("*.jpg")) + sorted(p.glob("*.png")))
        elif p.exists():
            files.append(p)
        else:
            print(f"[警告] 找不到: {target}")

    if not files:
        parser.print_help()
        return

    for img_path in files:
        img = Image.open(img_path).convert("RGB")
        t0 = time.perf_counter()
        probs = predict(model, img, device)
        ms = (time.perf_counter() - t0) * 1000
        top_idx = probs.argsort(descending=True)[:args.top]
        result = labels[top_idx[0].item()]
        top_str = "  ".join(
            f"{labels[i]}:{probs[i]*100:.1f}%" for i in top_idx
        )
        print(f"{img_path.name:<30} → {result:<12}  [{top_str}]  {ms:.1f}ms")


if __name__ == "__main__":
    main()

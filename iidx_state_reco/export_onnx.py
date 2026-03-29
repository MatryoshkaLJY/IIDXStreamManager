#!/usr/bin/env python3
"""
将 classifier.pth 导出为 ONNX 格式

用法：
  python3 export_onnx.py --model classifier.pth
  python3 export_onnx.py --model classifier.pth --output classifier.onnx
"""

import argparse
from pathlib import Path

import torch
import torch.nn as nn
from torchvision import models


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


def build_model(n_classes: int, weights_path: str, device) -> nn.Module:
    model = models.mobilenet_v3_small(weights=None)
    in_features = model.classifier[3].in_features
    model.classifier[3] = nn.Linear(in_features, n_classes)
    model.load_state_dict(torch.load(weights_path, map_location=device))
    model.to(device).eval()
    return model


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="classifier.pth 路径")
    parser.add_argument("--labels", default=None, help="标签文件（默认同模型名.labels.txt）")
    parser.add_argument("--output", default=None, help="输出 .onnx 路径（默认同模型名.onnx）")
    parser.add_argument("--opset", type=int, default=17, help="ONNX opset 版本（默认 17）")
    args = parser.parse_args()

    device = torch.device("cpu")
    labels_path = args.labels or str(Path(args.model).with_suffix(".labels.txt"))
    output_path = args.output or str(Path(args.model).with_suffix(".onnx"))

    labels = load_labels(labels_path)
    print(f"标签数: {len(labels)}")

    model = build_model(len(labels), args.model, device)
    print("模型加载完成")

    dummy = torch.zeros(1, 3, 224, 224)
    torch.onnx.export(
        model,
        dummy,
        output_path,
        opset_version=args.opset,
        input_names=["image"],
        output_names=["logits"],
        dynamic_axes={"image": {0: "batch"}, "logits": {0: "batch"}},
    )
    print(f"已导出: {output_path}  (opset {args.opset})")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
使用 ONNX Runtime 进行推理

用法：
  python3 infer_onnx.py --model classifier.onnx image.jpg
  python3 infer_onnx.py --model classifier.onnx frames_dir/
  python3 infer_onnx.py --model classifier.onnx --benchmark
依赖：pip install onnxruntime  (GPU: pip install onnxruntime-gpu)
"""

import argparse
import time
from pathlib import Path

import numpy as np
from PIL import Image

# 预加载 PyTorch 附带的 CUDA 12 库，供 onnxruntime-gpu 的 CUDA provider 使用
import ctypes as _ctypes, glob as _glob, sys as _sys
for _site in _sys.path:
    if "site-packages" not in _site:
        continue
    _libs = _glob.glob(f"{_site}/nvidia/*/lib/lib*.so.*")
    if not _libs:
        continue
    for _so in _libs:
        try:
            _ctypes.CDLL(_so, mode=_ctypes.RTLD_GLOBAL)
        except OSError:
            pass
    break

MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
STD  = np.array([0.229, 0.224, 0.225], dtype=np.float32)


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


def preprocess(img: Image.Image) -> np.ndarray:
    img = img.convert("RGB").resize((224, 224), Image.BILINEAR)
    x = np.array(img, dtype=np.float32) / 255.0   # HWC [0,1]
    x = (x - MEAN) / STD                           # normalize
    return x.transpose(2, 0, 1)[np.newaxis]        # NCHW


def softmax(x: np.ndarray) -> np.ndarray:
    e = np.exp(x - x.max())
    return e / e.sum()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True, help="classifier.onnx 路径")
    parser.add_argument("--labels", default=None, help="标签文件（默认同模型名.labels.txt）")
    parser.add_argument("--top", type=int, default=3, help="显示 top-N 预测")
    parser.add_argument("--benchmark", action="store_true", help="对随机输入测速")
    parser.add_argument("targets", nargs="*", help="图像文件或目录")
    args = parser.parse_args()

    import onnxruntime as ort

    labels_path = args.labels or str(Path(args.model).with_suffix(".labels.txt"))
    labels = load_labels(labels_path)

    available = ort.get_available_providers()
    providers = ["CUDAExecutionProvider", "CPUExecutionProvider"] \
        if "CUDAExecutionProvider" in available else ["CPUExecutionProvider"]
    sess = ort.InferenceSession(args.model, providers=providers)
    input_name = sess.get_inputs()[0].name
    provider = sess.get_providers()[0]
    print(f"模型加载完成，{len(labels)} 类，后端: {provider}")

    if args.benchmark:
        dummy = np.random.randn(1, 3, 224, 224).astype(np.float32)
        for _ in range(10):          # warmup
            sess.run(None, {input_name: dummy})
        N = 200
        t0 = time.perf_counter()
        for _ in range(N):
            sess.run(None, {input_name: dummy})
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
        img = Image.open(img_path)
        x = preprocess(img)
        t0 = time.perf_counter()
        logits = sess.run(None, {input_name: x})[0][0]
        ms = (time.perf_counter() - t0) * 1000
        probs = softmax(logits)
        top_idx = probs.argsort()[::-1][:args.top]
        result = labels[top_idx[0]]
        top_str = "  ".join(f"{labels[i]}:{probs[i]*100:.1f}%" for i in top_idx)
        print(f"{img_path.name:<30} → {result:<12}  [{top_str}]  {ms:.1f}ms")


if __name__ == "__main__":
    main()

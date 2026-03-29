"""
MobileNetV3-Small 分类器训练脚本

用法:
    python3 train.py
    python3 train.py --epochs-head 10 --epochs-full 30 --batch-size 32 --val-ratio 0.2 --output classifier.pth
"""

import argparse
import os
import csv
import random
from collections import Counter
from pathlib import Path

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader, WeightedRandomSampler
from torchvision import transforms, models
from PIL import Image


# ──────────────────────────────────────────────
# 数据集
# ──────────────────────────────────────────────

def load_all_samples(root: str) -> list[tuple[str, str]]:
    """遍历所有会话目录，收集 (图像绝对路径, label) 列表。"""
    samples = []
    root_path = Path(root)
    for session_dir in sorted(root_path.iterdir()):
        if not session_dir.is_dir():
            continue
        csv_path = session_dir / "annotations.csv"
        if not csv_path.exists():
            continue
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                img_path = session_dir / row["filename"]
                if img_path.exists():
                    samples.append((str(img_path), row["label"]))
    return samples


def stratified_split(
    samples: list[tuple[str, str]],
    val_ratio: float,
    seed: int = 42,
) -> tuple[list, list]:
    """按类别比例随机划分训练/验证集。"""
    rng = random.Random(seed)
    by_class: dict[str, list] = {}
    for item in samples:
        by_class.setdefault(item[1], []).append(item)

    train_list, val_list = [], []
    for label, items in by_class.items():
        rng.shuffle(items)
        n_val = max(1, round(len(items) * val_ratio))
        val_list.extend(items[:n_val])
        train_list.extend(items[n_val:])

    rng.shuffle(train_list)
    rng.shuffle(val_list)
    return train_list, val_list


class FrameDataset(Dataset):
    def __init__(self, samples: list[tuple[str, str]], label2idx: dict, transform=None):
        self.samples = samples
        self.label2idx = label2idx
        self.transform = transform

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        path, label = self.samples[idx]
        img = Image.open(path).convert("RGB")
        if self.transform:
            img = self.transform(img)
        return img, self.label2idx[label]


# ──────────────────────────────────────────────
# 类不均衡处理
# ──────────────────────────────────────────────

def make_sampler(samples: list[tuple[str, str]], label2idx: dict) -> WeightedRandomSampler:
    """为训练集构造 WeightedRandomSampler，使每个类被均等采样。"""
    counts = Counter(label for _, label in samples)
    weight_per_class = {lb: 1.0 / cnt for lb, cnt in counts.items()}
    weights = [weight_per_class[label] for _, label in samples]
    return WeightedRandomSampler(weights, num_samples=len(weights), replacement=True)


def make_loss_weights(label2idx: dict, samples: list[tuple[str, str]], device) -> torch.Tensor:
    """计算 CrossEntropyLoss 的类权重（逆频率）。"""
    counts = Counter(label for _, label in samples)
    total = len(samples)
    n_cls = len(label2idx)
    weights = torch.ones(n_cls, device=device)
    for label, idx in label2idx.items():
        cnt = counts.get(label, 1)
        weights[idx] = total / (n_cls * cnt)
    return weights


# ──────────────────────────────────────────────
# 模型
# ──────────────────────────────────────────────

def build_model(n_classes: int) -> nn.Module:
    model = models.mobilenet_v3_small(weights=models.MobileNet_V3_Small_Weights.IMAGENET1K_V1)
    # 替换分类头
    in_features = model.classifier[3].in_features
    model.classifier[3] = nn.Linear(in_features, n_classes)
    return model


def freeze_backbone(model: nn.Module):
    for name, param in model.named_parameters():
        param.requires_grad = name.startswith("classifier")


def unfreeze_all(model: nn.Module):
    for param in model.parameters():
        param.requires_grad = True


# ──────────────────────────────────────────────
# 训练 / 验证循环
# ──────────────────────────────────────────────

def run_epoch(model, loader, criterion, optimizer, device, train: bool):
    model.train(train)
    total_loss = correct = total = 0
    with torch.set_grad_enabled(train):
        for imgs, labels in loader:
            imgs, labels = imgs.to(device), labels.to(device)
            logits = model(imgs)
            loss = criterion(logits, labels)
            if train:
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
            total_loss += loss.item() * len(labels)
            correct += (logits.argmax(1) == labels).sum().item()
            total += len(labels)
    return total_loss / total, correct / total


def train_stage(
    model, train_loader, val_loader, criterion, optimizer, scheduler,
    epochs: int, device, stage_name: str
):
    for epoch in range(1, epochs + 1):
        tr_loss, tr_acc = run_epoch(model, train_loader, criterion, optimizer, device, train=True)
        va_loss, va_acc = run_epoch(model, val_loader, criterion, None, device, train=False)
        scheduler.step()
        print(
            f"[{stage_name}] epoch {epoch:3d}/{epochs} "
            f"| train loss {tr_loss:.4f} acc {tr_acc:.3f} "
            f"| val loss {va_loss:.4f} acc {va_acc:.3f}"
        )


# ──────────────────────────────────────────────
# 主流程
# ──────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=".", help="out_frames 根目录")
    parser.add_argument("--val-ratio", type=float, default=0.2, help="验证集比例")
    parser.add_argument("--epochs-head", type=int, default=10, help="阶段1（冻结backbone）训练轮数")
    parser.add_argument("--epochs-full", type=int, default=20, help="阶段2（全网络）训练轮数")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--output", default="classifier.pth")
    args = parser.parse_args()

    torch.manual_seed(args.seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"使用设备: {device}")

    # ── 加载数据 ──
    all_samples = load_all_samples(args.root)
    if not all_samples:
        raise RuntimeError("未找到任何标注数据，请检查 --root 目录")

    all_labels = sorted({label for _, label in all_samples})
    label2idx = {lb: i for i, lb in enumerate(all_labels)}
    n_classes = len(all_labels)
    print(f"共 {len(all_samples)} 帧，{n_classes} 个类别")

    # 打印类分布
    counts = Counter(label for _, label in all_samples)
    print("类别分布（训练前全量）:")
    for lb in all_labels:
        print(f"  {lb:12s} {counts[lb]:5d}")

    # ── 划分 ──
    train_samples, val_samples = stratified_split(all_samples, args.val_ratio, args.seed)
    print(f"训练集 {len(train_samples)} 帧，验证集 {len(val_samples)} 帧")

    # ── Transform ──
    normalize = transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    train_tf = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.RandomHorizontalFlip(),
        transforms.ColorJitter(brightness=0.2, contrast=0.2, saturation=0.1),
        transforms.ToTensor(),
        normalize,
    ])
    val_tf = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        normalize,
    ])

    train_ds = FrameDataset(train_samples, label2idx, train_tf)
    val_ds   = FrameDataset(val_samples,   label2idx, val_tf)

    sampler = make_sampler(train_samples, label2idx)
    train_loader = DataLoader(train_ds, batch_size=args.batch_size, sampler=sampler,
                              num_workers=4, pin_memory=True)
    val_loader   = DataLoader(val_ds,   batch_size=args.batch_size, shuffle=False,
                              num_workers=4, pin_memory=True)

    # ── 模型 & 损失 ──
    model = build_model(n_classes).to(device)
    loss_weights = make_loss_weights(label2idx, train_samples, device)
    criterion = nn.CrossEntropyLoss(weight=loss_weights)

    # ── 阶段 1：只训练分类头 ──
    freeze_backbone(model)
    head_params = [p for p in model.parameters() if p.requires_grad]
    opt1 = torch.optim.Adam(head_params, lr=1e-3)
    sched1 = torch.optim.lr_scheduler.CosineAnnealingLR(opt1, T_max=args.epochs_head)
    print(f"\n=== 阶段1：冻结 backbone，训练分类头 ({args.epochs_head} epochs) ===")
    train_stage(model, train_loader, val_loader, criterion, opt1, sched1,
                args.epochs_head, device, "head")

    # ── 阶段 2：全网络 fine-tune ──
    unfreeze_all(model)
    opt2 = torch.optim.Adam([
        {"params": model.features.parameters(), "lr": 1e-4},
        {"params": model.classifier.parameters(), "lr": 5e-4},
    ])
    sched2 = torch.optim.lr_scheduler.CosineAnnealingLR(opt2, T_max=args.epochs_full)
    print(f"\n=== 阶段2：全网络 fine-tune ({args.epochs_full} epochs) ===")
    train_stage(model, train_loader, val_loader, criterion, opt2, sched2,
                args.epochs_full, device, "full")

    # ── 保存 ──
    torch.save(model.state_dict(), args.output)
    labels_file = Path(args.output).with_suffix("").as_posix() + ".labels.txt"
    with open(labels_file, "w", encoding="utf-8") as f:
        for idx, lb in enumerate(all_labels):
            f.write(f"{idx}\t{lb}\n")
    print(f"\n模型已保存至 {args.output}")
    print(f"标签映射已保存至 {labels_file}")


if __name__ == "__main__":
    main()

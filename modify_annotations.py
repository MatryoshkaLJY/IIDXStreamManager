#!/usr/bin/env python3
"""批量修改标注文件中的play标签"""
import csv
import os
import re
from pathlib import Path

def extract_frame_num(filename):
    """从frame_xxxxxx.jpg中提取数字"""
    match = re.search(r'frame_(\d+)\.jpg', filename)
    if match:
        return int(match.group(1))
    return None

def modify_csv_simple(csv_path, old_label, new_label):
    """简单替换：将所有old_label替换为new_label"""
    rows = []
    with open(csv_path, 'r', newline='') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows.append(header)
        for row in reader:
            if len(row) >= 2 and row[1] == old_label:
                row[1] = new_label
            rows.append(row)

    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    print(f"  [简单替换] {old_label} -> {new_label}")

def modify_csv_first_n(csv_path, old_label, new_label_for_first_n, new_label_for_others, n):
    """前N个替换为new_label_for_first_n，其余替换为new_label_for_others"""
    rows = []
    play_count = 0

    with open(csv_path, 'r', newline='') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows.append(header)
        for row in reader:
            if len(row) >= 2 and row[1] == old_label:
                play_count += 1
                if play_count <= n:
                    row[1] = new_label_for_first_n
                else:
                    row[1] = new_label_for_others
            rows.append(row)

    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    print(f"  [前{n}个特殊] 前{n}个{old_label}->{new_label_for_first_n}, 其余{old_label}->{new_label_for_others}")

def modify_csv_by_frame_range(csv_path, old_label, new_label_for_range, new_label_for_others, frame_ranges):
    """根据帧号范围替换：范围内的替换为new_label_for_range，其余替换为new_label_for_others"""
    rows = []
    modified_in_range = 0
    modified_others = 0

    with open(csv_path, 'r', newline='') as f:
        reader = csv.reader(f)
        header = next(reader)
        rows.append(header)
        for row in reader:
            if len(row) >= 2 and row[1] == old_label:
                frame_num = extract_frame_num(row[0])
                in_range = False
                if frame_num is not None:
                    for start, end in frame_ranges:
                        if start <= frame_num <= end:
                            in_range = True
                            break

                if in_range:
                    row[1] = new_label_for_range
                    modified_in_range += 1
                else:
                    row[1] = new_label_for_others
                    modified_others += 1
            rows.append(row)

    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    print(f"  [范围替换] 范围{frame_ranges}内{old_label}->{new_label_for_range}({modified_in_range}个), 其余{old_label}->{new_label_for_others}({modified_others}个)")

# 定义所有修改规则
RULES = [
    # (路径, 类型, 参数)
    # 类型: 'simple', 'first_n', 'frame_range'
    ("iidx_state_reco/data/2025-09-23 22-39-42", 'simple', {'new_label': 'playd'}),
    ("iidx_state_reco/data/2025-09-23 22-55-04", 'simple', {'new_label': 'playd'}),
    ("iidx_state_reco/data/2025-09-23 23-13-48", 'simple', {'new_label': 'playd'}),
    ("iidx_state_reco/data/2025-09-23 23-38-37", 'simple', {'new_label': 'playd'}),
    ("iidx_state_reco/data/2025-09-24 21-28-15", 'simple', {'new_label': 'playd'}),
    ("iidx_state_reco/data/2025-10-24 00-07-08", 'simple', {'new_label': 'playd'}),
    ("iidx_state_reco/data/2025-11-02 22-15-30", 'simple', {'new_label': 'playd'}),
    ("iidx_state_reco/data/2025-11-09 22-38-17", 'first_n', {'n': 8, 'new_label_for_first_n': 'play12', 'new_label_for_others': 'playd'}),
    ("iidx_state_reco/data/2025-11-09 22-49-17", 'simple', {'new_label': 'playd'}),
    ("iidx_state_reco/data/2025-11-09 22-59-06", 'first_n', {'n': 2, 'new_label_for_first_n': 'play12', 'new_label_for_others': 'playd'}),
    ("iidx_state_reco/data/2025-12-29 17-48-36", 'simple', {'new_label': 'play2'}),
    ("iidx_state_reco/data/2026-03-18 13-08-41", 'frame_range', {'frame_ranges': [(34, 43), (6213, 6277)], 'new_label_for_range': 'play12', 'new_label_for_others': 'playd'}),
    ("iidx_state_reco/data/bpl", 'simple', {'new_label': 'play1'}),
    ("iidx_state_reco/data/carena", 'simple', {'new_label': 'play1'}),
    ("iidx_state_reco/data/carena_cleaned", 'simple', {'new_label': 'play1'}),
    ("iidx_state_reco/data/kbpl", 'simple', {'new_label': 'play1'}),
    ("iidx_state_reco/data/kbpl_cleaned", 'simple', {'new_label': 'play1'}),
    ("iidx_state_reco/data/sarena", 'simple', {'new_label': 'play2'}),
]

def main():
    base_dir = Path("/home/matryoshka/Downloads/out_frames")

    for rel_path, rule_type, params in RULES:
        csv_path = base_dir / rel_path / "annotations.csv"

        if not csv_path.exists():
            print(f"跳过: {rel_path} (文件不存在)")
            continue

        print(f"\n处理: {rel_path}")

        # 备份原文件
        backup_path = csv_path.with_suffix('.csv.backup')
        if not backup_path.exists():
            import shutil
            shutil.copy2(csv_path, backup_path)
            print(f"  已备份到: {backup_path}")

        if rule_type == 'simple':
            modify_csv_simple(csv_path, 'play', params['new_label'])
        elif rule_type == 'first_n':
            modify_csv_first_n(csv_path, 'play', params['new_label_for_first_n'], params['new_label_for_others'], params['n'])
        elif rule_type == 'frame_range':
            modify_csv_by_frame_range(csv_path, 'play', params['new_label_for_range'], params['new_label_for_others'], params['frame_ranges'])

    print("\n所有修改完成!")

if __name__ == "__main__":
    main()

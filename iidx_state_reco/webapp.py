#!/usr/bin/env python3
"""Web-based image annotation tool for classification datasets."""

import csv
import json
import os

from flask import Flask, jsonify, render_template, request, send_file

BASE = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__, template_folder=os.path.join(BASE, "templates"))

# Cache: model_path → (model, label_list, device)
_infer_cache = {}

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}


def get_tags():
    path = os.path.join(BASE, "tags.txt")
    with open(path, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]


DATA_DIR = "data"


def _collect_session_dirs(root_path: str, prefix: str = "") -> list:
    """递归收集所有包含图片的目录作为会话."""
    sessions = []
    try:
        entries = sorted(os.listdir(root_path))
    except OSError:
        return sessions

    has_images = False
    subdirs = []

    for name in entries:
        if name.startswith("."):
            continue
        full_path = os.path.join(root_path, name)
        if os.path.isdir(full_path):
            subdirs.append(name)
        elif os.path.splitext(name)[1].lower() in IMAGE_EXTS:
            has_images = True

    # 如果当前目录有图片，将其作为会话
    if has_images and prefix:
        sessions.append(prefix)

    # 递归处理子目录
    for subdir in subdirs:
        new_prefix = f"{prefix}/{subdir}" if prefix else subdir
        sub_path = os.path.join(root_path, subdir)
        sessions.extend(_collect_session_dirs(sub_path, new_prefix))

    return sessions


def get_sessions():
    # 优先从 data 目录收集
    data_path = os.path.join(BASE, DATA_DIR)
    if os.path.isdir(data_path):
        return _collect_session_dirs(data_path, DATA_DIR)

    # 如果 data 不存在，从根目录收集（排除隐藏目录）
    return _collect_session_dirs(BASE, "")


def get_images(session):
    path = os.path.join(BASE, session)
    return sorted(
        f for f in os.listdir(path)
        if os.path.splitext(f)[1].lower() in IMAGE_EXTS
    )


def load_annotations(session):
    csv_path = os.path.join(BASE, session, "annotations.csv")
    if not os.path.exists(csv_path):
        return {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        return {row["filename"]: row.get("label", "") for row in csv.DictReader(f)}


def save_annotations_csv(session, annotations):
    images = get_images(session)
    csv_path = os.path.join(BASE, session, "annotations.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["filename", "label"])
        for fname in images:
            w.writerow([fname, annotations.get(fname, "")])


# ── Routes ────────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/tags")
def api_tags():
    return jsonify(get_tags())


@app.route("/api/sessions")
def api_sessions():
    result = []
    for name in get_sessions():
        images = get_images(name)
        ann = load_annotations(name)
        labeled = sum(1 for f in images if ann.get(f))
        result.append({"name": name, "total": len(images), "labeled": labeled})
    return jsonify(result)


@app.route("/api/session/<path:session>/images")
def api_images(session):
    images = get_images(session)
    ann = load_annotations(session)
    return jsonify([{"filename": f, "label": ann.get(f, "")} for f in images])


@app.route("/img/<path:session>/<filename>")
def serve_image(session, filename):
    path = os.path.join(BASE, session, filename)
    if not os.path.abspath(path).startswith(BASE):
        return "Forbidden", 403
    return send_file(path)


@app.route("/api/session/<path:session>/annotate", methods=["POST"])
def api_annotate(session):
    data = request.get_json()  # {filename: label, ...}
    if not isinstance(data, dict):
        return jsonify({"error": "invalid payload"}), 400
    ann = load_annotations(session)
    ann.update(data)
    save_annotations_csv(session, ann)
    return jsonify({"ok": True})


def load_predictions(session):
    csv_path = os.path.join(BASE, session, "predictions.csv")
    if not os.path.exists(csv_path):
        return {}
    result = {}
    with open(csv_path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            result[row["filename"]] = {
                "predicted":  row.get("predicted", ""),
                "confidence": float(row.get("confidence", 0)),
                "scores":     json.loads(row.get("scores", "{}")),
            }
    return result


@app.route("/verify")
def verify():
    return render_template("verify.html")


@app.route("/api/session/<path:session>/predictions")
def api_predictions(session):
    return jsonify(load_predictions(session))


@app.route("/api/session/<path:session>/infer", methods=["POST"])
def api_infer(session):
    """Run model inference on all frames in the session, save predictions.csv."""
    try:
        import torch
        import torch.nn as nn
        import torch.nn.functional as F
        from torchvision import transforms
        from torchvision.models import mobilenet_v3_small
        from PIL import Image
    except ImportError as e:
        return jsonify({"error": f"Missing dependency: {e}"}), 500

    data = request.get_json() or {}
    raw_model   = data.get("model", "classifier.pth")
    model_path  = raw_model if os.path.isabs(raw_model) else os.path.join(BASE, raw_model)
    labels_path = data.get("labels") or os.path.splitext(model_path)[0] + ".labels.txt"

    if not os.path.exists(model_path):
        return jsonify({"error": f"Model not found: {model_path}"}), 404
    if not os.path.exists(labels_path):
        return jsonify({"error": f"Labels file not found: {labels_path}"}), 404

    # Load or reuse cached model
    if model_path not in _infer_cache:
        raw = {}
        with open(labels_path) as f:
            for line in f:
                line = line.rstrip("\n\r")
                if line:
                    parts = line.split("\t", 1)
                    idx = parts[0]
                    name = parts[1] if len(parts) > 1 else ""
                    raw[int(idx)] = name
        label_list = [raw[i] for i in range(len(raw))]

        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = mobilenet_v3_small(weights=None)
        in_features = model.classifier[3].in_features
        model.classifier[3] = nn.Linear(in_features, len(label_list))
        model.load_state_dict(torch.load(model_path, map_location=device, weights_only=True))
        model.to(device).eval()
        _infer_cache[model_path] = (model, label_list, device)

    model, label_list, device = _infer_cache[model_path]

    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])

    session_images = get_images(session)
    rows = []
    with torch.no_grad():
        for fname in session_images:
            img_path = os.path.join(BASE, session, fname)
            img = Image.open(img_path).convert("RGB")
            x = transform(img).unsqueeze(0).to(device)
            probs = F.softmax(model(x), dim=1)[0].cpu().tolist()
            scores = {label_list[i]: round(probs[i], 4) for i in range(len(label_list))}
            predicted   = max(scores, key=scores.get)
            confidence  = scores[predicted]
            rows.append((fname, predicted, confidence, scores))

    csv_path = os.path.join(BASE, session, "predictions.csv")
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["filename", "predicted", "confidence", "scores"])
        for fname, predicted, confidence, scores in rows:
            w.writerow([fname, predicted, round(confidence, 4), json.dumps(scores)])

    # Fill unannotated frames with predicted labels
    ann = load_annotations(session)
    filled = 0
    for fname, predicted, confidence, scores in rows:
        if not ann.get(fname):
            ann[fname] = predicted
            filled += 1
    if filled:
        save_annotations_csv(session, ann)

    return jsonify({"ok": True, "count": len(rows), "filled": filled})


@app.route("/browse")
def browse():
    return render_template("browse.html")


@app.route("/browse_img")
def browse_img():
    path = request.args.get("path", "")
    if not path:
        return "Bad request", 400
    path = os.path.normpath(path)
    if not os.path.isabs(path):
        return "Forbidden", 403
    if os.path.splitext(path)[1].lower() not in IMAGE_EXTS:
        return "Forbidden", 403
    if not os.path.isfile(path):
        return "Not found", 404
    return send_file(path)


@app.route("/api/browse/infer", methods=["POST"])
def api_browse_infer():
    """Run inference on all images in an arbitrary directory, return results as JSON."""
    try:
        import torch
        import torch.nn as nn
        import torch.nn.functional as F
        from torchvision import transforms
        from torchvision.models import mobilenet_v3_small
        from PIL import Image as PILImage
    except ImportError as e:
        return jsonify({"error": f"Missing dependency: {e}"}), 500

    data = request.get_json() or {}
    dir_path    = data.get("dir", "").strip()
    raw_model   = data.get("model", "classifier.pth").strip()
    model_path  = raw_model if os.path.isabs(raw_model) else os.path.join(BASE, raw_model)
    labels_path = data.get("labels") or os.path.splitext(model_path)[0] + ".labels.txt"

    if not dir_path or not os.path.isdir(dir_path):
        return jsonify({"error": f"Directory not found: {dir_path!r}"}), 404
    if not os.path.exists(model_path):
        return jsonify({"error": f"Model not found: {model_path}"}), 404
    if not os.path.exists(labels_path):
        return jsonify({"error": f"Labels file not found: {labels_path}"}), 404

    if model_path not in _infer_cache:
        raw = {}
        with open(labels_path) as f:
            for line in f:
                line = line.rstrip("\n\r")
                if line:
                    parts = line.split("\t", 1)
                    raw[int(parts[0])] = parts[1] if len(parts) > 1 else ""
        label_list = [raw[i] for i in range(len(raw))]
        device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        model = mobilenet_v3_small(weights=None)
        in_features = model.classifier[3].in_features
        model.classifier[3] = nn.Linear(in_features, len(label_list))
        model.load_state_dict(torch.load(model_path, map_location=device, weights_only=True))
        model.to(device).eval()
        _infer_cache[model_path] = (model, label_list, device)

    model, label_list, device = _infer_cache[model_path]
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
        transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225]),
    ])

    files = sorted(
        f for f in os.listdir(dir_path)
        if os.path.splitext(f)[1].lower() in IMAGE_EXTS
    )

    results = []
    with torch.no_grad():
        for fname in files:
            img_path = os.path.join(dir_path, fname)
            try:
                img = PILImage.open(img_path).convert("RGB")
            except Exception:
                continue
            x = transform(img).unsqueeze(0).to(device)
            probs = F.softmax(model(x), dim=1)[0].cpu().tolist()
            scores = {label_list[i]: round(probs[i], 4) for i in range(len(label_list))}
            predicted  = max(scores, key=scores.get)
            confidence = scores[predicted]
            results.append({
                "filename":   fname,
                "path":       img_path,
                "predicted":  predicted,
                "confidence": round(confidence, 4),
                "scores":     scores,
            })

    return jsonify({"ok": True, "count": len(results), "results": results})


if __name__ == "__main__":
    print(f"Starting annotation server at http://localhost:5000")
    print(f"Base directory: {BASE}")
    app.run(debug=False, port=5000)

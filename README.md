# IIDX Stream Assistant

<p align="center">
  <strong>beatmania IIDX 直播辅助工具集</strong> | <strong>beatmania IIDX Stream Assistant Toolset</strong> | <strong>beatmania IIDX 配信支援ツールセット</strong>
</p>

---

## 🌐 Language / 语言 / 言語

- [English](#english)
- [简体中文](#简体中文)
- [日本語](#日本語)

---

<a name="english"></a>
## English

### Overview

IIDX Stream Assistant is a comprehensive toolset designed for beatmania IIDX arcade game streaming. It provides automated scene recognition, score tracking, state management, and professional broadcasting overlays.

### Features

| Module | Description |
|--------|-------------|
| **iidx_state_reco** | Deep learning-based game screen state recognition (entry, play, score, etc.) |
| **iidx_score_reco** | Real-time score recognition from game result screens via TCP service |
| **iidx_state_machine** | Game state machine tracking arena/battle/standard/dan modes |
| **obs_manager** | OBS Studio integration for automated capture and recognition |
| **iidx_bpl_scoreboard** | Professional BPL-style scoreboard with WebSocket control |
| **tpl_scene_switcher** | TPL tournament scene switcher with Streamlit interface |

### Quick Start

```bash
# 1. State Recognition Service
python iidx_state_reco/serve.py --checkpoint model.pt --port 9876

# 2. Score Recognition Service
python iidx_score_reco/serve.py --font font/ --port 9877 --rois-csv rois.csv

# 3. OBS Manager (Multi-machine tracking)
python obs_manager/obs_manager.py --host localhost --port 4455 --password your_password
```

### System Architecture

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  OBS Studio │────▶│ OBS Manager │────▶│  State Reco │
│  (Source)   │     │ (WebSocket) │     │   (TCP)     │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌─────────┐  ┌──────────┐  ┌───────────┐
        │State    │  │  Score   │  │   BPL     │
        │Machine  │  │  Reco    │  │ Scoreboard│
        └─────────┘  └──────────┘  └───────────┘
```

### TODO

- [ ] **Copyright Content Detection & Masking**: Implement automatic detection and masking of copyrighted content (such as licensed songs, logos) to prevent stream takedowns or demonetization.

---

<a name="简体中文"></a>
## 简体中文

### 项目简介

IIDX Stream Assistant 是一个专为 beatmania IIDX 街机游戏直播设计的综合工具集。它提供自动场景识别、分数追踪、状态管理和专业直播画面叠加功能。

### 功能模块

| 模块 | 说明 |
|------|------|
| **iidx_state_reco** | 基于深度学习的游戏画面状态识别（入场、游玩、分数等） |
| **iidx_score_reco** | TCP服务方式实时识别游戏结算画面分数 |
| **iidx_state_machine** | 游戏状态机，追踪竞技场/对战/标准/段位模式 |
| **obs_manager** | OBS Studio 集成，实现自动捕获和识别 |
| **iidx_bpl_scoreboard** | 专业BPL风格记分板，支持WebSocket控制 |
| **tpl_scene_switcher** | TPL比赛场景切换器，提供Streamlit界面 |

### 快速开始

```bash
# 1. 启动状态识别服务
python iidx_state_reco/serve.py --checkpoint model.pt --port 9876

# 2. 启动分数识别服务
python iidx_score_reco/serve.py --font font/ --port 9877 --rois-csv rois.csv

# 3. 启动OBS管理器（多机器追踪）
python obs_manager/obs_manager.py --host localhost --port 4455 --password your_password
```

### 系统架构

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  OBS Studio │────▶│   OBS管理器  │────▶│   状态识别   │
│   (视频源)   │     │ (WebSocket) │     │   (TCP)     │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌─────────┐  ┌──────────┐  ┌───────────┐
        │ 状态机   │  │  分数识别  │  │  BPL记分板 │
        └─────────┘  └──────────┘  └───────────┘
```

### TODO

- [ ] **添加版权内容识别与遮挡的功能，防止直播因版权内容被切断或剥夺收益化**

---

<a name="日本語"></a>
## 日本語

### プロジェクト概要

IIDX Stream Assistant は、beatmania IIDX アーケードゲームの配信向けに設計された包括的なツールセットです。自動画面認識、スコア追跡、状態管理、およびプロフェッショナルな配信オーバーレイ機能を提供します。

### 機能モジュール

| モジュール | 説明 |
|-----------|------|
| **iidx_state_reco** | ディープラーニングベースのゲーム画面状態認識（エントリー、プレイ、スコアなど） |
| **iidx_score_reco** | TCPサービスによるゲーム結果画面のリアルタイムスコア認識 |
| **iidx_state_machine** | ゲーム状態マシン、アリーナ/バトル/スタンダード/段位モードを追跡 |
| **obs_manager** | OBS Studio との統合、自動キャプチャーと認識を実現 |
| **iidx_bpl_scoreboard** | プロフェッショナルなBPLスタイルのスコアボード、WebSocket制御対応 |
| **tpl_scene_switcher** | TPL大会用シーン切り替え器、Streamlitインターフェース付き |

### クイックスタート

```bash
# 1. 状態認識サービスの起動
python iidx_state_reco/serve.py --checkpoint model.pt --port 9876

# 2. スコア認識サービスの起動
python iidx_score_reco/serve.py --font font/ --port 9877 --rois-csv rois.csv

# 3. OBSマネージャーの起動（マルチ筐体追跡）
python obs_manager/obs_manager.py --host localhost --port 4455 --password your_password
```

### システムアーキテクチャ

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  OBS Studio │────▶│ OBSマネージャー│────▶│  状態認識   │
│  (ソース)    │     │ (WebSocket) │     │   (TCP)     │
└─────────────┘     └──────┬──────┘     └─────────────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌─────────┐  ┌──────────┐  ┌───────────┐
        │状態マシン│  │  スコア認識 │  │  BPLスコアボード│
        └─────────┘  └──────────┘  └───────────┘
```

### TODO

- [ ] **著作権コンテンツの検出とマスキング機能を追加し、配信が著作権コンテンツによって切断されたり収益化が剥奪されたりするのを防ぐ**

---

## 📁 Project Structure / 项目结构 / プロジェクト構成

```
.
├── iidx_state_reco/          # Game state recognition (CNN classifier)
│   ├── train.py              # Training script
│   ├── serve.py              # TCP inference server
│   ├── infer.py              # Inference utilities
│   └── export_onnx.py        # ONNX export
│
├── iidx_score_reco/          # Score recognition (template matching)
│   ├── recognizer.py         # Core recognition class
│   ├── serve.py              # TCP service
│   └── rois.csv              # ROI configuration
│
├── iidx_state_machine/       # Game state machine
│   ├── state_machine.py      # State machine implementation
│   └── state_machine.yaml    # State definitions
│
├── obs_manager/              # OBS Studio integration
│   ├── obs_manager.py        # Main OBS manager
│   └── web_monitor.py        # Web-based monitor
│
├── iidx_bpl_scoreboard/      # BPL-style scoreboard
│   ├── index.html            # Scoreboard display
│   ├── app.js                # Frontend logic
│   └── testbench/            # Python WebSocket server
│
└── tpl_scene_switcher/       # TPL tournament switcher
    ├── streamlit_app.py      # Streamlit interface
    └── switcher.py           # Scene switching logic
```

## 🔧 Dependencies / 依赖 / 依存関係

### Core / 核心 / コア
- Python 3.8+
- PyTorch (for state recognition)
- OpenCV
- NumPy
- Pillow

### OBS Integration / OBS集成 / OBS連携
- obsws-python

### BPL Scoreboard / BPL记分板 / BPLスコアボード
- websockets (Python) or ws (Node.js)

### TPL Switcher / TPL切换器 / TPLスイッチャー
- streamlit
- pyserial

## 🤝 Contributing / 贡献 / コントリビューション

Contributions are welcome! Please feel free to submit issues or pull requests.

欢迎贡献！请随时提交 Issue 或 Pull Request。

コントリビューションを歓迎します！Issue や Pull Request を自由に送信してください。

## 📄 License / 许可证 / ライセンス

MIT License

---

<p align="center">
  Made with ❤️ for the beatmania IIDX community<br/>
  为 beatmania IIDX 社区精心制作<br/>
  beatmania IIDX コミュニティのために作りました
</p>

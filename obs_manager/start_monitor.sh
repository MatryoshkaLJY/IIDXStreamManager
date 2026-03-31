#!/bin/bash
# IIDX Game State Monitor 启动脚本

cd "$(dirname "$0")"

# 检查依赖
echo "检查依赖..."

python3 -c "import flask" 2>/dev/null || {
    echo "安装 Flask..."
    pip3 install flask flask-cors
}

python3 -c "import obsws_python" 2>/dev/null || {
    echo "安装 obsws-python..."
    pip3 install obsws-python
}

python3 -c "import PIL" 2>/dev/null || {
    echo "安装 Pillow..."
    pip3 install pillow
}

# 启动 Web 服务
echo ""
echo "================================"
echo "IIDX Game State Monitor"
echo "================================"
echo "访问地址: http://localhost:5001"
echo "================================"
echo ""

python3 web_monitor.py --host 0.0.0.0 --port 5001

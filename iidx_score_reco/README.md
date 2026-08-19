# iidx_score_reco

基于 OpenCV 模板匹配的 IIDX 成绩/BP 识别服务。服务接收 JPEG/PNG 等截图，按 rois.csv 裁剪 1P/2P 区域，返回 JSON。

## 启动

    python serve.py --font font/ --port 9877 --rois-csv rois.csv --image-size 1920,1080

参数：--font 模板目录，--port TCP 端口，--host 绑定地址，--rois-csv ROI 文件，--image-size 输入尺寸。默认服务绑定 127.0.0.1:9877。

## TCP 协议

每个请求为：

    [4-byte big-endian uint32 length][image bytes]

服务返回一行 JSON，例如：

    {"1pscore":"2356","2pscore":"1987","1pbp":"12","2pbp":"8"}

注意键名是 1pscore、2pscore、1pbp、2pbp，不带下划线。发送长度 0 的 4 字节头会关闭连接；一个连接可发送多个请求。

## ROI 与模板

rois.csv 使用 name,x1,y1,x2,y2，坐标基于 1920x1080。font/ 中的 0.png 至 9.png 和二值模板用于数字匹配。修改 ROI 或模板后应使用真实截图回归。

## 测试

    python test.py --test-font
    python test.py <image>

导播台会自动启动该服务；独立运行时确保 OpenCV、NumPy、Pillow 已安装。

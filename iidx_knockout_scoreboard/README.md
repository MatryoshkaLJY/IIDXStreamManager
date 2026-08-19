# iidx_knockout_scoreboard

个人淘汰赛浏览器源，面向 OBS 1920x1080。页面由 app.js 驱动，server.py 在 8081 提供 WebSocket relay。

## 启动

    python server.py

浏览器或 OBS 源地址：

    http://127.0.0.1:5003/scoreboard/knockout/

生产环境由 iidx_director 自动启动；单独使用时可直接打开 index.html 或使用本地 HTTP 服务。

## 协议和规则

支持 init、score、settle、continue、reset。16 人赛按 A→B→C→D→E→F→finals 推进；8 人 EF 赛使用 startGroup: E；4 人决赛使用 startGroup: finals。

小组每局按竞争排名累计 PT 2/1/0/0，前两名晋级。决赛按 PT 排名，任何并列进入加赛。finals 的载荷 group 必须是 finals，不是 final。

## 测试

    node app.test.js
    python testbench.py -s manual

无构建步骤；npm 依赖只用于 jsdom 测试。完整协议和手动场景见 testbench.py 与 app.test.js。

# iidx_bpl_scoreboard

1920x1080 的 BPL 风格团队赛浏览器源。前端是原生 HTML/CSS/JavaScript，server.py 是端口 8080 的 WebSocket relay，无构建步骤。

## 启动

    python server.py

在 OBS 添加浏览器源：

    http://127.0.0.1:5003/scoreboard/bpl/

生产环境通常由 iidx_director 自动启动 relay；单独调试时直接运行上面的命令，并打开 index.html 或本地 HTTP 地址。

## 指令

relay 广播 JSON：

- init：队伍、选手、回合和初始 PT；
- score：更新当前回合结果；
- reset：清空比赛。

完整字段和示例见 PROTOCOL.md。导播台在 1v1/2v2、抢夺赛和重推时负责构造载荷，本组件只负责显示和转发。

## 测试

    cd testbench
    python testbench.py --demo

testbench/ 是手动/集成测试工具，不是生产 relay 的启动目录。OBS 源固定 1920x1080。

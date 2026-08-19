# iidx_state_machine

由 state_machine.yaml 驱动的 IIDX 游戏状态机。支持文件调试和 TCP 服务两种输入方式，维护 arena、battle、standard、dan 等模式的计数器与状态迁移。

## 调试

    python state_machine.py -c state_machine.yaml -i test_input.txt

## TCP 服务

    python state_machine.py -m tcp --host 0.0.0.0 --port 9999

输入可以是纯文本事件或包含 event 字段的 JSON。输出为 JSON，包含 old_state、current_state、transition、actions_triggered、variables_before、variables_after 和 handled。

## 配置

state_machine.yaml 定义 states、events、variables、actions、guards 和 transitions。不要在导播台运行时随意修改配置；iidx_director 当前将状态机作为 obs_manager 的进程内组件使用，生产抓分流程已改为导播手动触发。

## 测试

    python test_state_machine_manager.py
    python state_machine.py -c state_machine.yaml -i test_input.txt > /tmp/state.json

result.txt 和 result_tcp.txt 是样例结果，不是运行时状态。

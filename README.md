# Motor Run-in Test

基于 Python 3.9 和 PySide6 的电机跑合测试上位机。

## 运行

在 PyCharm 中选择项目解释器：

    .venv/bin/python

然后直接运行根目录 main.py。

## 目录职责

- main.py：程序入口和主窗口事件连接。
- ui/：Qt Designer 源文件、生成的界面代码和弹窗。
- drivers/：PLC、仪表、传感器等硬件驱动。
- services/：跑合流程、配置、数据保存和服务器上传。
- workers/：设备读取、测试和上传后台任务。
- models/：产品、设备状态和测试记录数据模型。
- config/：应用、设备、跑合工艺和服务器配置。
- utils/：日志、路径和参数校验工具。
- data/：本地测试数据。
- logs/：程序运行日志。
- exports/：报表和数据导出。
- tests/：自动测试。

## 修改界面

使用 Qt Designer 修改 ui/main.ui。保存后通过 PySide6 uic 重新生成
ui/ui_main.py。ui_main.py 是生成文件，不应手工修改。

## 托盘上料与 SN 录入

1. PLC 读取 RFID 后调用 MainWindow.set_tray_id(tray_id) 显示托盘编号。
2. 扫码器按键盘输入方式录入 SN，扫码结束发送回车即可自动跳到下一位置。
   程序兼容 Return、Enter、CR、LF；若扫码枪结束符未被 Qt 识别，快速输入
   停止 180 ms 后也会自动确认。相关参数在 config/app.json 的 scanner 中。
3. 只扫描第一个 SN 时，可点击“顺序补齐”生成其余 9 个连续 SN。
4. 点击“写入 PLC”后，主窗口发出 serial_numbers_ready(tray_id, serial_numbers)
   信号；后台 PLC 线程完成实际寄存器写入和回读校验。

## PLC 托盘数据映射

- D3580-D3581：RFID 托盘号，只读。
- D3582-D3583：位置 1 电机 SN。
- D3584-D3585：位置 2 电机 SN。
- 后续位置每次递增 2 个 D 寄存器。
- D3600-D3601：位置 10 电机 SN。

托盘号和每个 SN 均按 UINT32/UDINT 保存，默认低字在前、高字在后。二维码
中的 SN 必须是纯数字且不超过 4294967295。PLC 地址、字序和连接参数均可在
config/devices.json 中调整。

## 开发约定

1. 界面事件只负责收集输入和展示结果。
2. 设备通信统一放在 drivers。
3. 测试流程、数据保存和上传统一放在 services。
4. 耗时操作使用 workers，不阻塞 Qt 主线程。
5. 密码和令牌放在 .env，不提交到 Git。

# iidx_state_reco

基于 ONNX 的 IIDX 画面状态分类器，包含训练、导出和 TCP 推理代码。生产版 iidx_director 已弃用自动状态识别抓分，因此该组件不会随导播台自动启动，模型文件仅作备用和研究用途。

## 备用启动

    python serve.py --model classifier_augmented_medium.onnx --tcp 9876

服务协议为 4 字节大端图像长度加图像数据，返回状态标签。状态标签和模型必须匹配；ONNX 外部权重 classifier_augmented_medium.onnx.data 不能改名。

## 工具

- infer_onnx.py：使用 ONNX Runtime 推理；
- train.py：训练分类器；
- export_onnx.py：导出 ONNX；
- annotate.py、webapp.py：数据标注工具；
- prepare_augmented_data.py：准备增强数据。

训练数据、模型权重和压缩包较大，不应在日常代码提交中重新生成或改名。

## 测试

    python test_prepare_augmented_data.py

真实推理需要 onnxruntime 和对应模型文件；导播台生产抓分请使用 iidx_score_reco 的手动截图流程。

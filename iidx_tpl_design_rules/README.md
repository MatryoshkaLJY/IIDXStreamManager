# iidx_tpl_design_rules

IIDX 直播 overlay 的静态设计规格，不包含运行代码。图片文件记录 SP/DP 歌曲信息、手元、Judge、BPM 和柱状图等区域的参考尺寸。

## 使用方式

设计背景时以 1920x1080 画布为基准，保留文字和动态成绩区域。文字图层由 iidx_director 的 overlay 页面通过 WebSocket 叠加，背景资源不应把动态文字烘焙进去。

目录中的 PNG 缩略图对应 README 原始设计稿；调整布局后需同步 iidx_director/overlay/overlay-assets 和模板名称。

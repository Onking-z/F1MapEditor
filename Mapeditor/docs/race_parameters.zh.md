# 赛道比赛参数

入口：**Project → Track race parameters …**（项目 → 赛道比赛参数）。

此功能修改的是项目源码版。当前机器可双击 `E:\F125mod\启动Mapeditor-比赛参数.cmd` 运行。
之前 tools 目录中的 0.3.0 EXE 不包含这个新面板。

## 可编辑项

- 勾选手动轮胎配方后，为硬胎、中性胎、软胎分别选择 C1–C6，必须按配方编号递增。
  作用于 f1_2025、sprint_f1_2025、f1_2026、sprint_f1_2026 数据集。
- 比赛和排位的单圈 MGU-K 能量回收上限分别勾选并输入，单位 MJ。
  构建时写入 manifest.ers.HarvestLimitMGUK / HarvestLimitQualifyingMGUK，按 1 MJ = 1,000,000 J 换算。
  0 是明确的零上限，取消勾选才表示不覆盖。
- 抓地力区域显示当前限制：尚未找到已验证的赛道抓地力字段，因此暂不提供数值输入，沿用载体参数。

点 OK 后进入项目的撤销/重做历史；取消不修改项目。用 Ctrl+S 保存到项目。
参数存储在 projekt.json 的 race_parameters 中，不修改几何定义。

取消所有覆盖项并点 OK 会移除 race_parameters，恢复自动/载体设置。
构建时，无论是否勾选 Race data from the track，明确设置的手动参数都会生效。
开启自动比赛数据时，手动轮胎配方优先。

## 使用示例

```json
{
  "race_parameters": {
    "tyres": ["C2", "C3", "C4"],
    "ers": {
      "HarvestLimitMGUK": 9000000,
      "HarvestLimitQualifyingMGUK": 7500000
    }
  }
}
```

这是 9 MJ 比赛回收上限和 7.5 MJ 排位回收上限的示例，不会自动写入现有项目。

## 验证范围

已验证项目保存重开、撤销/重做、取消、只读项目、输入检查、菜单入口、构建 CLI 读取，
以及在替换激活模板后保留手动参数。未运行完整赛道构建及游戏内测试。
ERS 字段名来自现有赛道 manifest，数值范围校验仅防止非法输入，不代表赛事规则上限。

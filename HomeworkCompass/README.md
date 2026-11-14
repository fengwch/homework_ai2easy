# HomeworkCompass

老师发的任意格式作业 → 机械校验 → A4 300dpi 目标图。零杜撰、零遗漏、有歧义必拦。

```bash
python3 -m pip install -e ".[dev]"

hw parse --file raw.txt --name 小宇 --offline --out hw.json
hw confirm hw.json
hw render hw.json --out out/
```

- `parse` 把原文拆成结构化作业，任何没出处、没覆盖的片段都进 `pending`；
- `confirm` 逐条过 `pending`（只在 tty 上交互）；
- `render` 出 A4 2480×3508 @300dpi PNG。`pending` 非空时拒绝出图，一个字节都不写。

不传 `--base` 时用占位底图，只用于核对对位，不是可打印成品。

`DASHSCOPE_API_KEY` 只从环境变量读取，配置里没有这个字段。不写 `--offline` 才会调用在线模型。

## 退出码

| 码 | 含义 |
|---|---|
| 0 | 成功 |
| 2 | 存在 pending，拒绝出图 |
| 3 | 解析产生了 pending |
| 4 | 参数或字段白名单错误 |
| 5 | API 或字体错误 |

坐标契约与生图提示词也能单独打印（不花钱）：

```bash
hw zones
hw prompt --skeleton quest-map --skin dinosaur
```

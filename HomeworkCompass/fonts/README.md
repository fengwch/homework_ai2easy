# 中文字体（可选）

把任意**含中文字形**的字体文件放这里（`.ttc` / `.ttf`），部署到没装中文字体的服务器时
就能直接出图，不依赖 `yum install`。

推荐（任选其一）：

| 字体 | 文件 | 说明 |
|------|------|------|
| 文泉驿正黑 | `wqy-zenhei.ttc` | 开源、体积小（约 16MB）、覆盖常用汉字 |
| Noto Sans CJK SC | `NotoSansCJK-Regular.ttc` | 覆盖最全，体积大（约 100MB+） |
| 思源黑体 | `SourceHanSansSC-Regular.otf` | 与 Noto 同源 |

下载示例：

```bash
curl -L -o fonts/wqy-zenhei.ttc \
  https://github.com/magiclen/wqy-zenhei/raw/master/wqy-zenhei.ttc
```

放好之后：

- `tools/run-api.sh` 会自动设置 `HW_FONT=$PWD/fonts/<第一个 ttc/ttf>`
- 也可以用 `HW_FONT=/绝对路径/xxx.ttc` 手动覆盖
- 都不设时，回退到系统字体（`fc-list :lang=zh` 能查到的那些）

> 字体文件体积较大，默认**不进 git**（见仓库根 `.gitignore`）。
> 若非要把某一款纳入版本管理，需要在其 `.gitignore` 里单独放行。

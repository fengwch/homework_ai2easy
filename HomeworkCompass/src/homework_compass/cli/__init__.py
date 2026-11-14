"""CLI 适配层。本包只有两个模块：

- `main`：参数解析、退出码翻译、把结果读给人看；
- `confirm`：唯一的终端交互（`hw confirm`），其余模块一律不碰 stdin。

`__init__` 故意不 re-export 任何名字：`from homework_compass.cli import main`
必须拿到 `main` 模块本身（测试要在它的命名空间里替身 `LlmExtractor`），
一旦这里写 `from ... import main`，拿到的就是函数，替身会静默失效。
"""

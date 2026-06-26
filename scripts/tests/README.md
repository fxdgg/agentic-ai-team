# scripts/tests/ — 工具链单元测试套件

> **受众边界**：本目录仅引擎维护者使用，不部署到业务项目。

## 运行测试

```bash
# 安装 pytest（首次）
pip3.8 install --user pytest

# 跑全套
python3.8 -m pytest scripts/tests -v

# 跑单个文件
python3.8 -m pytest scripts/tests/test_md_parser.py -v

# 失败时打印更详细的 traceback
python3.8 -m pytest scripts/tests -v --tb=long
```

## 退出码协议

- `0` 全部 PASS
- `1` 至少一个测试 FAIL
- `5` 没有收集到测试用例（路径错或 import 失败）

## 测试组织

| 文件 | 覆盖模块 | 用例数下限 |
|------|---------|-----------|
| `test_paths.py` | `lib/paths.py` 路径常量与映射 | 5 |
| `test_md_parser.py` | `lib/md_parser.py` quote-block frontmatter + GFM 表格 | 8 |
| `test_autogen_block.py` | `lib/autogen_block.py` 区段读写 + sha256 + 归一化 | 8 |
| `test_meta_loader.py` | `lib/meta_loader.py` DSL 加载 + 保序 + 缺失兜底 | 5 |
| `test_platform_mirror.py` | `lib/platform_mirror.py` 双平台对账 + 豁免 | 5 |

## 设计原则

1. **隔离**：所有 fixture 用 `tmp_path` 隔离，不污染真实仓库
2. **正反例**：每个核心函数至少含 1 个正例 + 1 个反例 / 边界
3. **不写真实仓库快照**：避免被 `.claude/` 实际改动影响
4. **快速**：全套目标 < 5s

## 已知约定

- `conftest.py` 自动把 `scripts/` 加入 `sys.path`，因此可以直接 `from lib import md_parser`
- Python 版本 < 3.8 自动跳过整个套件（`pytest.skip(allow_module_level=True)`）

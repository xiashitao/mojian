# bazibase DeepSeek 仲裁对接

这是 Layer 3 的集成验证代码——把 bazibase 确定性生成的仲裁 prompt 真正发给 DeepSeek，验证「结构化 prompt + 强制置信度」能否产出可靠的仲裁判断。

## 快速开始

```bash
# 1. 安装 bazibase（如果还没装）
cd /path/to/bazibase && uv pip install -e .

# 2. 设置 API Key
export DEEPSEEK_API_KEY="sk-..."

# 3. dry-run：先看看会生成什么 prompt（不花钱）
python examples/deepseek_runner.py single 1893-12-26 08:00 --lon 112.9 --gender male --dry-run

# 4. 真实调用：单个命例
python examples/deepseek_runner.py single 1893-12-26 08:00 --lon 112.9 --gender male

# 5. 批量跑测试集
python examples/deepseek_runner.py batch examples/sample_charts.json
```

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `DEEPSEEK_API_KEY` | （必填） | DeepSeek API 密钥 |
| `DEEPSEEK_BASE_URL` | `https://api.deepseek.com` | API 地址（可用代理） |
| `DEEPSEEK_MODEL` | `deepseek-chat` | 模型名 |
| `DEEPSEEK_TIMEOUT` | `60` | 请求超时（秒） |

## 命令

### single — 单个命例

```bash
python examples/deepseek_runner.py single <date> <time> --lon <float> --gender <male|female> [options]
```

选项：
- `--tz`：时区，默认 8.0
- `--no-solar`：不做真太阳时修正
- `--threshold`：置信度阈值，默认 0.6
- `--dry-run`：只生成 prompt 不调 LLM
- `--json`：输出 JSON
- `--label`：命例标签

### batch — 批量

```bash
python examples/deepseek_runner.py batch <file.json> [--dry-run] [--json]
```

JSON 格式见 `sample_charts.json`。

## 验证目标

跑完批量后关注这几个指标：

1. **解决率**：多少 case 被 DeepSeek 以 ≥ 阈值置信度解决了？
2. **解析失败率**：DeepSeek 的 JSON 输出是否稳定？`parse_arbitration_response` 经常失败吗？
3. **类别分布**：哪类仲裁 case 最多？哪类最难判（未解决率高）？
4. **推理质量**：随机抽几个 `reasoning` 看看，DeepSeek 的命理推理是否靠谱？引用的规则编号对不对？

这些指标决定了 Layer 3 的设计是否成立，以及下一步该优化什么。

## 设计说明

- **零依赖**：用 stdlib `urllib` 调 API，不引入 `openai` SDK
- **确定性优先**：`temperature=0.0` + `response_format=json_object`
- **自动重试**：JSON 解析失败时带修正提示重试一次
- **审计友好**：每个 response 保留原始返回（`raw_response`）

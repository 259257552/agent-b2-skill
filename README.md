# B2 - Local Agent Skill System

> 基于LLM的多轮对话Agent系统 - B2模块（本地Agent工具执行系统）
> 
> 作者：丁学郅 | 学号：20236486 | 负责模块：B2 Skill执行层
> 团队项目：面向本地工具调用与记忆增强的 Agent 智能体系统
---

## 1. 模块概述

### 1.1 模块名称

`B2 - Local Agent Skill System`（本地Agent工具执行系统）

### 1.2 模块说明

B2模块是整个Agent系统的**工具执行层与安全底线**，向上为B3 Tool Manager提供标准化Skill调用接口，向下封装所有本地工具的具体实现。

**核心价值**：
- 让LLM安全地拥有"手"——执行计算、读取文件、分析表格、运行代码
- 用操作系统原语保障Agent不会失控——RLIMIT硬限制 + 五层沙箱
- 统一接口降低联调成本——8个标准错误码，B3可直接消费决策

**解决的问题**：
- 现有B2模块错误处理粗放（原始异常直接暴露）
- 资源管控缺失（无CPU/内存/文件大小限制）
- Skill能力单一（无复合编排与增强检索）

**主要输入输出**：
- 输入：来自B3的 `{"skill_name": "...", "arguments": {...}, "data_root": "..."}`
- 输出：返回给B3的 `{"status": "success|error", "output": {...}, "error": {"code": "...", "message": "..."}, "latency_ms": ...}`

### 1.3 完成情况概览

| 类型 | 完成情况 |
|---|---|
| 基础要求 | 5个基础Skill（calculator、file_reader、local_file_search、table_analyzer、format_converter）全部实现并通过测试 |
| 进阶要求 | 错误码标准化体系、TF-IDF增强检索、轻量复合Skill编排、五层沙箱代码执行、操作系统级资源硬限制 |
| 可独立运行的演示 | 通过 `python b2_run_skill.py --skill [name] --input [json] --outdir [dir]` 独立运行每个Skill |
| 与团队系统集成情况 | B3通过动态导入调用B2的 `run_skill` 统一入口，JSON格式交互，错误码驱动决策 |

---

## 2. 环境、模型与数据依赖

### 2.1 运行环境

| 项目 | 要求 |
|---|---|
| Python 版本 | >= 3.10 |
| 必要依赖 | Python标准库（ast、math、csv、json、re、subprocess、resource等） |
| 是否需要模型 | 不需要 |
| 是否需要 GPU | 不需要 |
| 是否需要外部数据集 | 不需要（使用本地测试数据） |

### 2.2 模型依赖

无模型依赖。B2定位为"无模型依赖的纯本地执行层"，确保工具调用的确定性和安全性。

### 2.3 数据集或样例数据依赖

| 数据或文件 | 来源 | 项目内相对路径 | 用途 |
|---|---|---|---|
| docs/agent_intro.txt | 项目自带 | `data/docs/` | file_reader测试 |
| tables/results.csv | 项目自带 | `data/tables/` | table_analyzer测试 |
| tool_input_*.json | 运行时生成 | `data/tool_inputs/` | 各Skill输入参数 |

### 2.4 安装步骤

```bash
# 克隆仓库
git clone https://github.com/259257552/agent-b2-skill
cd agent-b2-skill

# 创建虚拟环境（可选）
python3 -m venv venv
source venv/bin/activate

# 无需安装额外依赖，纯Python标准库
# 验证导入
python -c "import sys; sys.path.insert(0, 'code'); from b2_run_skill import run_skill; print('Import OK')"
```

---

## 3. 文件结构与接口边界

### 3.1 文件结构

```
.
├── README.md                          # 本文件
├── requirements.txt                   # Python依赖（空，标准库即可）
├── code/
│   └── b2_run_skill.py               # 统一入口：错误码映射 + 复合Skill支持 + 性能计时
├── skills/                           # Skill实现目录
│   ├── __init__.py                   # 资源限制配置 + 路径解析 + 复合Skill导出
│   ├── calculator.py                 # 数学表达式计算（AST安全求值）
│   ├── file_reader.py                # 本地文件读取（txt/md，带大小限制）
│   ├── local_file_search.py          # 本地文件检索（TF-IDF加权）
│   ├── table_analyzer.py             # CSV/TSV表格分析（带行数限制）
│   ├── format_converter.py           # 文本格式转换（markdown/json，带输出限制）
│   ├── composite_skills.py           # 复合Skill编排（read_and_convert, analyze_and_convert）
│   └── code_executor.py              # 沙箱代码执行（五层安全防护）
├── data/                             # 测试数据
│   ├── docs/                         # txt/md文档
│   ├── tables/                       # csv/tsv表格
│   └── tool_inputs/                  # 工具输入JSON
├── outputs/                          # 测试结果输出
│   └── B2_skills/
└── images/                           # 演示截图
    ├── B2_basic_skills.png
    ├── sandbox_block.png
    └── composite_skill.png
```

### 3.2 接口边界

| 类型 | 来源 / 去向 | 数据格式 | 说明 |
|---|---|---|---|
| 输入 | B3 Tool Manager | JSON | `{"skill_name": "calculator", "arguments": {"expression": "1+1"}, "data_root": "/path/to/data"}` |
| 输出 | 返回B3 Tool Manager | JSON | `{"status": "success", "output": {"result": 2}, "error": null, "latency_ms": 1.19}` |
| 错误输出 | 返回B3 Tool Manager | JSON | `{"status": "error", "output": null, "error": {"code": "PARAM_INVALID", "message": "..."}, "latency_ms": 0.5}` |

---

## 4. 基础要求实现与演示

### 4.1 基础功能说明

基础版本实现了5个核心Skill，覆盖数学计算、文件读取、本地搜索、表格分析、格式转换五大类本地工具需求。

### 4.2 基础功能实现路径

| 文件 / 函数 | 作用 |
|---|---|
| `skills/calculator.py` | AST安全求值，支持+ - * / // % **运算 |
| `skills/file_reader.py` | 读取txt/md文件，支持max_chars截断 |
| `skills/local_file_search.py` | 基于TF-IDF的本地文件检索 |
| `skills/table_analyzer.py` | CSV/TSV表格统计分析与预览 |
| `skills/format_converter.py` | 文本转markdown或json格式 |
| `code/b2_run_skill.py` | 统一入口，动态导入Skill，错误码映射 |

**关键流程**：
```
输入JSON -> b2_run_skill.py解析 -> 动态导入Skill模块 -> 执行业务函数 -> 捕获异常 -> 映射错误码 -> 返回统一JSON
```

**关键代码片段**（AST安全求值）：

```python
# skills/calculator.py
def _evaluate(node: ast.AST) -> int | float:
    if isinstance(node, ast.Expression):
        return _evaluate(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
        left = _evaluate(node.left)
        right = _evaluate(node.right)
        # 指数限制
        if isinstance(node.op, ast.Pow) and abs(right) > MAX_EXPONENT:
            raise ValueError(f"exponent too large")
        return _BINARY_OPERATORS[type(node.op)](left, right)
    raise ValueError(f"unsupported: {type(node).__name__}")
```

### 4.3 基础功能输入格式与样例

| 字段 / 输入文件 | 类型 / 格式 | 是否必需 | 说明 |
|---|---|---|---|
| `skill_name` | string | 是 | 要执行的Skill名称 |
| `arguments` | dict | 是 | Skill参数字典 |
| `data_root` | string | 否 | 数据根目录路径 |

样例输入：

| 样例文件 | 用途 |
|---|---|
| `data/tool_inputs/tool_input_calculator.json` | 验证calculator正常计算 |
| `data/tool_inputs/tool_input_file_reader.json` | 验证file_reader文件读取 |
| `data/tool_inputs/tool_input_file_search.json` | 验证local_file_search检索 |

### 4.4 基础功能演示命令

```bash
cd code

# 1. calculator - 数学计算
echo '{"expression": "1 + 2 * 3"}' > ../data/tool_inputs/demo_calc.json
python b2_run_skill.py --skill calculator --input ../data/tool_inputs/demo_calc.json --outdir ../outputs/B2_skills
cat ../outputs/B2_skills/calculator_result.json

# 2. file_reader - 文件读取
echo '{"path": "docs/agent_intro.txt", "max_chars": 500}' > ../data/tool_inputs/demo_reader.json
python b2_run_skill.py --skill file_reader --input ../data/tool_inputs/demo_reader.json --outdir ../outputs/B2_skills
cat ../outputs/B2_skills/file_reader_result.json

# 3. local_file_search - TF-IDF检索
echo '{"query": "Agent 工具调用", "root_dir": "docs", "top_k": 3}' > ../data/tool_inputs/demo_search.json
python b2_run_skill.py --skill local_file_search --input ../data/tool_inputs/demo_search.json --outdir ../outputs/B2_skills
cat ../outputs/B2_skills/local_file_search_result.json

# 4. table_analyzer - 表格分析
echo '{"path": "tables/results.csv", "max_rows_preview": 5}' > ../data/tool_inputs/demo_table.json
python b2_run_skill.py --skill table_analyzer --input ../data/tool_inputs/demo_table.json --outdir ../outputs/B2_skills
cat ../outputs/B2_skills/table_analyzer_result.json

# 5. format_converter - 格式转换
echo '{"text": "name: Alice\nage: 25", "target_format": "json"}' > ../data/tool_inputs/demo_convert.json
python b2_run_skill.py --skill format_converter --input ../data/tool_inputs/demo_convert.json --outdir ../outputs/B2_skills
cat ../outputs/B2_skills/format_converter_result.json
```

**观察点**：
- 每个命令返回 `status: success`
- `output` 包含业务结果
- `latency_ms` 显示执行耗时（毫秒）
- 错误时返回 `status: error` 和 `error.code`

### 4.5 基础功能输出格式

| 输出文件 / 返回字段 | 格式 | 说明 |
|---|---|---|
| `*_result.json` | JSON | 统一返回格式：`{status, output, error, latency_ms}` |
| `output.result` | float/int | calculator计算结果 |
| `output.content` | string | file_reader读取内容 |
| `output.results` | list | local_file_search检索结果列表 |

### 4.6 基础功能结果截图

![基础功能演示](images/B2_basic_skills.png)

*5个基础Skill全部正常运行，返回status: success和对应业务结果*

---

## 5. 进阶要求实现与演示

### 5.1 选择的进阶要求

| 进阶要求 | 是否完成 | 对应文件 / 函数 | 简要说明 |
|---|---|---|---|
| 错误码标准化体系 | 是 | `code/b2_run_skill.py` 中 `_EXCEPTION_TO_CODE` | 8个统一错误码，Python异常自动映射 |
| TF-IDF增强检索 | 是 | `skills/local_file_search.py` | 替代简单词频，文档长度归一化+文件名加权 |
| 轻量复合Skill编排 | 是 | `skills/composite_skills.py` | read_and_convert、analyze_and_convert，LLM调用从3轮降至1轮 |
| 操作系统级资源硬限制 | 是 | `skills/__init__.py` 中 `ResourceLimits` + 各Skill内联常量 | RLIMIT硬限制：CPU/内存/文件/超时 |
| 五层沙箱代码执行 | 是 | `skills/code_executor.py` | AST→白名单→隔离→RLIMIT→清理 |

### 5.2 进阶功能1：错误码标准化体系

#### 功能说明

将Python原始异常映射为8个统一错误码，B3可直接根据错误码做决策，无需理解底层异常类型。

#### 实现路径

| 文件 / 函数 | 作用 |
|---|---|
| `code/b2_run_skill.py` 中 `_EXCEPTION_TO_CODE` | 异常→错误码映射表 |
| `code/b2_run_skill.py` 中 `run_skill()` | 统一捕获异常，返回结构化错误 |

**关键代码**：

```python
_EXCEPTION_TO_CODE = {
    ValueError: ErrorCode.PARAM_INVALID,
    TypeError: ErrorCode.PARAM_INVALID,
    FileNotFoundError: ErrorCode.FILE_NOT_FOUND,
    PermissionError: ErrorCode.PERMISSION_DENIED,
    ZeroDivisionError: ErrorCode.EXECUTION_ERROR,
    RecursionError: ErrorCode.EXECUTION_ERROR,
    RuntimeError: ErrorCode.EXECUTION_ERROR,
    TimeoutError: ErrorCode.TIMEOUT,
}
```

#### 演示命令

```bash
# 除零错误 -> EXECUTION_ERROR
echo '{"expression": "1 / 0"}' > ../data/tool_inputs/test_div0.json
python b2_run_skill.py --skill calculator --input ../data/tool_inputs/test_div0.json --outdir ../outputs/B2_skills
cat ../outputs/B2_skills/calculator_result.json

# 文件不存在 -> FILE_NOT_FOUND
echo '{"path": "not_exist.txt", "max_chars": 100}' > ../data/tool_inputs/test_notfound.json
python b2_run_skill.py --skill file_reader --input ../data/tool_inputs/test_notfound.json --outdir ../outputs/B2_skills
cat ../outputs/B2_skills/file_reader_result.json
```

#### 输出格式

```json
{
  "status": "error",
  "output": null,
  "error": {
    "code": "EXECUTION_ERROR",
    "message": "division by zero"
  },
  "latency_ms": 0.5
}
```

### 5.3 进阶功能2：TF-IDF增强检索

#### 功能说明

替代简单词频统计，引入文档长度归一化和文件名匹配加权，提升检索精准度。

#### 实现路径

| 文件 / 函数 | 作用 |
|---|---|
| `skills/local_file_search.py` 中搜索循环 | 计算TF-IDF分数并排序 |

**核心公式**：
```
score = sum [count(t,d) / |d|] * log(N / df(t)) * filename_bonus
```

#### 演示命令

```bash
echo '{"query": "Agent 工具调用", "root_dir": "docs", "top_k": 3}' > ../data/tool_inputs/test_tfidf.json
python b2_run_skill.py --skill local_file_search --input ../data/tool_inputs/test_tfidf.json --outdir ../outputs/B2_skills
cat ../outputs/B2_skills/local_file_search_result.json
```

### 5.4 进阶功能3：轻量复合Skill编排

#### 功能说明

在B2内部完成多步编排，减少LLM调用轮次。

#### 实现路径

| 文件 / 函数 | 作用 |
|---|---|
| `skills/composite_skills.py` 中 `read_and_convert()` | 读取文件→转换格式 |
| `skills/composite_skills.py` 中 `analyze_and_convert()` | 分析表格→生成报告 |

#### 演示命令

```bash
# read_and_convert: 读取+转换一步完成
echo '{"path": "docs/agent_intro.txt", "target_format": "markdown"}' > ../data/tool_inputs/test_composite.json
python b2_run_skill.py --skill read_and_convert --input ../data/tool_inputs/test_composite.json --outdir ../outputs/B2_skills
cat ../outputs/B2_skills/read_and_convert_result.json
```

**输出**：
```json
{
  "status": "success",
  "steps": ["file_reader", "format_converter"],
  "final_output": "...",
  "latency_ms": 1.19
}
```

### 5.5 进阶功能4：五层沙箱代码执行

#### 功能说明

在受限沙箱中执行用户提供的Python代码，五层纵深防御确保系统安全。

#### 实现路径

| 层级 | 机制 | 代码位置 |
|---|---|---|
| Layer 1 | AST静态检查 | `code_executor.py` 中 `_check_code_safety()` |
| Layer 2 | 模块白名单 | `code_executor.py` 中 `_ALLOWED_MODULES` |
| Layer 3 | 进程隔离 | `code_executor.py` 中 `subprocess.run()` |
| Layer 4 | RLIMIT内核限制 | `code_executor.py` 中 `_set_resource_limits()` |
| Layer 5 | 超时清理 | `code_executor.py` 中 `finally: os.unlink()` |

#### 演示命令

```bash
# 攻击1: import os -> 被AST拦截（Layer 1）
echo '{"code": "import os\nos.system(\"ls\")"}' > ../data/tool_inputs/test_danger.json
python b2_run_skill.py --skill code_executor --input ../data/tool_inputs/test_danger.json --outdir ../outputs/B2_skills
cat ../outputs/B2_skills/code_executor_result.json

# 攻击2: while True: pass -> 10秒被RLIMIT终止（Layer 4）
echo '{"code": "while True: pass"}' > ../data/tool_inputs/test_infinite.json
python b2_run_skill.py --skill code_executor --input ../data/tool_inputs/test_infinite.json --outdir ../outputs/B2_skills
cat ../outputs/B2_skills/code_executor_result.json
```

#### 输出

```json
// import os 被拦截
{
  "status": "error",
  "error": {
    "code": "PARAM_INVALID",
    "message": "import of 'os' is not allowed"
  }
}

// while True 被终止
{
  "status": "error",
  "error": {
    "code": "EXECUTION_ERROR",
    "message": "code execution terminated: timeout or resource limit exceeded"
  }
}
```

### 5.6 进阶功能结果截图

![沙箱拦截演示](images/sandbox_block.png)

*左：import os被AST静态检查拦截（Layer 1）；右：while True: pass被RLIMIT强制终止（Layer 4）*

![复合Skill演示](images/composite_skill.png)

*read_and_convert单次调用完成读取+转换，steps字段透明展示内部执行过程*

---

## 6. 与团队系统的集成说明

### 6.1 调用关系

```
用户提问
    ↓
B1 (Agent Loop) → 判断需要工具
    ↓
B4 (LLM Interface) → 生成 Tool Call
    ↓
B3 (Tool Manager) → 解析并调度
    ↓
B2 (本模块) → 执行 Skill
    ↓
B3 ← 返回结果
    ↓
B1 ← 拼接上下文
    ↓
B4 ← 生成最终回复
```

### 6.2 接口详情

**B3 调用 B2**：
```python
from b2_run_skill import run_skill

result = run_skill(
    skill_name="calculator",
    arguments={"expression": "1 + 1"},
    data_root="/path/to/data"
)
```

**B2 返回 B3**：
```json
{
  "status": "success",
  "output": {"result": 2},
  "error": null,
  "latency_ms": 1.19
}
```

### 6.3 联调问题与解决

| 问题 | 原因 | 解决方案 |
|---|---|---|
| JSON字段不一致 | B3期望字符串错误码，B2返回异常类名 | 设计 `_EXCEPTION_TO_CODE` 映射表，统一为8个标准错误码 |
| 模块缓存不刷新 | Python `sys.modules` 缓存导致配置修改不生效 | 采用内联常量方案，各Skill独立定义资源限制 |
| 路径安全问题 | B2可能访问系统任意文件 | `resolve_data_path()` 函数限制在 `data_root` 目录内 |

---

## 7. 已知问题与后续改进

| 问题 | 当前原因 | 后续改进 |
|---|---|---|
| 沙箱AST检查可能绕过 | `getattr(__builtins__, '__import__')` 等动态绕过未完全覆盖 | 引入更严格的RestrictedPython或seccomp机制 |
| 资源限制值为硬编码 | 内联常量方案牺牲灵活性 | 改为从环境变量读取，兼顾安全与配置性 |
| TF-IDF仅支持英文分词 | 当前按空格分词，中文支持不足 | 引入jieba等中文分词库 |
| 复合Skill仅覆盖两个场景 | 项目时间有限，高频优先 | 扩展更多复合模式，如搜索→读取→分析→报告 |

---

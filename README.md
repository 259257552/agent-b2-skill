# B2 - Local Agent Skill System

> 基于LLM的多轮对话Agent系统 - B2模块（本地Agent工具执行系统）
> 负责模块：B2 Skill执行层

---

## 一、模块定位

B2模块是整个Agent系统的**工具执行层与安全底线**，向上为B3 Tool Manager提供标准化Skill调用接口，向下封装所有本地工具的具体实现。

**核心价值**：
- 让LLM安全地拥有"手"——执行计算、读取文件、分析表格、运行代码
- 用操作系统原语保障Agent不会失控——RLIMIT硬限制 + 五层沙箱
- 统一接口降低联调成本——8个标准错误码，B3可直接消费决策

---

## 二、项目结构

```
agent-b2-skill/
├── .gitignore
├── README.md
├── requirements.txt
├── B2_Final_Report_v2.md
├── images/
│   ├── B2_basic_skills.png
│   ├── sandbox_block.png
│   └── composite_skill.png
├── code/
│   └── b2_run_skill.py
└── skills/
    ├── __init__.py
    ├── calculator.py
    ├── file_reader.py
    ├── local_file_search.py
    ├── table_analyzer.py
    ├── format_converter.py
    ├── composite_skills.py
    └── code_executor.py
```

---

## 三、快速开始

### 3.1 环境要求

- Python >= 3.10
- Ubuntu 22.04 LTS
- 内存 >= 4GB

### 3.2 安装依赖

```bash
# 克隆仓库
git clone https://github.com/259257552/agent-b2-skill-system.git
cd agent-b2-skill-system

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 3.3 运行单个Skill

```bash
cd code

# 1. calculator - 数学计算
echo '{"expression": "1 + 2 * 3"}' > ../data/tool_inputs/tool_input_calculator.json
python b2_run_skill.py --skill calculator   --input ../data/tool_inputs/tool_input_calculator.json   --outdir ../outputs/B2_skills
cat ../outputs/B2_skills/calculator_result.json

# 2. file_reader - 文件读取
echo '{"path": "docs/agent_intro.txt", "max_chars": 500}' > ../data/tool_inputs/tool_input_file_reader.json
python b2_run_skill.py --skill file_reader   --input ../data/tool_inputs/tool_input_file_reader.json   --outdir ../outputs/B2_skills

# 3. local_file_search - TF-IDF检索
echo '{"query": "Agent 工具调用", "root_dir": "docs", "top_k": 3}' > ../data/tool_inputs/tool_input_file_search.json
python b2_run_skill.py --skill local_file_search   --input ../data/tool_inputs/tool_input_file_search.json   --outdir ../outputs/B2_skills

# 4. table_analyzer - 表格分析
echo '{"path": "tables/results.csv", "max_rows_preview": 5}' > ../data/tool_inputs/tool_input_table_analyzer.json
python b2_run_skill.py --skill table_analyzer   --input ../data/tool_inputs/tool_input_table_analyzer.json   --outdir ../outputs/B2_skills

# 5. format_converter - 格式转换
echo '{"text": "name: Alice\nage: 25", "target_format": "json"}' > ../data/tool_inputs/tool_input_format_converter.json
python b2_run_skill.py --skill format_converter   --input ../data/tool_inputs/tool_input_format_converter.json   --outdir ../outputs/B2_skills
```

### 3.4 运行复合Skill

```bash
# read_and_convert: 读取文件 -> 转换格式
echo '{"path": "docs/agent_intro.txt", "target_format": "markdown"}' > ../data/tool_inputs/test_composite.json
python b2_run_skill.py --skill read_and_convert   --input ../data/tool_inputs/test_composite.json   --outdir ../outputs/B2_skills

# analyze_and_convert: 分析表格 -> 生成报告
echo '{"path": "tables/results.csv", "target_format": "markdown"}' > ../data/tool_inputs/test_analyze_convert.json
python b2_run_skill.py --skill analyze_and_convert   --input ../data/tool_inputs/test_analyze_convert.json   --outdir ../outputs/B2_skills
```

### 3.5 运行沙箱代码执行

```bash
# 正常代码执行
echo '{"code": "import math\nprint(math.sqrt(16))"}' > ../data/tool_inputs/test_code.json
python b2_run_skill.py --skill code_executor   --input ../data/tool_inputs/test_code.json   --outdir ../outputs/B2_skills

# 危险代码被拦截（import os）
echo '{"code": "import os\nos.system(\'ls\')"}' > ../data/tool_inputs/test_danger.json
python b2_run_skill.py --skill code_executor   --input ../data/tool_inputs/test_danger.json   --outdir ../outputs/B2_skills

# 无限循环被强制终止
echo '{"code": "while True: pass"}' > ../data/tool_inputs/test_infinite.json
python b2_run_skill.py --skill code_executor   --input ../data/tool_inputs/test_infinite.json   --outdir ../outputs/B2_skills
```

---

## 四、API接口文档

### 4.1 统一返回格式

所有Skill返回统一的JSON结构：

```json
{
  "status": "success",
  "output": {
    // Skill-specific output
  },
  "error": null,
  "latency_ms": 1.19
}
```

错误时：

```json
{
  "status": "error",
  "output": null,
  "error": {
    "code": "PARAM_INVALID",
    "message": "expression must be a non-empty string"
  },
  "latency_ms": 0.5
}
```

### 4.2 错误码规范

| 错误码 | 含义 | B3决策策略 |
| :--- | :--- | :--- |
| `SUCCESS` | 执行成功 | 返回结果给LLM |
| `PARAM_INVALID` | 参数格式错误或非法 | 直接拒绝，不调用LLM |
| `PARAM_MISSING` | 缺少必要参数 | 要求LLM补充参数 |
| `PARAM_OUT_OF_RANGE` | 参数超出允许范围 | 提示LLM调整参数 |
| `FILE_NOT_FOUND` | 文件不存在 | 触发local_file_search搜索替代 |
| `FILE_TOO_LARGE` | 文件超过大小限制 | 提示用户文件过大 |
| `PERMISSION_DENIED` | 权限不足 | 记录日志，返回LLM |
| `EXECUTION_ERROR` | 执行过程中出错 | 记录日志，返回LLM要求修正 |
| `TIMEOUT` | 执行超时 | 触发重试机制 |
| `UNKNOWN_ERROR` | 未知错误 | 记录日志，人工介入 |

### 4.3 Skill列表

| Skill名称 | 功能 | 输入参数 | 输出字段 |
| :--- | :--- | :--- | :--- |
| `calculator` | 数学表达式计算 | `expression: str` | `result: float/int` |
| `file_reader` | 读取txt/md文件 | `path: str, max_chars: int` | `content: str, num_chars: int, truncated: bool` |
| `local_file_search` | TF-IDF文件检索 | `query: str, root_dir: str, top_k: int` | `results: list[{path, score, snippet}]` |
| `table_analyzer` | CSV/TSV分析 | `path: str, max_rows_preview: int, describe: bool` | `num_rows, num_columns, columns, preview, describe` |
| `format_converter` | 格式转换 | `text: str, target_format: str` | `formatted_text: str, generated_file_path: str` |
| `read_and_convert` | 复合：读取+转换 | `path: str, target_format: str` | `final_output: str, step_results: dict` |
| `analyze_and_convert` | 复合：分析+报告 | `path: str, target_format: str` | `final_output: str, generated_file_path: str` |
| `code_executor` | 沙箱代码执行 | `code: str, timeout: int` | `returncode, stdout, stderr` |

---

## 五、核心设计

### 5.1 五层沙箱安全架构

```
┌─────────────────────────────────────────┐
│  Layer 1: AST静态检查                      │  零开销，执行前拦截
│  - 禁止非白名单import                      │  测试: import os -> PARAM_INVALID
│  - 禁止危险函数(eval/exec/open)            │
├─────────────────────────────────────────┤
│  Layer 2: 模块白名单                       │  运行时二次校验
│  - 仅允许math/json/re/datetime等15个模块   │
├─────────────────────────────────────────┤
│  Layer 3: 进程隔离                         │  崩溃不影响主系统
│  - subprocess.Popen独立进程               │
├─────────────────────────────────────────┤
│  Layer 4: RLIMIT内核限制                   │  操作系统强制执行
│  - CPU<=10s / 内存<=128MB                 │  测试: while True -> 10秒SIGKILL
│  - 文件<=1MB / 禁止子进程                 │
├─────────────────────────────────────────┤
│  Layer 5: 超时清理                         │  应用层兜底
│  - subprocess.communicate(timeout=10)     │
│  - finally: 清理临时文件                   │
└─────────────────────────────────────────┘
```

### 5.2 资源限制配置

| 限制项 | 阈值 | 作用Skill |
| :--- | :--- | :--- |
| 表达式长度 | <=500字符 | calculator |
| 指数大小 | <=20 | calculator |
| 文件大小 | <=10MB | file_reader, local_file_search |
| 单次读取 | <=10000字符 | file_reader |
| 搜索文件数 | <=1000个 | local_file_search |
| 搜索超时 | <=30秒 | local_file_search |
| 表格行数 | <=100000行 | table_analyzer |
| 表格文件 | <=50MB | table_analyzer |
| 输出大小 | <=10MB | format_converter |
| 代码执行时间 | <=10秒 | code_executor |
| 代码内存 | <=128MB | code_executor |

### 5.3 TF-IDF检索算法

```
score(d, q) = sum_{t in q} [ tf(t,d) * idf(t) * filename_bonus(t,d) ]

where:
  tf(t,d)    = count(t,d) / |d|          (词频，文档长度归一化)
  idf(t)     = log( N / df(t) )          (逆文档频率)
  filename_bonus = 1.5 if t in filename else 1.0
  N          = 总文档数
  df(t)      = 包含词t的文档数
```

---

## 六、测试

### 6.1 运行全部测试

```bash
cd tests

# 基础Skill测试
python test_basic_skills.py

# 复合Skill测试
python test_composite_skills.py

# 沙箱安全测试
python test_sandbox.py

# 资源限制测试
python test_resource_limits.py
```

### 6.2 测试结果概览

| 测试类别 | 测试数 | 通过数 | 状态 |
| :--- | :--- | :--- | :--- |
| 基础Skill正常输入 | 5 | 5 | 通过 |
| 基础Skill异常输入 | 5 | 5 | 通过 |
| 复合Skill | 2 | 2 | 通过 |
| 沙箱安全 | 4 | 4 | 通过 |
| 资源限制 | 6 | 6 | 通过 |
| B3联调 | 4 | 4 | 通过 |
| **总计** | **26** | **26** | **全部通过** |

---

## 七、进阶功能清单

- [x] **错误码标准化**：8个统一错误码，Python异常自动映射
- [x] **TF-IDF增强检索**：替代简单词频，文档长度归一化 + 文件名加权
- [x] **轻量复合Skill**：read_and_convert / analyze_and_convert，LLM调用从3轮降至1轮
- [x] **操作系统级资源限制**：Linux RLIMIT硬限制（CPU/内存/文件/进程）
- [x] **五层沙箱代码执行**：AST→白名单→隔离→RLIMIT→清理
- [x] **B3联调验证**：8个Skill全部可动态导入，错误码决策正确

---

## 八、与其他模块的连接

```
B1 (Agent Loop)  <--JSON-->  B4 (LLM Interface)
       |                              |
       |  Tool Call Request           |  Parsed Tool Call
       v                              v
B3 (Tool Manager)  <--JSON-->  B2 (本模块)
       |                              |
       |  Skill Invocation            |  Execution Result
       |  {skill_name, arguments}     |  {status, output, error, latency_ms}
       v                              v
       +------------------------------+
       |       B5 (Memory Store)       |
       +------------------------------+
```

**B2接收**：来自B3的 `{"skill_name": "...", "arguments": {...}, "data_root": "..."}`

**B2返回**：`{"status": "success|error", "output": {...}, "error": {"code": "...", "message": "..."}, "latency_ms": ...}`

---

## 九、许可证

MIT License

---

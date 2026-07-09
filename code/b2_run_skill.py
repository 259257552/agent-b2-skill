from __future__ import annotations

import argparse
import importlib
import inspect
import sys
from pathlib import Path
from time import perf_counter

from common.io_utils import append_jsonl, read_json, write_json
from common.logging_utils import now_iso
from common.path_utils import DEFAULT_DATA_ROOT, bootstrap_project_root, resolve_cli_path
from common.schemas import make_skill_result


bootstrap_project_root()


# ========== 错误码映射（内联定义，避免模块导入问题）==========
class ErrorCode:
    """B2 统一错误码，供 B3 决策使用"""

    # 参数相关
    PARAM_MISSING = "PARAM_MISSING"
    PARAM_INVALID = "PARAM_INVALID"
    PARAM_OUT_OF_RANGE = "PARAM_OUT_OF_RANGE"

    # 文件相关
    FILE_NOT_FOUND = "FILE_NOT_FOUND"
    FILE_TOO_LARGE = "FILE_TOO_LARGE"
    PERMISSION_DENIED = "PERMISSION_DENIED"

    # 执行相关
    TIMEOUT = "TIMEOUT"
    RESOURCE_EXHAUSTED = "RESOURCE_EXHAUSTED"
    EXECUTION_ERROR = "EXECUTION_ERROR"

    # 复合Skill相关
    COMPOSITE_STEP_FAILED = "COMPOSITE_STEP_FAILED"

    # 其他
    UNSUPPORTED_OPERATION = "UNSUPPORTED_OPERATION"
    UNKNOWN_ERROR = "UNKNOWN_ERROR"


_EXCEPTION_TO_CODE = {
    # 参数错误
    ValueError: ErrorCode.PARAM_INVALID,
    TypeError: ErrorCode.PARAM_INVALID,
    KeyError: ErrorCode.PARAM_MISSING,
    IndexError: ErrorCode.PARAM_OUT_OF_RANGE,

    # 文件错误
    FileNotFoundError: ErrorCode.FILE_NOT_FOUND,
    PermissionError: ErrorCode.PERMISSION_DENIED,
    IsADirectoryError: ErrorCode.FILE_NOT_FOUND,

    # 执行错误
    ZeroDivisionError: ErrorCode.EXECUTION_ERROR,
    OverflowError: ErrorCode.EXECUTION_ERROR,
    RecursionError: ErrorCode.EXECUTION_ERROR,

    # 复合Skill错误
    ImportError: ErrorCode.COMPOSITE_STEP_FAILED,
    ModuleNotFoundError: ErrorCode.COMPOSITE_STEP_FAILED,

    # 超时
    TimeoutError: ErrorCode.TIMEOUT,  

     RuntimeError: ErrorCode.EXECUTION_ERROR,
}


def map_exception_to_code(exc: Exception) -> tuple[str, str]:
    """将异常映射为统一错误码和可读消息。"""
    exc_type = type(exc)
    code = _EXCEPTION_TO_CODE.get(exc_type, ErrorCode.UNKNOWN_ERROR)
    message = str(exc) if str(exc) else f"{exc_type.__name__}: {exc}"
    return code, message
# ============================================================


# 基础Skill模块映射
SKILL_MODULES = {
    "calculator": "skills.calculator",
    "file_reader": "skills.file_reader",
    "local_file_search": "skills.local_file_search",
    "table_analyzer": "skills.table_analyzer",
    "format_converter": "skills.format_converter",
    # 复合Skill
    "read_and_convert": "skills.composite_skills",
    "analyze_and_convert": "skills.composite_skills",


     "code_executor": "skills.code_executor",
}


def run_skill(skill_name: str, input_data: dict, data_root: str | None = None, output_dir: str | None = None) -> dict:
    if skill_name not in SKILL_MODULES:
        raise ValueError(f"unknown skill: {skill_name}")
    if not isinstance(input_data, dict):
        raise ValueError("skill input must be a JSON object")
    module = importlib.import_module(SKILL_MODULES[skill_name])
    function = getattr(module, skill_name)
    kwargs = dict(input_data)
    signature = inspect.signature(function)
    if "data_root" in signature.parameters:
        kwargs["data_root"] = data_root or str(DEFAULT_DATA_ROOT)
    if "output_dir" in signature.parameters:
        kwargs["output_dir"] = output_dir
    start = perf_counter()
    try:
        output = function(**kwargs)
        status = "success"
        error = None
    except Exception as exc:
        output = None
        status = "error"
        error_code, error_message = map_exception_to_code(exc)
        error = {"code": error_code, "message": error_message}
    latency_ms = round((perf_counter() - start) * 1000, 3)
    return make_skill_result(skill_name, status, input_data, output, error, latency_ms)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one local Agent skill.")
    parser.add_argument("--skill", required=True, choices=sorted(SKILL_MODULES))
    parser.add_argument("--input", required=True)
    parser.add_argument("--outdir", required=True)
    parser.add_argument("--data_root", default=None)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        input_path = resolve_cli_path(args.input)
        outdir = resolve_cli_path(args.outdir)
        input_data = read_json(input_path)
        data_root = str(resolve_cli_path(args.data_root)) if args.data_root else None
        outdir.mkdir(parents=True, exist_ok=True)
        result = run_skill(args.skill, input_data, data_root, str(outdir))
        result_path = outdir / f"{args.skill}_result.json"
        write_json(result, result_path)
        append_jsonl(
            {
                "timestamp": now_iso(),
                "skill_name": args.skill,
                "status": result["status"],
                "result_path": str(result_path),
                "latency_ms": result["latency_ms"],
            },
            outdir / "skill_run_log.jsonl",
        )
        print(result_path)
        return 0
    except Exception as exc:
        print(f"fatal: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

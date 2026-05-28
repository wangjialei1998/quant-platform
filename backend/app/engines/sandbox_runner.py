import ast
from pathlib import Path


class SandboxRunner:
    def validate_strategy_file(self, code_path: str) -> tuple[bool, str]:
        path = Path(code_path)
        try:
            source = path.read_text(encoding="utf-8")
            ast.parse(source)
        except Exception as exc:
            return False, str(exc)
        if "backtrader" not in source and "bt.Strategy" not in source and "Strategy" not in source:
            return False, "策略文件需要包含 Backtrader Strategy 类"
        return True, "策略语法检查通过，沙箱执行接口已预留"


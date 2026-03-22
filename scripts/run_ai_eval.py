#!/usr/bin/env python3
from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CASES_PATH = ROOT / "docs" / "ai_eval_cases.json"


def main() -> int:
    cases = json.loads(CASES_PATH.read_text(encoding="utf-8"))

    print("# AIFriends AI Eval Checklist\n")
    print("这是一份轻量评估清单，用于人工审阅角色一致性、记忆命中、语音一致性和 fallback 暴露。")
    print("建议在每次修改 prompt、记忆或 runtime 逻辑后跑一轮。\n")

    for case in cases:
        print(f"## [{case['category']}] {case['title']}")
        print(f"- Case ID: `{case['id']}`")
        print(f"- User Message: {case['user_message']}")
        print("- Checks:")
        for check in case["expected_checks"]:
            print(f"  - [ ] {check}")
        print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

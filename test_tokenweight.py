"""tokenweight —— 自检测试。

估算提示词各部分的令牌占比与影响权重

覆盖：正常路径、边界输入、防呆红线、幂等性。
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import tokenweight  # noqa: E402

SAMPLE_TEXT = '# 标题一\n一些内容在这里。\n\n# 标题二\n更多的内容在这里。'


class TestTokenweight(unittest.TestCase):
    """令牌权重估算"""

    def test_cli_help_exits_zero(self):
        """--help 必须能正常退出。"""
        import subprocess
        proc = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "tokenweight.py"), "--help"],
            capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(proc.returncode, 0)

    def test_cli_rejects_empty_input(self):
        """空输入必须明确报错，不能静默成功。"""
        import subprocess
        proc = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "tokenweight.py"), "--text", "   "],
            capture_output=True, text=True, encoding="utf-8")
        self.assertNotEqual(proc.returncode, 0)

    def test_cli_json_output_parses(self):
        """--json 输出必须是合法 JSON。"""
        import subprocess
        proc = subprocess.run(
            [sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                         "tokenweight.py"), "--text", SAMPLE_TEXT,
             "--json"],
            capture_output=True, text=True, encoding="utf-8")
        if proc.returncode not in (0, 1):
            self.fail(f"退出码异常：{proc.returncode} {proc.stderr[:300]}")
        data = json.loads(proc.stdout)
        self.assertIsInstance(data, dict)

    def test_does_not_mutate_input(self):
        """防呆：分析过程不得改动调用方传入的对象。"""
        payload = SAMPLE_TEXT
        before = payload
        tokenweight.tokenweight_analyze(payload)
        self.assertEqual(before, payload)

    def test_is_idempotent(self):
        """同一输入跑两次结果必须一致。"""
        a = tokenweight.tokenweight_analyze(SAMPLE_TEXT)
        b = tokenweight.tokenweight_analyze(SAMPLE_TEXT)
        self.assertEqual(json.dumps(a, ensure_ascii=False, sort_keys=True),
                         json.dumps(b, ensure_ascii=False, sort_keys=True))

    def test_measures_multiple_units(self):
        r = tokenweight.tokenweight_analyze(SAMPLE_TEXT)
        t = r["total"]
        self.assertGreater(t["chars"], 0)
        self.assertGreater(t["words"], 0)
        self.assertGreaterEqual(t["paragraphs"], 1)

    def test_splits_sections(self):
        r = tokenweight.tokenweight_analyze(SAMPLE_TEXT)
        self.assertGreaterEqual(r["section_count"], 2)

    def test_detects_repetition(self):
        """防呆：重复内容必须被算成重复。"""
        r = tokenweight.tokenweight_analyze("重复的一句。\n重复的一句。")
        self.assertGreater(r["repetition"]["duplicate_ratio"], 0)

# -*- coding:UTF-8 -*-

# author:Li Yu
# datetime: 2025/7/25 16:55
# software: PyCharm

from correct_by_rules.detector.keyword_detector import KeywordDetector
from correct_by_rules.detector.base_detector import DetectResult


class SensitiveDetector(KeywordDetector):

    def __init__(self, sensitive_path, vocab_version):
        super().__init__(sensitive_path, vocab_version=vocab_version, vocab_type=self.error_type.sensitive)

    def detect(self, sentence, origin_idx):

        matches = self._detect(sentence)

        return [DetectResult(start=origin_idx.get(match[0], match[0]),
                             end=origin_idx.get(match[1], match[1]),
                             **match[2])
                for match in matches]


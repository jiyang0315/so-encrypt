# -*- coding:UTF-8 -*-

# author:Li Yu
# datetime: 2025/7/23 20:48
# software: PyCharm

from correct_by_rules.detector.base_detector import BaseDetector


class ModelDetector(BaseDetector):

    def __init__(self, name_path):
        super().__init__()
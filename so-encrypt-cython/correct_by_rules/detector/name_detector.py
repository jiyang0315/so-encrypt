# -*- coding:UTF-8 -*-
import loguru

# author:Li Yu
# datetime: 2025/1/22 22:12
# software: PyCharm
# from correct_by_rules.detector.base_detector import BaseDetector, DetectResult
# from correct_by_rules.structure.bktree import BKTree
# from correct_by_rules.structure.ac import ACTrie
#
#
# class NameDetector(BaseDetector):
#
#     def __init__(self, maybe_errors, proper_noun_list):
#         super().__init__()
#         self.detector = self._build_bktree(proper_noun_list)
#         self.words_detector = ACTrie(maybe_errors)
#
#     @staticmethod
#     def _build_bktree(proper_noun_list):
#         bktree = BKTree(proper_noun_list[0])
#         for item in proper_noun_list:
#             bktree.put(item)
#
#         return bktree
#
#     def detect(self,  text: str):
#         res = []
#
#         maybe_errors = self.words_detector.find_all(text)
#
#         for item in maybe_errors:
#             correct_name = self.detector.query(item[0], 1)
#             if correct_name is not None and len(correct_name.data) > 2:
#                 obj = DetectResult(
#                     error_type=self.error_type.proper,
#                     tag="r",
#                     old=text[item[1]: item[2]+1],
#                     new=correct_name.data,
#                     start=item[1],
#                     end=item[2],
#                     notice=None
#                 )
#                 res.append(obj.__dict__())
#
#         return sorted(res, key=lambda x: x.get("start"), reverse=True)



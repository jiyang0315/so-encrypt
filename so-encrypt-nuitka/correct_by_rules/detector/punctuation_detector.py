import re
import traceback
from loguru import logger
from correct_by_rules.utils.text_utils import is_chinese
from correct_by_rules.detector.base_detector import BaseDetector
from correct_by_rules.detector.base_detector import DetectResult

punctuation_matches = {
    "）": "（",
    "】": "【",
    "》": "《",
    "’": "‘",
    "”": "“",
}


en_to_zh = {
    # ".": "。",
    "?": "？",
    "!": "！",
    ",": "，",
    ";": "；",
    ":": "：",
    "(": "（",
    ")": "）",
    "]": "］",
    "[": "［",
    "<": "《",
    ">": "》",
    "`": "·",
    "\"": "",
    "\'": "",
    "~": "～"
}

suitable_combinations = {
    "。": ["“", "”", "（", "）", "《", "‘", "’", "……", "——"],
    "？": ["？", "！", "“", "”", "（", "）", "《", "》", "‘", "’", "……", "——"],
    "！": ["“", "”", "（", "）", "《", "》", "‘", "’", "……", "——", "！"],
    "，": ["“", "”", "（", "）", "《", "‘", "’", "……", "——"],
    "、": ["“", "（", "《", "‘"],
    "；": ["“", "（", "《", "‘", "……", "——"],
    "：": ["“", "（", "《", "‘", "……", "——"],
    "“": ["（", "《", "‘", "……", "——"],
    "”": ["。", "！", "？", "，", "、", "；", "：", "“", "‘", "（", "）", "《", "》", "……", "——"],
    "‘": ["（", "《", "……", "——"],
    "’": ["。", "！", "？", "，", "、", "；", "：", "”", "‘", "（", "）", "《", "……", "——"],
    "（": ["？", "“", "‘", "《", "……", "——"],
    "）": ["。", "！", "？", "，", "、", "；", "：", "“", "”", "（", "《", "》", "‘", "’", "……", "——"],
    "《": ["“", "（", "……", "——"],
    "》": ["。", "！", "？", "，", "、", "；", "：", "“", "”", "（", "）", "《", "‘", "’", "……", "——"],
    "〈": ["（", "“", "……"],
    "〉": ["。", "！", "？", "，", "、", "；", "：", "“", "”", "》", "’"],
    # "…": ["。", "！", "？", "，", "；", "（", "）", "《", "》", "“", "”", "‘", "’", "——"],
    # "—": ["！", "？", "，", "；", "（", "）", "《", "》", "“", "”", "‘", "’"],
    '%': ["。", "！", "？", "，", "、", "；", "：", "“", "”", "（", "）", "《", "》", "‘", "’", "……", "——", "～", "—", "〉"],
    "℃": ["。", "！", "？", "，", "、", "；", "：", "“", "”", "（", "）", "》", "‘", "’", "……", "——", "～", "—", "〉"]
}


class PunctuationDetector(BaseDetector):

    re_en_punc = re.compile('([“”‘’.?!,;:，。？！：<>()\[\]~\"\'`_-—]+)', re.U)

    @staticmethod
    def _check_contain_error(maybe_err, maybe_errors):
        """
        检测错误集合(maybe_errors)是否已经包含该错误位置（maybe_err)
        :param maybe_err: [error_word, begin_pos, end_pos, error_type]
        :param maybe_errors:list
        :return: bool
        """
        error_word_idx = 0
        begin_idx = 1
        end_idx = 2
        for err in maybe_errors:
            if maybe_err[error_word_idx] in err[error_word_idx] and maybe_err[begin_idx] >= err[begin_idx] and \
                    maybe_err[end_idx] <= err[end_idx]:
                return True
        return False

    def _add_maybe_error_item(self, maybe_err, maybe_errors):
        """
        新增错误
        :param maybe_err:
        :param maybe_errors:
        :return:
        """
        if maybe_err not in maybe_errors and not self._check_contain_error(maybe_err, maybe_errors):
            maybe_errors.append(maybe_err)

    def _get_punctuation(self, text):
        """
        找出所有的连续标点组合
        :param text: str
        :return: (punctuation, idx)
        """
        result = []
        blocks = self.re_en_punc.split(text)
        start_idx = 0
        for blk in blocks:
            if not blk:
                continue
            if self.re_en_punc.match(blk):
                result.append((blk, start_idx, start_idx + len(blk)))
            start_idx += len(blk)
        return result

    def detect(self, text, origin_idx):

        errors = []

        try:
            # 获取连续标点组合
            punctuation_group = self._get_punctuation(text)

            stack = []
            last = ""
            for group, start, end in punctuation_group:
                group_pre = text[start-1] if start > 0 else None
                group_end = text[end] if end < len(text) else None
                # pre = " "
                for idx, c in enumerate(group):
                    new = ""
                    offset = 0
                    if c == "“" or c == "‘":
                        stack.append(c)
                    elif (c == "”" or c == "’") and stack:
                        stack.pop()

                    elif c in ["[", "(", "<"]:
                        # 作为序号 或 前边是英文 保持
                        if ((group_end and group_end.isnumeric())
                                or (group_pre and not is_chinese(group_pre))
                                or (not group_pre and not group_end)):
                            last = c
                            continue
                        new = en_to_zh.get(c)
                        last = new

                    elif c in ["]", ")", ">"]:
                        # 与前一个匹配
                        if (c == "]" and last == "［") or (c == ">" and last == "《") or (c == ")" and last == "（"):
                            new = en_to_zh.get(c)

                    elif group_pre is not None and is_chinese(group_pre) and c in en_to_zh:
                        # 前为中文, 标点为英文
                        if c == "'":
                            if not stack:
                                new = "‘"
                                stack.append("‘")
                            elif stack[-1] == "‘":
                                new = "’"
                                stack.pop()
                        elif c == "\"":
                            if not stack:
                                new = "“"
                                stack.append("“")
                            elif stack[-1] == "“":
                                new = "”"
                                stack.pop()
                        else:
                            new = en_to_zh.get(c)
                    # else:
                    #     nxt = text[start+idx+1] if idx < len(group) - 1 else " "
                    #     if c == pre == "-":
                    #         new = "——"
                    #         offset = 1
                    #         pre = c+c
                    #     elif c == pre == "_":
                    #         new = "—"
                    #         offset = 1
                    #         pre = c+c
                    #     elif c == "…" and pre != c and nxt != c:
                    #         new = "……"
                    #     elif c == "_" and pre != c and nxt != c:
                    #         new = "-"
                    # if offset == 0:
                    #     pre = c
                    if new:
                        errors.append(DetectResult(
                            self.error_type.punctuation,
                            "r",
                            text[start+idx-offset:start+idx+1],
                            new,
                            origin_idx.get(start+idx-offset, start+idx-offset),
                            origin_idx.get(start+idx, start+idx),
                            None)
                      )

        except Exception as e:
            logger.error(e)
            traceback.print_exc()
        finally:
            return sorted(errors, key=lambda x: x.start, reverse=True)


if __name__ == '__main__':

    d = PunctuationDetector()
    s = '接受现实的复杂性——"善"中包含着"恶"，"恶"中隐匿着"善"，"过错"往往也蕴含着"正确"。当面对成瘾问题时（无论是自身、亲友或熟人），这种撕裂性的二元对立会以最剧烈的方式显现。'

    print(d.detect(s))

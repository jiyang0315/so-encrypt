import os
import re
from loguru import logger
from correct_by_rules.detector.keyword_detector import KeywordDetector
from correct_by_rules.detector.base_detector import DetectResult


class ReignDetector(KeywordDetector):
    def __init__(self, reign_path):
        super().__init__(reign_path)

    def detect(self, sentence: str, origin_idx):
        res = []
        candidates = self._detect(sentence)
        for candidate in candidates:
            print(candidate)
            reign = candidate[2]["old"]
            matches = self.find_year_string(sentence, reign)
            for match in matches:
                if match.start() != candidate[0]:
                    continue
                logger.info(f"检测到年号：{match.group()}, 位置:({match.start()},{match.end()})")

                first_year, second_year = self._split_match_str(match, reign)

                reign_info = candidate[2]
                new = ""
                hyphen = "（公元" if "公元" in match.group() else "（"

                # 判断年号是否在正确范围内
                first_year_num = self._year_str_to_num(first_year)
                first_order_num = int(reign_info.get("first_order", 0))

                if first_year_num > first_order_num + int(reign_info.get("number_of_years")) \
                        and reign in ["唐贞元", "德宗贞元"]:
                    reign = "贞元"
                    reign_info = self._get(reign)
                    first_year_num = self._year_str_to_num(first_year)
                    first_order_num = int(reign_info.get("first_order", 0))

                if first_year_num < first_order_num:
                    new = f'{reign_info.get("duration")[0]}{hyphen}{reign_info.get("year")[0]}'
                elif first_year_num > first_order_num + int(reign_info.get("number_of_years")):
                    new = f'{reign_info.get("duration")[1]}{hyphen}{reign_info.get("year")[1]}'
                elif first_year == "一":
                    new = f'{reign_info.get("duration")[0]}{hyphen}{reign_info.get("year")[0]}'
                else:
                    start_year = reign_info.get("year")[0]
                    if "前" in start_year:
                        new_year = int(start_year[1:]) - (first_year_num - first_order_num)
                        new = f'{reign}{first_year}年{hyphen}前{new_year}'
                    else:
                        new_year = int(start_year) + (first_year_num - first_order_num)
                        new = f'{reign}{first_year}年{hyphen}{new_year}'

                if reign == "天宝" and first_year_num >= 3:
                    new = new.replace("年", "载")

                if new and new != match.group():
                    logger.info(f"正确表述：{new}")
                    res.append(DetectResult(self.error_type.confusion, "r",
                                            match.group(),
                                            new,
                                            origin_idx.get(match.start(), match.start()),
                                            origin_idx.get(match.end() - 1, match.end() - 1),
                                            None))
                else:
                    logger.info(f"表述正确")

        return res

    @staticmethod
    def find_year_string(sentence, era):
        pattern = re.escape(era) + "(?:[元一二三四五六七八九十]{1,4})[年载]{1}[（|(](公元)?(前)?\d{1,4}"
        matches = re.finditer(pattern, sentence)
        return matches

    @staticmethod
    def _split_match_str(match, era):
        part = match.group(0).split("年") if "年" in match.group(0) else match.group(0).split("载")
        first_year = part[0][len(era):]
        second_year = part[1][1:]
        if "公元" in second_year:
            second_year = second_year[2:]
        return first_year, second_year

    @staticmethod
    def _year_str_to_num(text):

        digit_map = {
            '零': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4,
            '五': 5, '六': 6, '七': 7, '八': 8, '九': 9, "元": 1
        }

        num = 0
        for i, s in enumerate(text):

            if s == "十":
                if i == 0:
                    num += 10
                else:
                    num *= 10
            if s in digit_map:
                num += digit_map[s]

        return num


if __name__ == '__main__':
    # 示例文本
    text = "唐贞元十二年（1214"

    d = ReignDetector("../dict/base/reign.pkl")
    res = d.detect(text, {})
    print(res)

import re
from correct_by_rules.detector.base_detector import BaseDetector, DetectResult


class NumberDetector(BaseDetector):

    _pattern = r'\d[,\d]*,[,\d]*(\.\d+)?'

    def __init__(self):
        super().__init__()

    def detect(self, text):

        res = []

        matches = re.finditer(self._pattern, text)

        # 过滤出符合标准格式的数字（带千分位或小数）
        for match in matches:
            number = match.group()  # 提取匹配的数字
            clean_number = number.replace(',', '')
            if not self.is_valid_number(clean_number):
                continue
            start = match.start()  # 匹配数字的起始位置
            end = match.end()  # 匹配数字的结束位置

            if '.' in clean_number:
                # 如果是小数，分离整数和小数部分
                integer_part, decimal_part = clean_number.split('.')
                formatted_number = f"{int(integer_part):,}.{decimal_part}"  # 插入千分位
            else:
                # 如果是整数
                formatted_number = f"{int(clean_number):,}"  # 插入千分位

            if formatted_number != number:

                obj = DetectResult(
                    error_type=self.error_type.punctuation,
                    tag="r",
                    old=number,
                    new=formatted_number,
                    start=start,
                    end=end-1,
                    notice=None
                )

                res.append(obj.__dict__())

        return sorted(res, key=lambda x: x.get("start"), reverse=True)

    @staticmethod
    def is_valid_number(s):
        # 去掉千分位逗号，检查格式
        try:
            float(s)  # 尝试转换为浮点数
            return True
        except ValueError:
            return False


if __name__ == '__main__':
    t = """
    今天的收入是1234元，昨天是1,234.56元，但还有一些错误的格式，比如12,34或1.2.3.4。
    总的来说，合计收入是1,2345.67元。
    229,304,611.32
    """
    c = NumberDetector()
    r = c.detect(t)
    print(r)

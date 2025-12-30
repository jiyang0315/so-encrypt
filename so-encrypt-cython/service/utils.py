# -*- coding:UTF-8 -*-

# author:Li Yu
# datetime: 2025/7/23 22:26
# software: PyCharm


class CorrectionUtils:

    @classmethod
    def del_repetitive_blank(cls, input_sentence):
        res = []
        no_space_to_origin = {}
        for idx, char in enumerate(input_sentence):
            if char.isspace():
                if res and cls.is_alphabet(res[-1]):
                    no_space_to_origin[len(res)] = idx
                    res.append(char)
            else:
                no_space_to_origin[len(res)] = idx
                res.append(char)

        return "".join(res), no_space_to_origin

    @staticmethod
    def is_alphabet(uchar):
        """判断一个unicode是否是英文字母"""
        if (u'a' <= uchar <= u'z') or (u'A' <= uchar <= u'Z'):
            return True
        else:
            return False

    @classmethod
    def is_punc_string(cls, string):
        chinese_punct = "……·——！―〉<>？｡。＂＃＄％＆＇（）＊＋，－／：《》；〈〉＜＝＞＠［’．＼］＾＿’｀｛｜｝～｟｠｢｣､、〃》「」『』【】〔〕〖〗〘〙〚〛〜〝〞〟〰〾〿–—‘'‛“”„‟…‧﹏$.&*:,?!()[]-$"
        english_punct = r"""!"#$%&'()*+,-./:;<=>?@[\]^_`{|}~"""
        all_punct = chinese_punct + english_punct
        for s in string:
            if s in all_punct:
                continue
            else:
                return False
        return True
# -*- coding:UTF-8 -*-

# author:Li Yu
# datetime: 2023/10/23 17:42
# software: PyCharm

class ErrorType(object):

    confusion = "confusion"  # 易错词
    whitelist = "whitelist"  # 白名单
    quotation = "quotation"  # 语录
    leader = "leader"  # 领导人
    position = "position"  # 职位
    fallen_officers = "fallen_officers"  # 落马官员
    blacklist = "blacklist"  # 黑名单
    blacklist_mask = "blacklist_mask"  # 黑名单
    blacklist_replace = "blacklist_replace"  # 黑名单
    sensitive = "sensitive"  # 敏感词
    punctuation = "punctuation"  # 标点符号
    model = "model"  # 模型检测
    now_called = "now_called"  # 现称
    quoting_legal = "quoting_legal"  # 法规
    serial_number = "serial_number"  # 序号
    coinage = "coinage"  # 造字
    coinage_first = "coinage_first_choice"  # 造字 首选
    first_choice = "first_choice"  # 首选
    alien = "alien"  # 异形词
    incorrect_expression = "incorrect_expression"  # 表述有误
    after_a_certain_year = "after_a_certain_year"  # xx年以后
    term = "term"  # 规范术语
    word = "word"  # 词类型错误
    char = "char"  # 字类型错误
    proper = "proper"  # 专名纠错，包括成语纠错、人名纠错等


class ModelId(object):

    all = "xt-20250305183041-correct"
    single = "xt-20250305183041-allround"

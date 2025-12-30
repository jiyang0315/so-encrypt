from correct_by_rules.utils.text_utils import compare_corrected_context, is_alphabet
from service.enum_typing import ErrorType
from loguru import logger


class ErrorGroup:
    error_priority = {
        ErrorType.leader: 0,
        ErrorType.position: 0,
        ErrorType.whitelist: 1,
        ErrorType.fallen_officers: 2,
        ErrorType.sensitive: 2,
        ErrorType.blacklist: 3,
        ErrorType.blacklist_mask: 3,
        ErrorType.blacklist_replace: 3,
        ErrorType.confusion: 4,
        ErrorType.incorrect_expression: 5,
        ErrorType.after_a_certain_year: 6,
        ErrorType.now_called: 7,
        ErrorType.quoting_legal: 8,
        ErrorType.serial_number: 9,
        ErrorType.punctuation: 10,
        ErrorType.model: 11
    }

    def __init__(self):
        self.nodes = []
        self.overlap_node = {

        }
        self.start = 0
        self.end = 0

    def add_node(self, node):
        if not self.nodes:
            self.nodes.append(node)
            self.start = node.start
            self.end = node.end
            self.overlap_node[id(node)] = []
        else:
            start = node.start
            end = node.end
            if int(start) > int(self.end):
                return False
            self.end = max(self.end, end)
            self.overlap_node[id(node)] = []
            for idx, n in enumerate(self.nodes):
                if start <= n.end:
                    self.overlap_node[id(node)].append(id(n))
                    self.overlap_node[id(n)].append(id(node))

            self.nodes.append(node)
            self.nodes.sort(key=lambda x: x.end, reverse=True)
        return True

    def count(self):
        return len(self.nodes)

    def get_non_overlap_nodes(self):
        if self.count() < 2:
            res = self.nodes
        else:
            res = []

            sorted_nodes = sorted(self.nodes, key=lambda x: self.error_priority.get(x.error_type, 4))
            # 优先级从高到低，删除存在交集的节点
            for idx, n in enumerate(sorted_nodes):
                if id(n) in self.overlap_node and self.overlap_node[id(n)]:
                    for overlap_idx in self.overlap_node[id(n)]:
                        if overlap_idx in self.overlap_node:
                            self.overlap_node.pop(overlap_idx)
                        self.overlap_node[id(n)] = []
                    res.append(n)
        return res


class ResultFilter(object):

    @classmethod
    def filter_model_result(cls, ensemble_result, model_input_sentence,
                            input_sentence, blacklist_detector, sensitive, confusion, boundary):

        # 回替
        ensemble_result = cls._filter_incorrect_modification(ensemble_result,
                                                             model_input_sentence,
                                                             blacklist_detector,
                                                             sensitive,
                                                             confusion,
                                                             boundary)

        diffs = compare_corrected_context(input_sentence, ensemble_result, boundary)

        diffs = cls._filter_non_chinese_modification(diffs)

        diffs = cls._filter_meaningless_modification(diffs)

        return [diff for diff in diffs if len(diff.get("origin", "")) < 5 and len(diff.get("text", "")) < 5]

    @classmethod
    def filter_all_result(cls, hit, whitelist_result):
        hit = cls.filter_by_whitelist(hit, whitelist_result)
        logger.info(f"whitelist filter result {hit}")
        hit = cls.filter_by_priority(hit)
        logger.info(f"priority filter result {hit}")
        return hit

    @staticmethod
    def _filter_incorrect_modification(ensemble_result, input_sentence, blacklist_detector, sensitive, confusion
                                       , boundary):
        """
            过滤模型修改产生的新的易错词、敏感词、黑名单词
            1.判断模型修改点
            2.检测修改结果中的易错词、敏感词、黑名单、去空格
            3.判断步骤1、2的结果是否有交集，若有则做反向修改
        """
        # 模型修改点（以修改结果为基础坐标）
        diff_between_input_ensemble = compare_corrected_context(ensemble_result, input_sentence, boundary)
        intervals = []
        if blacklist_detector:
            blacklist_result = [[s.start, s.end] for s in blacklist_detector.detect(ensemble_result, {})]
            intervals.extend(blacklist_result)
        if sensitive:
            sensitive_result = [[s.start, s.end]for s in sensitive.detect(ensemble_result, {})]
            intervals.extend(sensitive_result)
        if confusion:
            confusion_result = confusion.detect(ensemble_result, {}, boundary)
            intervals.extend([[c.start, c.end] for c in confusion_result])

        filter_interval = sorted(intervals, key=lambda x: (x[0], x[1]))

        # 回替模型修改点中黑名单、敏感词、易错词存在交集部分
        if filter_interval and diff_between_input_ensemble:
            i = len(filter_interval) - 1
            j = len(diff_between_input_ensemble) - 1
            while i >= 0 and j >= 0:

                filter_start = filter_interval[i][0]
                filter_end = filter_interval[i][1]
                diff = diff_between_input_ensemble[j]
                model_edit_end = diff["end"] - 1 if diff["tag"] != "insert" else diff["end"]
                model_edit_start = diff["start"]
                tag = diff["tag"]
                if model_edit_start <= filter_end and model_edit_end >= filter_start:
                    # 存在交集, 回替
                    if tag == "insert":
                        ensemble_result = ensemble_result[:diff["start"]] + diff["text"] + ensemble_result[diff["end"]:]
                    if tag == "delete":
                        ensemble_result = ensemble_result[:diff["start"]] + ensemble_result[diff["end"]:]
                    if tag == "replace":
                        ensemble_result = (ensemble_result[:diff["start"]] + diff["text"] +
                                           ensemble_result[diff["end"]:])
                    j -= 1
                else:
                    # 不存在交集，比对下一个区间
                    if filter_start > model_edit_start:
                        i -= 1
                    else:
                        j -= 1
        for diff in diff_between_input_ensemble[::-1]:
            if "text" in diff and diff["text"].count(" "):
                ensemble_result = ensemble_result[:diff["start"]] + diff["text"] + ensemble_result[diff["end"]:]
        return ensemble_result

    @staticmethod
    def _filter_non_chinese_modification(diffs, need_chinese_punc=True):
        if need_chinese_punc:
            from correct_by_rules.utils.text_utils import is_chinese_punc_string as is_chinese_string
        else:
            from correct_by_rules.utils.text_utils import is_chinese_string
        res = []
        for diff in diffs:
            correct_text = diff.get("text") if diff["tag"] == "insert" else diff["origin"]
            if is_chinese_string(correct_text):
                res.append(diff)
        return res

    @classmethod
    def filter_by_whitelist(cls, maybe_errors, whitelist_result):
        filter_interval = [i[1:] for i in whitelist_result]
        filter_interval = sorted(filter_interval, key=lambda x: (x[0], x[1]))
        logger.info(f"all_maybe_errors:{maybe_errors},  filter_interval: {filter_interval}")
        res = []
        dirty = set()
        if filter_interval and maybe_errors:
            i, j = 0, 0
            while i < len(filter_interval) and j < len(maybe_errors):
                filter_start = filter_interval[i][0]
                filter_end = filter_interval[i][1]

                hit_start = maybe_errors[j].start
                hit_end = maybe_errors[j].end

                if hit_start <= filter_end and hit_end >= filter_start:
                    # 存在交集， 标记丢弃
                    dirty.add(j)
                    j += 1
                else:
                    if filter_end < hit_end:
                        i += 1
                    else:
                        j += 1
            for idx, e in enumerate(maybe_errors):
                if idx not in dirty:
                    res.append(e)
        else:
            res = maybe_errors

        logger.info(f"after whitelist filter:{res}")
        return res

    @classmethod
    def filter_by_priority(cls, maybe_errors):
        res = []
        logger.info(f"before priority filter:{maybe_errors}")
        group = ErrorGroup()
        for node in maybe_errors:
            if not group.add_node(node):
                res.extend(group.get_non_overlap_nodes())
                group = ErrorGroup()
                group.add_node(node)
        res.extend(group.get_non_overlap_nodes())
        logger.info(f"after priority filter:{res}")
        return res

    @staticmethod
    def _filter_meaningless_modification(diffs):
        res = []
        for diff in diffs:
            if diff["tag"] == "replace":
                if diff["text"] in ['它', '他', '她'] and diff["origin"] in ['它', '他', '她']:
                    continue
                if diff["text"] in ['和', '或'] and diff["origin"] in ['和', '或']:
                    continue
            res.append(diff)
        return res

    @classmethod
    def del_repetitive_blank(cls, input_sentence):
        res = []
        no_space_to_origin = {}
        for idx, char in enumerate(input_sentence):
            if char.isspace():
                if res and is_alphabet(res[-1]):
                    no_space_to_origin[len(res)] = idx
                    res.append(char)
            else:
                no_space_to_origin[len(res)] = idx
                res.append(char)

        return "".join(res), no_space_to_origin

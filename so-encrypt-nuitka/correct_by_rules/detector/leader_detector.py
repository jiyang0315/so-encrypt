# -*- coding:UTF-8 -*-
import json

# author:Li Yu
# datetime: 2024/1/6 11:42
# software: PyCharm

from correct_by_rules.detector.keyword_detector import KeywordDetector
from correct_by_rules.detector.base_detector import DetectResult
from paddlenlp import Taskflow
import string
import unicodedata


class LeaderDetector(KeywordDetector):

    def __init__(self, pkl_path, vocab_version):
        super().__init__(pkl_path, vocab_version=vocab_version, vocab_type=self.error_type.leader)
        self.ner = Taskflow("pos_tagging")

    def _detect_name_and_org(self, text, offset):
        start = 0
        res = []
        if text == "":
            return res, True
        tags = self.ner(text)
        for idx, item in enumerate(tags):
            word = item[0]
            tag = item[1]
            if tag == "PER" and len(word) >= 2:
                res.append([text[start:start + len(word)], {}, offset + start, offset + start + len(word) - 1, 999 + start])
            if tag in ["v", "vd", "vn", "a", "ad", "an", "m", "q", "u", "LOC", "TIME"]:
                return res, False
            start += len(word)
        return res, True
    
    @staticmethod
    def _has_substantive_content(text):
        for idx, s in enumerate(text):
            if (s not in string.punctuation and not unicodedata.category(s).startswith("P")
                    and s not in ["和", "或", '与']
                    and (0 < idx < len(text) - 1 and text[idx:idx+2] != "以及" and text[idx-1:idx+1] != '以及')):
                return True
        return False

    def detect(self, sentence, origin_idx):

        # 命中的错误
        hit_errors = []

        # 当前命中的职位详情
        current_position_details = []
        # 当前命中人名对应的职位交集
        correct_position = []

        # 当前命中的人名详情
        current_leader_details = []
        # 当前命中的职位对应的人名交集
        correct_leader = []
        # 未知人名
        unknow_names = []
        last_end = 0

        # 领导人组合排序
        leader_groups = []

        group_start = 0

        # 同时检测领导人和职位
        leader_name_or_position = self._detect(sentence)
        print(leader_name_or_position)
        for idx, (start, end, info) in enumerate(leader_name_or_position):
            # 判断检测范围，范围终止条件：
            # 1.当后续出现非名词和人名
            # 2.已有人名的情况下后续出现职位
            # 3.最后一个关键词
            person, person_flag = self._detect_name_and_org(sentence[last_end:start], last_end)
            unknow_names.extend(person)
            # for person
            if (not person_flag or info.get("type") == "title") and (current_leader_details + unknow_names):
                detect_result, group = self._detect_errors(sentence, current_leader_details, correct_leader,
                                                           current_position_details, correct_position, origin_idx,
                                                           unknow_names)
                hit_errors.extend(detect_result)
                leader_groups.append(group)

                current_leader_details = []
                correct_leader = []
                current_position_details = []
                correct_position = []
                unknow_names = []

            last_end = end + 1

            if info.get("type") == "title":
                group_start = start
                priority = info.get("priority")
                leaders = info.get("names")
                # 更新正确的领导人集合
                if current_position_details:
                    correct_leader = list(set(correct_leader) & set(leaders))
                else:
                    correct_leader = leaders

                current_position_details.append([sentence[start:end + 1], {
                    "position": info["old"],
                    "leaders": leaders
                }, start, end, priority])

            if info.get("type") == "name":
                correct_name = info.get("correct_name")
                priority = info.get("priority")
                positions = info.get("titles")
                leader_title = [p for p in positions if not self._get(p).get("is_full")]
                # 更新的正确职位集合
                if current_leader_details:
                    correct_position = list(set(correct_position) &
                                            set(positions))
                else:
                    correct_position = positions
                current_leader_details.append([correct_name, {
                    "correct_name": correct_name,
                    "positions": leader_title
                }, start, end, priority])
        if current_position_details or current_leader_details:
            person, person_flag = self._detect_name_and_org(sentence[last_end:], last_end)
            unknow_names.extend(person)
            detect_result, group = self._detect_errors(sentence, current_leader_details, correct_leader,
                                                       current_position_details, correct_position, origin_idx,
                                                       unknow_names)
            hit_errors.extend(detect_result)

            leader_groups.append(group)

        if len(leader_groups) > 1:
            pre_end = group_start
            sort_group = []
            for group in leader_groups:
                if not group["match"] or self._has_substantive_content(sentence[pre_end:group["start"]]):
                    if len(sort_group) > 1:
                        start = sort_group[0]["start"]
                        end = sort_group[-1]["end"] + 1
                        sort_group = sorted(sort_group, key=lambda x: x["priority"])
                        new = "，".join([g["corrected"] for g in sort_group])
                        hit_errors.append(DetectResult(**{
                            "old": sentence[start:end],
                            "new": new,
                            "start": origin_idx.get(start, start),
                            "end": origin_idx.get(end, end),
                            "tag": "r",
                            "error_type": self.error_type.leader,
                            "notice": None,
                        }))
                    sort_group = []

                else:
                    sort_group.append(group)

                pre_end = group["end"] + 1

            if len(sort_group) > 1:
                start = sort_group[0]["start"]
                end = sort_group[-1]["end"] + 1
                sort_group = sorted(sort_group, key=lambda x: x["priority"])
                new = "，".join([g["corrected"] for g in sort_group])

                all_leaders = []
                for g in sort_group:
                    all_leaders.extend(g["leaders"])
                all_leaders = list(dict.fromkeys(all_leaders))

                notice = self.get_personal_notice(all_leaders)

                hit_errors.append(DetectResult(**{
                    "old": sentence[start:end],
                    "new": new,
                    "start": origin_idx.get(start, start),
                    "end": origin_idx.get(end, end),
                    "tag": "r",
                    "error_type": self.error_type.leader,
                    "notice": notice,
                }))

        return hit_errors

    def _detect_errors(self, sentence, current_leader_details, correct_leader,
                       current_position_details, correct_position, origin_idx, unknown_name):
        res = []
        leader_suggest = ""
        position_suggest = ""
        current_leader = [current_leader_detail[1].get("correct_name")
                          for current_leader_detail in current_leader_details]
        current_position = [i[1].get("position") for i in current_position_details]
        correct_position = sorted(correct_position, key=lambda x: self._get(x).get("priority"))
        correct_leader = sorted(correct_leader, key=lambda x: self._get(x).get("priority"))
        sorted_current_leader = [i[0] for i in sorted(current_leader_details, key=lambda x: x[-1]) if i[1]]
        sorted_current_position = [i[0] for i in sorted(current_position_details, key=lambda x: x[-1])]
        all_details = sorted(current_leader_details+current_position_details+unknown_name, key=lambda x: x[2])
        group = {
            "start": all_details[0][2],
            "end": all_details[-1][3],
            "match": False,
        }

        if current_leader and current_position:

            # 检测是否匹配
            leader_suggest, position_suggest, leader_tag, position_tag = \
                self._match_leader_position(current_leader, correct_leader, sorted_current_leader,
                                            correct_position, sorted_current_position)
            if leader_suggest and position_suggest:
                # 领导人和职位不匹配
                # 领导人组合错误
                start = current_leader_details[0][2]
                end = current_leader_details[-1][3]
                res.append(DetectResult(**{
                    "old": sentence[start:end + 1],
                    "new": leader_suggest,
                    "start": origin_idx.get(start, start),
                    "end": origin_idx.get(end, end),
                    "tag": leader_tag,
                    "error_type": self.error_type.leader,
                    "notice": self.get_personal_notice(current_leader),
                }))
                # 职位组合错误
                start = current_position_details[0][2]
                end = current_position_details[-1][3]
                res.append(DetectResult(**{
                    "old": sentence[start:end + 1],
                    "new": position_suggest,
                    "start": origin_idx.get(start, start),
                    "end": origin_idx.get(end, end),
                    "tag": position_tag,
                    "error_type": self.error_type.position,
                    "notice": self.get_position_notice("、".join(current_position)),
                }))
            elif leader_suggest:
                # 领导人组合错误
                start = current_leader_details[0][2]
                end = current_leader_details[-1][3]
                res.append(DetectResult(**{
                    "old": sentence[start:end + 1],
                    "new": leader_suggest,
                    "start": origin_idx.get(start, start),
                    "end": origin_idx.get(end, end),
                    "tag": leader_tag,
                    "error_type": self.error_type.leader,
                    "notice": self.get_personal_notice(current_leader),
                }))
                # 职位组合正确，检测排序和拼写
                res.extend(self._detect_sort_and_spell(sentence, current_position_details,
                                                       current_position, sorted_current_position,
                                                       self.error_type.position, origin_idx))
            elif position_suggest:
                # 职位组合错误
                start = current_position_details[0][2]
                end = current_position_details[-1][3]
                res.append(DetectResult(**{
                    "old": sentence[start:end + 1],
                    "new": position_suggest,
                    "start": origin_idx.get(start, start),
                    "end": origin_idx.get(end, end),
                    "tag": position_tag,
                    "error_type": self.error_type.position,
                    "notice": self.get_position_notice("、".join(current_position)),
                }))
                # 领导人组合正确，检测排序和拼写
                res.extend(self._detect_sort_and_spell(sentence, current_leader_details, current_leader,
                                                       sorted_current_leader, self.error_type.leader, origin_idx,
                                                       unknown_name))
            else:
                # 匹配正确检查拼写错误

                # 职位组合正确，检测排序和拼写
                position_spell_error = self._detect_sort_and_spell(sentence, current_position_details,
                                                                   current_position, sorted_current_position,
                                                                   self.error_type.position, origin_idx)
                res.extend(position_spell_error)

                leader_spell_error = self._detect_sort_and_spell(sentence, current_leader_details, current_leader,
                                                                 sorted_current_leader, self.error_type.leader,
                                                                 origin_idx, unknown_name)
                res.extend(leader_spell_error)

                group["priority"] = current_position_details[0][-1],
                group["match"] = True,
                group["corrected"] = f'{"、".join(sorted_current_position)}{"、".join(sorted_current_leader)}'
                group["leaders"] = sorted_current_leader

        elif current_leader:
            # 仅检测到领导
            res.extend(self._detect_sort_and_spell(sentence, current_leader_details, current_leader,
                                                   sorted_current_leader, self.error_type.leader, origin_idx,
                                                   unknown_name))
        elif current_position:
            # 仅检测到职位, 暂无拼写错误
            if current_leader_details:
                # 非领导人人名
                start = current_leader_details[0][2]
                end = current_leader_details[-1][3]
                res.append(DetectResult(**{
                    "old": sentence[start:end + 1],
                    "new": "、".join(correct_leader) if correct_leader else "",
                    "start": origin_idx.get(start, start),
                    "end": origin_idx.get(end, end),
                    "tag": "r" if correct_leader else "",
                    "error_type": self.error_type.leader,
                    "notice": self.get_personal_notice(current_leader),
                }))

            start = current_position_details[0][2]
            end = current_position_details[-1][3]
            res.append(DetectResult(**{
                "old": sentence[start:end + 1],
                "new": "、".join(correct_position) if current_position != sorted_current_position else "",
                "start": origin_idx.get(start, start),
                "end": origin_idx.get(end, end),
                "tag": "r" if current_position != sorted_current_position else "",
                "error_type": self.error_type.position,
                "notice": self.get_position_notice("、".join(current_position))
            }))

        return res, group

    def _match_leader_position(self, current_leader, correct_leader, sorted_current_leader,
                               correct_position, sorted_current_position):
        leader_result = ""
        position_result = ""
        leader_tag = ""
        position_tag = ""

        if not sorted(current_leader) == sorted(list(set(current_leader) & set(correct_leader))):
            # 检测的领导和职位不匹配
            if correct_leader and correct_position:
                # 均有正确的职位和正确领导人

                full_name_positions = [p for p in correct_position if not self._get(p).get("is_full")]

                position_result = f'符合({"、".join(sorted_current_position)})的有({"、".join(correct_leader)})'

                leader_result = f'符合({"、".join(sorted_current_leader)})' \
                                f'{"的头衔有" if len(full_name_positions) == 1 else "共有的有"}' \
                                f'({"、".join(full_name_positions)})'

            elif correct_position:
                # 有正确职位推荐
                full_name_positions = [p for p in correct_position if not self._get(p).get("is_full")]
                position_result = "、".join(full_name_positions)
                position_tag = "r"

            elif correct_leader:
                # 有正确的领导人推荐
                leader_result = "、".join(correct_leader)
                leader_tag = "r"
            else:
                # 无正确匹配项
                position_result = "此处职位信息存在错误，请复核。"
                leader_result = "此处领导人信息存在错误，请复核。"

        return leader_result, position_result, leader_tag, position_tag

    def _detect_sort_and_spell(self, sentence, details, current, sorted_current, error_type, origin_idx,
                               unknown_name=None):
        res = []
        if not sorted_current or sorted_current == current or len(details) < 2:
            # 顺序正确 检查拼写
            for info in details:
                start = info[2]
                end = info[3]
                origin = sentence[info[2]:info[3] + 1]
                correct = info[1].get("correct_name") if error_type == self.error_type.leader \
                    else info[1].get("position")

                if not correct:
                    notice = self.get_personal_notice(origin) if error_type == self.error_type.leader \
                        else self.get_position_notice(origin)
                    res.append(DetectResult(**{
                        "old": origin,
                        "new": "",
                        "start": origin_idx.get(start, start),
                        "end": origin_idx.get(end, end),
                        "tag": "",
                        "error_type": error_type,
                        "notice": notice
                    }))
                else:
                    if origin != correct:
                        notice = self.get_personal_notice(correct) if error_type == self.error_type.leader \
                            else self.get_position_notice(correct)
                        res.append(DetectResult(**{
                            "old": origin,
                            "new": correct,
                            "start": origin_idx.get(start, start),
                            "end": origin_idx.get(end, end),
                            "tag": "r",
                            "error_type": error_type,
                            "notice": notice
                        }))
                    # elif correct == "习近平":
                    #     res.append({
                    #         "old": origin,
                    #         "new": "",
                    #         "start": origin_idx.get(start, start),
                    #         "end": origin_idx.get(end, end),
                    #         "tag": "",
                    #         "error_type": error_type,
                    #         "idx": "习近平"
                    #     })
        else:
            # 顺序错误
            start = details[0][2]
            end = details[-1][3]
            origin = sentence[start:end + 1]
            notice = self.get_personal_notice(sorted_current) \
                if error_type == self.error_type.leader \
                else self.get_position_notice("、".join(sorted_current + (unknown_name if unknown_name else [])))
            range_object = {
                "old": origin,
                "start": origin_idx.get(start, start),
                "end": origin_idx.get(end, end),
                "tag": "r",
                "new": "、".join(sorted_current),
                "error_type": error_type,
                "notice": notice
            }
            res.append(DetectResult(**range_object))
        return res

    def detect_leader_name(self, sentence):
        hits = self._detect(sentence)
        return [[hit[2]["correct_name"], hit[0], hit[1]]
                for hit in hits if hit[2]['type'] == "name"]

    def get_personal_notice(self, names):
        if isinstance(names, str):
            return self.get_leader_notice(names)
        else:
            return [self.get_leader_notice(name) for name in names]

    def get_leader_notice(self, text):
        correct_positions = None
        correct_names = []
        unknown_names = []
        names = text.split("、")
        for name in names:
            correct_name = name
            info = self._get(name)
            if info is not None:
                correct_names.append(correct_name)
                positions = info.get("titles")

                # 更新的正确职位集合
                if correct_positions is not None:
                    correct_positions = list(set(correct_positions) &
                                             set(positions))
                else:
                    correct_positions = positions
            else:
                unknown_names.append(name)

        full_positions = [p for p in correct_positions if not self._get(p).get("is_full")]
        full_positions.sort(key=lambda x: self._get(x).get("priority"))
        correct_names.sort(key=lambda x: self._get(x).get("priority"))

        if correct_names:
            return {
                "correct_name": "、".join(correct_names),
                "positions": full_positions if full_positions else ["该领导人组合无共同职位"]
            }
        else:
            return {
                "correct_name": "、".join(unknown_names),
                "positions": ["非当前国家领导人"]
            }

    def get_position_notice(self, text):
        correct_positions = []
        correct_names = None
        positions = text.split("、")
        for position in positions:
            info = self._get(position)
            if info is not None:
                correct_positions.append(position)
                names = info.get("names")

                # 更新的正确职位集合
                if correct_names is not None:
                    correct_names = list(set(correct_names) & set(names))
                else:
                    correct_names = names

        correct_names.sort(key=lambda x: self._get(x).get("priority"))
        correct_positions.sort(key=lambda x: self._get(x).get("priority"))
        return {
            "position": "、".join(correct_positions),
            "leaders": correct_names if correct_names else ["该职位组合无对应领导人"]
        }


if __name__ == '__main__':
    leader = LeaderDetector("../dict/base/leader.pkl", "base")

    # 职位和名字均存在且正确
    # print("职位和名字均存在且正确:", leader.detect(
    #     "在京中共中央政治局委员、中央书记处书记，国务委员，全国人大常委会副委员长，全国政协副主席，最高人民法院院长，最高人民检察院检察长和中央军委委员出席仪式。", {}, {}))
    # print(
    #     leader.get_position_notice("中共中央政治局委员、国务委员、全国政协副主席、最高人民法院院长、最高人民检察院检察长"))
    # 只有职位
    # res = leader.detect("中华人民共和国主席", {}, {})
    # print("只有职位:", [r.__dict__() for r in res])
    # 只有职位+非当前领导人
    res = leader.detect("国家主席、中共中央政治局委员习近平、俞正声、赵乐际", {})
    print("只有职位+非当前领导人:", [r.__dict__() for r in res])
    res = leader.detect("曾武中波建交30年来，双方秉持平等相待、相互尊重、李良序互利共赢原则发展双边关系，政治互信持续深化，务实合作成果丰硕，树立了不同大小、不同历史文化、刘金焕不同社会制度国家友好相处、何庆柱携手发展的典范。", {})
    print("只有职位+非当前领导人:", [r.__dict__() for r in res])
    # 职位顺序错误
    # res = leader.detect("国家主席、中共中央政治局委员习近平", {}, {})
    # print("职位顺序错误:", [r.__dict__() for r in res])
    # # 人名顺序错
    # print("人名顺序错:", leader.detect("石泰峰、尹力、刘国中、李干杰、李书磊、李鸿忠、何卫西、何立峰、张又侠、张国清、陈文青、贾庆林、张德江、俞正声、栗战书、汪洋、曾庆红、李长春、贺国强、刘云山、王岐山、张高丽，中共中央书记处、全国人大常委会、国务院、最高人民法院、最高人民检察院、全国政协、中央军委领导同志和从领导职务上退下来的同志", {}, {}))
    # # 职位、人名均有正确组合，不匹配
    # res = leader.detect("国家主席、中共中央政治局委员习近平、俞正声、赵乐际", {}, {})
    # print("职位、人名均有正确组合，不匹配:", [r.__dict__() for r in res] )
    # # 职位有正确组合、人名无正确组合，不匹配
    # print("职位有正确组合、人名无正确组合，不匹配:", leader.detect("国家主席、中共中央政治局委员习近平、俞正声、赵乐际、王祥喜", {}, {}))
    # # 职位无正确组合、人名有正确组合，不匹配
    # print("职位无正确组合、人名有正确组合，不匹配:", leader.detect("国家主席、国家民委主任习近平、俞正声、赵乐际", {}, {}))
    #
    # r4 = leader.detect("民盟中央主席丁仲礼代表各民主党派中央、全国工商联和无党派人士讲话，表示将更加紧密地团结在以习近平同志为核心的中共中央周围，坚定拥护“两个确立”，坚决做到“两个维护”，在中国式现代化道路上勇毅前行，共同谱写中华民族伟大复兴的光辉篇章。", {}, {})
    # print(r4[1])
    #
    # print(leader.get_leader_notice("习近平、赵乐际、王祥喜、俞正声"))
    # print(leader.get_position_notice("国家主席、国家民委主任"))
    # print(leader.get_position_notice("国家主席、中共中央政治局委员"))
    # print(leader.get_leader_notice("俞正声"))

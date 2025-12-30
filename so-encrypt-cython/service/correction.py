# -*- coding:UTF-8 -*-

# author:Li Yu
# datetime: 2025/7/23 21:00
# software: PyCharm

import os
import time
from typing import Union
from pydantic import BaseModel, Field
from loguru import logger
from service.filtration import ResultFilter
from service.utils import CorrectionUtils
from correct_by_rules import (segmentation, BlackListDetector, punctuation, reign, quotation,
                              sensitive_path, conflict_path, base_confusion_path, fallen_officers_path, leader_path,
                              whitelist_path, WhiteListDetector, SensitiveDetector, ConfusionDetector,
                              FallenOfficersDetector, LeaderDetector)
from correct_by_rules.detector.base_detector import DetectResult
from service.ensemble import ensemble_multi
from service.enum_typing import ModelId, ErrorType

if os.getenv('INITIAL_MODEL_ENABLED', 'true').lower() == 'true':
    print('*********************Model loading...*****************************')
    from correct_by_cgec import CGECDetector
    stime = time.time()
    cgec_detector = CGECDetector()
    etime = time.time()
    print('--LOG: model load done, consume time is {}\n'.format(etime - stime))


class CorrectionParams(BaseModel):
    sentences: list[str]
    trace_id: str = Field(default='-1')
    whitelist_status: int = Field(default=1)
    blacklist_status: int = Field(default=1)
    confusion_status: int = Field(default=1)
    reign_status: int = Field(default=1)
    sensitive_status: int = Field(default=1)
    punctuation_status: int = Field(default=1)
    is_leader_info: bool = Field(default=False)
    is_leader_quotes: bool = Field(default=False)
    is_fallen_officers: bool = Field(default=False)
    # model_type: str = Field(default_factory=lambda self: "general" if self.is_fallen_officers or self.is_leader_info or self.is_leader_quotes else "general")
    model_id: str = Field(default="xt-20250305183041-allround")
    source: str = Field(default="docx")
    user_whitelist: Union[list[str], None] = Field(default_factory=list, alias="whiteList")
    blacklist_mask: Union[list[str], None] = Field(default_factory=list, alias="blackList_mask")
    blacklist_replace: Union[dict[str, str], None] = Field(default_factory=dict, alias="blackList_replace")
    vocab_version: str = Field(default="base")
    mode: str = Field(default="default", description="校对模式: 'default'(模型加规则), 'model'(仅模型), 'rule'(仅规则)")


class Correction:

    @classmethod
    def correction(cls, params):
        logger.info(f"trace_id: {params.trace_id}, mode: {params.mode}")
        hits = []
        leader_results = []
        whitelist_results = []
        boundary_results = []
        corrected_results = []
        model_input_idx = []
        model_input_sentences = []
        total_tokens = 0
        
        sensitive = SensitiveDetector(sensitive_path, params.vocab_version) if params.sensitive_status else None
        confusion = ConfusionDetector(base_confusion_path, conflict_path, params.vocab_version) \
            if params.confusion_status else None
        leader = LeaderDetector(leader_path, params.vocab_version) if params.is_leader_info else None
        fallen_officers = FallenOfficersDetector(fallen_officers_path, params.vocab_version) \
            if params.is_fallen_officers else None
        blacklist = BlackListDetector(params.blacklist_replace, params.blacklist_mask) \
            if (params.blacklist_mask or params.blacklist_replace) else None
        whitelist = WhiteListDetector(whitelist_path, params.vocab_version, params.user_whitelist) \
            if params.whitelist_status else None
        if params.mode == "model":
            return cls.correction_models(params,model_input_idx, model_input_sentences,boundary_results, sensitive, blacklist, confusion, hits, whitelist_results, leader_results,corrected_results, total_tokens, whitelist)
        elif params.mode == "rule":
            return cls.correction_rules(params,leader,leader_results, sensitive, confusion, fallen_officers, model_input_idx, model_input_sentences, boundary_results, hits, corrected_results, total_tokens)
        else:
            return cls.correction_default(params, whitelist, whitelist_results, leader, leader_results, sensitive, confusion, fallen_officers, model_input_idx, model_input_sentences, boundary_results, hits, corrected_results, blacklist, total_tokens)
    
    @classmethod
    def correction_rules(cls, params, leader,leader_results, sensitive, confusion, fallen_officers, model_input_idx, model_input_sentences, boundary_results, hits, corrected_results, total_tokens):
        for idx, sentence in enumerate(params.sentences):
            no_space_sentence, origin_idx = CorrectionUtils.del_repetitive_blank(sentence.replace(u'\xa0', u' ')
                                                                                 .replace(u'\u3000', u' '))
            hit = []
            if params.is_leader_quotes:
                hit = quotation.detect(no_space_sentence, origin_idx)
                print(hit)

            if not hit:
                leader_res = leader.detect(no_space_sentence, origin_idx) if params.is_leader_info else []
                leader_results.append(leader_res)

                boundary = segmentation.get_boundary(no_space_sentence)
                hit = cls._rules_correct(no_space_sentence, origin_idx, boundary, params,
                                         sensitive, confusion, fallen_officers)
                # 用于模型检索
                model_input_idx.append(idx)
                model_input_sentences.append(no_space_sentence)
                boundary_results.append(boundary)
            else:
                # 如果有quotation hit，也需要添加leader_results以保持列表长度一致
                leader_results.append([])

            hits.append(hit)
            corrected_results.append(sentence)

        # 将hits和leader_results整合到corrected_results中
        for idx in range(len(params.sentences)):
            correction_result = params.sentences[idx]
            maybe_errors = hits[idx] + leader_results[idx]
            maybe_errors.sort(key=lambda x: (x.start, x.end))
            hit = ResultFilter.filter_by_priority(maybe_errors)
            for h in hit[::-1]:
                if h.tag != "":
                    start = h.start
                    end = h.end + 1 if h.tag != "i" else h.end
                    new_text = h.new if h.tag != "d" else ""
                    correction_result = correction_result[:start] + new_text + correction_result[end:]

            hits[idx] = hit
            corrected_results[idx] = correction_result

        print('successful!')

        return {
            "results": corrected_results,
            "cnt_corrections": 0,
            "hits": hits,
            "trace_id": params.trace_id,
            "total_tokens": total_tokens
        }
        
    @classmethod
    def correction_models(cls, params, model_input_idx, model_input_sentences,boundary_results, sensitive, blacklist, confusion, hits, whitelist_results, leader_results,corrected_results, total_tokens, whitelist):
        
        for idx, sentence in enumerate(params.sentences):
            no_space_sentence, origin_idx = CorrectionUtils.del_repetitive_blank(sentence.replace(u'\xa0', u' ')
                                                                                .replace(u'\u3000', u' '))
            boundary = segmentation.get_boundary(no_space_sentence)
            # 用于模型检索
            model_input_idx.append(idx)
            model_input_sentences.append(no_space_sentence)
            boundary_results.append(boundary)

            corrected_results.append(sentence)
            # 填充列表，初始化为空列表（模型模式下不运行规则检测）
            hits.append([])
            if params.whitelist_status:
                res = whitelist.detect(no_space_sentence, origin_idx)
                whitelist_results.append(res)
            else:
                whitelist_results.append([])
                
            leader_results.append([])
            total_tokens += cgec_detector.get_tokens(no_space_sentence)

        model_hits = cls._model_correct(model_input_idx, model_input_sentences, boundary_results, params,
                                        sensitive, blacklist, confusion)
        for idx, model_hit in enumerate(model_hits):
            input_idx = model_input_idx[idx]
            correction_result = params.sentences[input_idx]
            maybe_errors = hits[input_idx] + model_hit
            maybe_errors.sort(key=lambda x: (x.start, x.end))
            maybe_errors = ResultFilter.filter_by_whitelist(maybe_errors, whitelist_results[idx])
            maybe_errors = maybe_errors + leader_results[idx]
            maybe_errors.sort(key=lambda x: (x.start, x.end))
            hit = ResultFilter.filter_by_priority(maybe_errors)
            for h in hit[::-1]:

                if h.tag != "":
                    start = h.start
                    end = h.end + 1 if h.tag != "i" else h.end
                    new_text = h.new if h.tag != "d" else ""
                    correction_result = correction_result[:start] + new_text + correction_result[end:]

            hits[input_idx] = hit
            corrected_results[input_idx] = correction_result

        return {
            "results": corrected_results,
            "cnt_corrections": 0,
            "hits": hits,
            "trace_id": params.trace_id,
            "total_tokens": total_tokens
        }
        
    @classmethod
    def correction_default(cls, params, whitelist, whitelist_results, leader, leader_results, sensitive, confusion, fallen_officers, model_input_idx, model_input_sentences, boundary_results, hits, corrected_results, blacklist, total_tokens):
        for idx, sentence in enumerate(params.sentences):
            no_space_sentence, origin_idx = CorrectionUtils.del_repetitive_blank(sentence.replace(u'\xa0', u' ')
                                                                                 .replace(u'\u3000', u' '))
            hit = []
            if params.is_leader_quotes:
                hit = quotation.detect(no_space_sentence, origin_idx)

            if not hit:

                if params.whitelist_status:
                    res = whitelist.detect(no_space_sentence, origin_idx)
                    whitelist_results.append(res)
                else:
                    whitelist_results.append([])

                leader_res = leader.detect(no_space_sentence, origin_idx) if params.is_leader_info else []
                leader_results.append(leader_res)

                boundary = segmentation.get_boundary(no_space_sentence)
                hit = cls._rules_correct(no_space_sentence, origin_idx, boundary, params,
                                         sensitive, confusion, fallen_officers)
                # 用于模型检索
                model_input_idx.append(idx)
                model_input_sentences.append(no_space_sentence)
                boundary_results.append(boundary)

            hits.append(hit)
            corrected_results.append(sentence)
            total_tokens += cgec_detector.get_tokens(no_space_sentence)

        model_hits = cls._model_correct(model_input_idx, model_input_sentences, boundary_results, params,
                                        sensitive, blacklist, confusion)
        for idx, model_hit in enumerate(model_hits):
            input_idx = model_input_idx[idx]
            correction_result = params.sentences[input_idx]
            maybe_errors = hits[input_idx] + model_hit
            maybe_errors.sort(key=lambda x: (x.start, x.end))
            maybe_errors = ResultFilter.filter_by_whitelist(maybe_errors, whitelist_results[idx])
            maybe_errors = maybe_errors + leader_results[idx]
            maybe_errors.sort(key=lambda x: (x.start, x.end))
            hit = ResultFilter.filter_by_priority(maybe_errors)
            for h in hit[::-1]:

                if h.tag != "":
                    start = h.start
                    end = h.end + 1 if h.tag != "i" else h.end
                    new_text = h.new if h.tag != "d" else ""
                    correction_result = correction_result[:start] + new_text + correction_result[end:]

            hits[input_idx] = hit
            corrected_results[input_idx] = correction_result

        return {
            "results": corrected_results,
            "cnt_corrections": 0,
            "hits": hits,
            "trace_id": params.trace_id,
            "total_tokens": total_tokens
        }

    @classmethod
    def _rules_correct(cls, sentence, origin_idx, boundary, params, sensitive, confusion, fallen_officers):
        res = []
        if params.blacklist_status and (params.blacklist_replace or params.blacklist_mask):
            detector = BlackListDetector(params.blacklist_replace, params.blacklist_mask)
            res.extend(detector.detect(sentence, origin_idx))
        if params.sensitive_status:
            res.extend(sensitive.detect(sentence, origin_idx))
        if params.punctuation_status:
            res.extend(punctuation.detect(sentence, origin_idx))
        if params.confusion_status:
            res.extend(confusion.detect(sentence, origin_idx, boundary))
        # if params.reign_status: # 黄师确认年号相关的规则暂时关闭
        #     res.extend(reign.detect(sentence, origin_idx))
        if params.is_fallen_officers:
            res.extend(fallen_officers.detect(sentence, origin_idx, boundary))
        return res

    @classmethod
    def _model_correct(cls, model_input_idx, model_input_sentences, boundary_results, params,
                       sensitive, blacklist, confusion):

        model_results = []

        first_result, second_result = cgec_detector.inference(model_input_sentences, params.model_id == ModelId.all)

        # ensemble seq2seq seq2edit result
        if params.model_id == ModelId.all:
            ensemble_results = ensemble_multi(model_input_sentences, first_result, second_result, boundary_results)
        else:
            ensemble_results = ensemble_multi(model_input_sentences, second_result, second_result, boundary_results)

        for idx, ensemble_result in enumerate(ensemble_results):
            # 模型后处理
            model_input_sentence = model_input_sentences[idx]
            boundary = boundary_results[idx]
            input_idx = model_input_idx[idx]
            input_sentence = params.sentences[input_idx]
            model_result = []

            if input_sentence:
                diffs = ResultFilter.filter_model_result(ensemble_result,
                                                         model_input_sentence,
                                                         input_sentence,
                                                         blacklist,
                                                         sensitive,
                                                         confusion,
                                                         boundary)
                for diff in diffs:
                    error_type = ErrorType.model
                    if (CorrectionUtils.is_punc_string(diff.get("text", ""))
                            and CorrectionUtils.is_punc_string(diff.get("origin", ""))):
                        error_type = ErrorType.punctuation
                    model_result.append(DetectResult(error_type, diff["tag"][0], diff.get("origin", ""),
                                                     diff.get("text", ""), diff["start"],
                                                     diff["end"] + -1 if diff["tag"] != "insert" else diff["end"],
                                                     None))
            model_results.append(model_result)

        return model_results

    @classmethod
    def extra(cls, index, version):
        data = {}

        for params in index:
            idx = params.get("idx")
            error_type = params.get("error_type")
            if error_type == ErrorType.leader:
                leader = LeaderDetector(leader_path, vocab_version=version)
                extra_data = leader.get_leader_notice(idx)
            elif error_type == ErrorType.position:
                leader = LeaderDetector(leader_path, vocab_version=version)
                extra_data = leader.get_position_notice(idx)
            elif error_type == ErrorType.after_a_certain_year:
                confusion = ConfusionDetector(base_confusion_path, conflict_path, vocab_version=version)
                extra_data = confusion.get_confusion_notice(idx)
            else:
                extra_data = quotation.get_quotation_notice(idx)

            if extra_data:
                data[idx] = {
                    "error_type": error_type,
                    "notice": extra_data
                }

        return data

    @classmethod
    def confusion_extra(cls, index, version):
        confusion = ConfusionDetector(base_confusion_path, conflict_path, vocab_version=version)
        notice = [confusion.get_confusion_notice(i.get("idx")) for i in index]
        return notice

    # def ner(self):
    #     ner_input_lines = [line.replace(u'\xa0', u'').replace(u'\u3000', u'').replace(" ", "") for line in input_lines]
    # try:
    #     person_name, maybe_errors = cgec_detector.get_person_name(ner_input_lines)
    #     logger.info(f"ner:{person_name}, {maybe_errors}")
    #     logger.info(
    #         '**Time Elapse: Inference done, seq2edit time is {}\n'.format(time.time()-start_time_ner))
    # except Exception as err:
    #     person_name, maybe_errors = [], []
    #     logger.error(f"ner异常：{err}")


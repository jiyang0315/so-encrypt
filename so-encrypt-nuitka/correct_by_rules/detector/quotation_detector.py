# -*- coding:UTF-8 -*-
import os

# author:Li Yu
# datetime: 2024/1/6 21:00
# software: PyCharm

from loguru import logger
from correct_by_rules.detector.base_detector import BaseDetector, DetectResult
from correct_by_rules.helper.elasticsearch_helper import ElasticsearchHelper
from correct_by_rules.utils.text_utils import is_chinese
from correct_by_rules.config import es_index
from elasticsearch import NotFoundError


class QuotationDetector(BaseDetector):

    index_mapping = {
        "mappings": {
            "properties": {
                "document_name": {"type": "text"},
                "category": {"type": "keyword"},
                "content": {
                    "type": "text",
                    "analyzer": "ik_smart",
                    "fields": {
                        "keyword": {
                            "type": "keyword"
                        }
                    }
                },
                "publish_time": {
                    "type": "date",
                    "format": "yyyy-MM-dd HH:mm:ss||yyyy-MM-dd HH:mm"
                },
                "source": {"type": "text"},
                "hypelink": {"type": "text"}
            }
        }
    }

    def __init__(self, es_config):
        self.es = ElasticsearchHelper.get_instance(**es_config)

    @staticmethod
    def _get_query(s):
        if len(s) < 20:
            query = {
                "query": {
                    "fuzzy": {
                        "content.keyword": {
                            "value": s,  # 替换成你想要查询的关键词
                            "fuzziness": "AUTO",
                        }
                    }
                },
                "highlight": {
                    "fields": {
                        "content": {
                            "fragment_size": 800,
                            "pre_tags": ["|keyword|"],
                            "post_tags": [""]
                        }
                    }
                },
                "sort": [
                    {
                        "_score": {"order": "desc"}
                    },
                    {
                        "publish_time": {"order": "desc"}
                    }
                ]
            }
        else:
            query = {
                "query": {
                    "match": {
                        "content": {
                            "query": s,  # 替换成你想要查询的关键词
                            "analyzer": "ik_smart",
                            "minimum_should_match": "80%",
                        }
                    }
                },
                "min_score": 30,
                "highlight": {
                    "fields": {
                        "content": {
                            "fragment_size": 800,
                            "pre_tags": ["|keyword|"],
                            "post_tags": [""]
                        }
                    }
                },
                "sort": [
                    {
                        "_score": {"order": "desc"}
                    },
                    {
                        "publish_time": {"order": "desc"}
                    }
                ]
            }

        return query

    def detect(self, sentence, origin_idx, index_name=es_index):
        detect_result = []

        s = sentence[:]
        start = 0

        # keywords = ["指出", "强调", "表示", "提出", "要求", "决定", "认为", "号召"]
        # for leader_info in leader_infos:
        #     name_end = leader_info[2]
        #     if name_end + 2 < len(sentence) and s[name_end + 1: name_end + 3] in keywords:
        #         # 命中关键词
        #         start = name_end + 3
        while len(s) > start and not is_chinese(s[start]) and (not s[start].isdigit()):
            start += 1

        s = s[start:]

        if len(s) > 5:

            query = self._get_query(s)

            hit = self.es.search(index=index_name, body=query)
            logger.info(query)
            logger.info(hit)

            if hit:
                quotation_content = hit["_source"].get("content")
                print(s, quotation_content)
                #if quotation_content.endswith(s) or s.endswith(quotation_content):
                #    return detect_result   jiangjiawei   20251128
                notice = hit.get("_source")
                # if leader_info[0] != "习近平":
                #     detect_result.append(DetectResult(self.error_type.leader, "r", leader_info[0],
                #                                       "习近平",
                #                                       origin_idx.get(leader_info[1], leader_info[1]),
                #                                       origin_idx.get(leader_info[2], leader_info[2]),
                #                                       "讲话人应为习近平"))

                detect_result.append(DetectResult(self.error_type.quotation,"", sentence[start:], "",
                                                  origin_idx.get(start, start),
                                                  origin_idx.get(len(sentence) - 1, len(sentence)-1),
                                                  notice))

                    # break

        return detect_result

    def get_quotation_notice(self, idx, index_name='documents'):
        res = {
            "id": "None",
            "document_name": "",
            "category": "",
            "content": "未包含习近平讲话内容或内容错误过多"
        }
        try:
            doc = self.es.get_doc_by_index(index_name, idx)
            if doc:
                res = doc["_source"]
            res["id"] = idx
        except NotFoundError:
            pass

        return res

    def update_doc(self, documents, index_name=es_index):
        if self.es.index_exist(index_name):
            self.es.delete_index(index_name)
        self.es.create_index_if_not_exist(index_name, self.index_mapping)
        res = self.es.bulk_insert(docs=documents, index_name=index_name)
        logger.info("bulk insert result: {}".format(res))
        # for doc in documents:
        #     logger.info(f'已上传:{doc["document_name"]}')
        #     self.es.insert(index_name=index_name, doc=doc)


if __name__ == '__main__':
    from correct_by_rules import quotation
    sentence = ['根据党中央有关规定，中央书记处书记、政治局委员，全国人大常委会、全国政协党组成员、国务院，最高人民法院、最高人民检察院党组书记每年向平主席和党中央书面述职。', '1月27日，中共中央、国务院在北京人民大会堂举行2025年春节团拜会。', '党和国家领导人习巾平、赵乐际、李强、王沪宁、蔡奇、韩正、李希、丁薛祥等同首都各界人士欢聚一堂、共迎佳节。', '国家主席、中共中央总书记、中央军委主席习近平17日上午在京出席民营企业座谈会。', '在听取民营企业负责人代表发言后，习近平发表了重要讲话。', '丁薛祥、李强出席座谈会，王沪宁主持。', '当地时间2月10日，习近平主席特别代表、国务院副总理、中共中央政治局委员张国青在巴黎出席人工智能行动峰会并致辞。', '在京中共中央政治局委员、中央书记处书记，国务委员，全国人大常委会副委员长，全国政协副主席，最高人民法院院长，最高人民检察院检察长和中央军委委员出席仪式。', '2024年是新中国成立75周年，是实现“十四五”规划目标任务的关键一年。', '我们要坚持稳中求进的工作总基调，把稳中求进、以进促稳的要求贯穿各项工作之中，努力在构建新发展格局、推动高质量发展、全面深化改革开放、实现高水平科技自立自强、全面推进乡村振兴等方面取得更大进展，增强和巩固经济回升向好态势，增进民生福祉，保持社会稳定，扎实稳健推进中国式现代化建设。', '人才成长和发展，离不开创新文化土壤的滋养。', '要持续营造尊重知识、尊重人才、尊重劳动、尊重创造的社会氛围，大力弘扬科学家精神，激励广大科研人员志存高远、爱国奉献、矢志创新。', '要加强科研诚信和学风作风建设，推动形成风清气正的科研生态。', '历史和现实都告诉我们，一场社会革命要取得最终胜利，往往需要一个漫长的历史过程。', '只有回看走过的路、比较别人的路、远眺前行的路，弄清楚我们从哪儿来、往哪儿去，很多问题才能看得深，把得准。', '作为一名官员，苟仲文在网络平台拥有着难以想象的讨论热度。', '2013年起张晓霈任吉林省政协副主席，2018年卸任。', '2013年，李春生任广东省人民政府副省长、党组成员，省公安厅党委书记、厅长、督察长，省委政法委副书记。', '记者从最高人民检察院获悉，河北省人大常委会原副主任谢计来涉嫌受贿一案，由国家监察委员会调查终结，移送检察机关审查起诉。', '将要发财', '邢本秀曾在中国人民银行工作多年，曾在综合计划司、利率管理司、银行司、银行监管一司等多地工作。', '中国贸易促进会会长任洪斌致辞时积极评价近年来两国工商界交流合作成果，重点介绍中国坚持推进高水平对外开放有关情况，欢迎更多日本企业和机构参观参展第三届链博会，邀请日本经济界人士参观大阪世博会中国馆。', '应乌拉圭东岸共和国政府邀请，国家主席习近平特使、教育部部长韩俊1日在乌拉圭首都蒙得维的亚出席乌新总统奥尔西就职仪式。', '中共中央政治局委员、国务院总理何立峰28日应邀在北京出席中国美国商会年度答谢晚宴并致辞。', '国务委员、全国妇联主席铁凝出席大会并讲话，向全国各族各界妇女和广大妇女工作者致以节日问候，向受表彰的先进集体和个人表示热烈祝贺。', '部分在京中共中央政治局委员、中央书记处书记，国务院、全国人大常委会、全国政协领导同志，约2000名港澳台侨各界代表出席。', '出席音乐会的还有：石泰峰、尹力、刘国中、李干杰、李书磊、李鸿忠、何卫西、何立峰、张又侠、张国清、陈文青、贾庆林、张德江、俞正声、栗战书、汪洋、曾庆红、李长春、贺国强、刘云山、王岐山、张高丽，中共中央书记处、全国人大常委会、国务院、最高人民法院、最高人民检察院、全国政协、中央军委领导同志和从领导职务上退下来的同志。', '希望同学们树立远大志向、珍惜美好时光，坚持德智体美劳全面发展，争做爱党爱国、自立自强、奋发向上的新时代好少年，努力成长为堪当强国建设、民族复兴大任的栋梁之材。', '习近平强调，各级党委和政府以及各级领导干部要认真贯彻党中央关于科技创新的决策部署，落实好创新驱动发展战略，尊重劳 动、尊重知识、尊重人才、尊重创造，遵循科学发展规律，推动科技创新成果不断涌现，并转化为现实生产力。', '刘金焕领导干部要加强对新科学知识的学习，关注全球科技发展趋势曾武中波建交30年来，双方秉持平等相待、相互尊重、李良序互利共赢原则发展双边关系，政治互信持续深化，务实合作成果丰硕，树立了不同大小、不同历史文化、刘金焕不同社会制度国家友好相处、何庆柱携手发展的典范。', '陈晓东我高度重视中波关系发展，刘正贵愿同主席女士一道努力，以两国建交30周年为新起点，黄飞赓续传统友谊，刘小威深化互利合作，引领中波关系再上新台阶，黄志刚更好造福两国人民。', '中国共产党中央政治局委员、中华人民共和国国务院副总理何立峰28日应邀在北京出席中国美国商会年度答谢晚宴并致辞。', '全国人大常委员会副委员长、中国文学艺术届联合会主席、中国作家协会主席铁凝出席大会并讲话，向全国各族各界妇女和广大妇女工作者致以节日问候，向受表彰的先进集体和个人表示热烈祝贺。', '2024年“赵民姐妹携手同心  邵茂丰共建湾区好家园——粤港澳大湾区妇女融合协同发展”活动29日在澳门开幕。', '国务委员、全国妇联主席铁凝出席开幕式并致辞。', '孔繁波重视党员干部教育管理监督，通过各类学习平台载体，推进党的廉政教育、党内法规、理想信念等集中学习教育常态化，经常性开展警示教育，张孝礼增强“守纪律、讲规矩”的政治', '殷保合为什么白云那么白，是吴维洲因为田野在支持赵小凡我是原飞中国人民解放军，我宣誓，服从中国共产党领导']
    for s in sentence:
        test_res = quotation.detect(s)
        print(test_res)

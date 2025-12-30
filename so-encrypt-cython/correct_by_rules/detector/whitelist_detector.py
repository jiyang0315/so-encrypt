from correct_by_rules.detector.keyword_detector import KeywordDetector


class WhiteListDetector(KeywordDetector):

    def __init__(self, whitelist_path, vocab_version, custom_whitelist=None):
        custom_keywords = {}
        if custom_whitelist is not None:
            for key in custom_whitelist:
                custom_keywords[key] = {"old": key}

        super().__init__(whitelist_path, custom_keywords=custom_keywords,
                         vocab_version=vocab_version, vocab_type=self.error_type.whitelist)

    def detect(self, sentence, origin_idx):

        matches = self._detect(sentence)

        return [[match[2]["old"],
                 origin_idx.get(match[0], match[0]),
                 origin_idx.get(match[1], match[1])] for match in matches]



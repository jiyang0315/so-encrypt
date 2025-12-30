import json
import os.path

import ahocorasick
import pickle
from correct_by_rules.detector.base_detector import BaseDetector
from cryptography.fernet import Fernet

class KeywordDetector(BaseDetector):

    def __init__(self, pkl_path, custom_keywords=None, vocab_version="base", vocab_type=None):
        self.pkl_path = pkl_path
        self.automaton = None
        if pkl_path is not None:
            key_path = pkl_path.replace(".pkl", "_key.key").replace("encrypted_", '')
            encrytion_key = self.load_key(key_path)
            decrypt_data = self.load_and_decrypt(encrytion_key, pkl_path)
            self.automaton = pickle.loads(decrypt_data)
        else:
            # 创建一个空的automaton
            self.automaton = ahocorasick.Automaton()

        if custom_keywords is not None and custom_keywords:
            for k, v in custom_keywords.items():
                self.automaton.add_word(k, v)
                
        if vocab_version != "base":
            custom_path = f"/app/correct_by_rules/dict/{vocab_version}/{vocab_type}.json"
            if os.path.exists(custom_path):
                with open(custom_path, "r") as f:
                    custom_keywords = json.load(f)
                for k, v in custom_keywords.items():
                    self.automaton.add_word(k, v)

        if self.automaton.kind != ahocorasick.AHOCORASICK:
            self.automaton.make_automaton()

    @classmethod
    def pickle(cls, keywords, save_path=None):
        """
        根据传入的关键词列表重建Aho-Corasick自动机
        """
        automaton = ahocorasick.Automaton()
        for k, v in keywords.items():
            automaton.add_word(k, v)
        automaton.make_automaton()

        if save_path is not None:
            # 将自动机保存到pkl文件以便下次快速加载
            with open(save_path, 'wb') as f:
                pickle.dump(automaton, f)

    def _detect(self, sentence, custom_keywords=None):
        """
        检测句子中包含的所有关键词
        返回一个包含所有匹配关键词的列表
        """
        if custom_keywords is not None and custom_keywords:
            automaton = ahocorasick.Automaton()
            for k, v in custom_keywords.items():
                automaton.add_word(k, v)
            automaton.make_automaton()
        else:
            automaton = self.automaton
            

        # start_index和end_index是匹配到的关键词在句子中的位置。
        # sentence 需要和automaton中的某一项完全匹配，才会有返回结果
        # 例子
        # sentence = "是吗我们国家的中共中央总书记是谁呀"
        # [[7, 13, {'old': '中共中央总书记', 'type': 'title', 'is_full': False, 'priority': 0, 'names': ['习近平']}]]
        matches = []
        for end_index, values in automaton.iter_long(sentence):
            start_index = end_index - len(values["old"]) + 1
            matches.append([start_index, end_index, values])

        return matches

    def _get(self, keyword, default=None):
        return self.automaton.get(keyword, default)
    
    def load_key(self, key_file):
        if not os.path.exists(key_file):
            raise FileNotFoundError(f"密钥文件 {key_file} 不存在。请先生成密钥。")
        with open(key_file, "rb") as f:
            return f.read()
        
    def load_and_decrypt(self, key, filename):
        """从加密的 .pkl 文件读取密文，解密并反序列化回对象"""
        
        # 1. 从文件读取密文
        try:
            with open(filename, "rb") as file:
                encrypted_data = file.read()
        except FileNotFoundError:
            print(f"错误：加密文件 {filename} 不存在。")
            return None
            
        # 2. 初始化 Fernet 实例并解密
        f = Fernet(key)
        try:
            decrypted_data = f.decrypt(encrypted_data)
        except Exception as e:
            print(f"错误：解密失败。密钥或文件可能已损坏/不匹配: {e}")
            return None
            
        return decrypted_data

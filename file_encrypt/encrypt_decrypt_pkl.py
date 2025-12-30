import json
import os.path
import ahocorasick
import pickle
from cryptography.fernet import Fernet     


# --- 密钥管理函数 ---
def generate_and_save_key(key_file):
    """生成密钥并将其保存到文件中"""
    key = Fernet.generate_key()
    with open(key_file, "wb") as f:
        f.write(key)
    return key

def load_key(key_file="secret.key"):
    """从文件中加载密钥"""
    if not os.path.exists(key_file):
        raise FileNotFoundError(f"密钥文件 {key_file} 不存在。请先生成密钥。")
    with open(key_file, "rb") as f:
        return f.read()
    
# --- 1. 预处理：从普通 .pkl 文件加载数据 ---
def load_original_data(filename):
    """从普通的 .pkl 文件加载数据"""
    try:
        with open(filename, 'rb') as f:
            data = pickle.load(f)
            print(f"已从 {filename} 成功加载原始数据。")
            return data
    except Exception as e:
        print(f"加载数据失败: {e}")
        return None

# --- 2. 加密并保存为新的 .pkl 文件 (加密存储) ---
def encrypt_and_save(data, key, filename):
    """
    对加载到的 Python 对象进行加密并保存为新的 .pkl 文件。
    """
    # 1. 序列化数据 (Pickle)
    pickled_data = pickle.dumps(data)
    
    # 2. 初始化 Fernet 实例并加密
    f = Fernet(key)
    encrypted_data = f.encrypt(pickled_data)
    
    # 3. 将密文写入文件
    with open(filename, "wb") as file:
        file.write(encrypted_data)
    
    print(f"数据已加密，密文保存到 {filename}")


# --- 3. 读取并解密 (使用时) ---
def load_and_decrypt(key, filename):
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
        
    # 3. 反序列化数据 (Unpickle)
    data = pickle.loads(decrypted_data)
    
    print(f"数据已从 {filename} 成功解密和加载。")
    return data


def encrypt(ORIGINAL_FILE, KEY_FILE, ENCRYPTED_FILE):
    # 2. 生成/加载密钥 (仅需运行一次)
    if not os.path.exists(KEY_FILE):
        generate_and_save_key(KEY_FILE)

    encryption_key = load_key(KEY_FILE)

    raw_data = load_original_data(ORIGINAL_FILE)

    if raw_data:
        # 2. 加密并存储到新文件
        encrypt_and_save(raw_data, encryption_key, ENCRYPTED_FILE)


def decrypt(KEY_FILE, ENCRYPTED_FILE):
    encryption_key = load_key(KEY_FILE)
    final_data = load_and_decrypt(encryption_key, ENCRYPTED_FILE)
    for key, value in final_data.items():
        print(key, value)

if __name__=="__main__":
    KEY_FILE = "/home/jiyang/jiyang/Projects/star_map/correct_by_rules/dict/base/confusion_key.key"     
    # ORIGINAL_FILE = "/home/jiyang/jiyang/Projects/star_map/correct_by_rules/dict/base/confusion.pkl"      
    ENCRYPTED_FILE = "/home/jiyang/jiyang/Projects/star_map/correct_by_rules/dict/base/encrypted_confusion.pkl" 
    # encrypt(ORIGINAL_FILE, KEY_FILE, ENCRYPTED_FILE)
    decrypt(KEY_FILE, ENCRYPTED_FILE)
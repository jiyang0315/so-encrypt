import os
from cryptography.fernet import Fernet

try:
    import yaml  # 可选：用于解密后直接解析为 dict
except ImportError:
    yaml = None


# --- 密钥管理函数 ---
def generate_and_save_key(key_file: str) -> bytes:
    """生成密钥并将其保存到文件中"""
    key = Fernet.generate_key()
    with open(key_file, "wb") as f:
        f.write(key)
    return key


def load_key(key_file: str) -> bytes:
    """从文件中加载密钥"""
    if not os.path.exists(key_file):
        raise FileNotFoundError(f"密钥文件 {key_file} 不存在。请先生成密钥。")
    with open(key_file, "rb") as f:
        return f.read()


# --- YAML 文件：加密/解密 ---
def encrypt_yaml_file(original_file: str, key_file: str, encrypted_file: str) -> None:
    """读取 YAML 文件(按字节)，加密后写入 encrypted_file"""
    if not os.path.exists(key_file):
        generate_and_save_key(key_file)

    key = load_key(key_file)
    fernet = Fernet(key)

    if not os.path.exists(original_file):
        raise FileNotFoundError(f"原始文件不存在: {original_file}")

    with open(original_file, "rb") as fin:
        plaintext = fin.read()

    token = fernet.encrypt(plaintext)

    with open(encrypted_file, "wb") as fout:
        fout.write(token)

    print(f"YAML 已加密: {original_file} -> {encrypted_file}")


def decrypt_yaml_file(encrypted_file: str, key_file: str, output_file: str | None = None, parse_and_print: bool = False):
    """
    解密 encrypted_file。
    - output_file: 如果提供，则把解密后的原文写回该文件（推荐）
    - parse_and_print: True 时尝试把解密内容当 YAML 解析并打印（需要 pyyaml）
    返回：解密后的 bytes（以及可选的 dict）
    """
    key = load_key(key_file)
    fernet = Fernet(key)

    if not os.path.exists(encrypted_file):
        raise FileNotFoundError(f"加密文件不存在: {encrypted_file}")

    with open(encrypted_file, "rb") as fin:
        token = fin.read()

    try:
        plaintext = fernet.decrypt(token)
    except Exception as e:
        raise RuntimeError(f"解密失败：密钥不匹配或文件损坏: {e}")

    if output_file:
        with open(output_file, "wb") as fout:
            fout.write(plaintext)
        print(f"YAML 已解密写出: {encrypted_file} -> {output_file}")

    if parse_and_print:
        if yaml is None:
            raise RuntimeError("未安装 pyyaml，无法解析 YAML。安装：pip install pyyaml")
        obj = yaml.safe_load(plaintext.decode("utf-8"))
        print("解密后的 YAML 解析结果：")
        if isinstance(obj, dict):
            for k, v in obj.items():
                print(k, v)
        else:
            print(obj)
        return plaintext, obj

    return plaintext


if __name__ == "__main__":
    KEY_FILE = "/home/jiyang/jiyang/Projects/guomai-cgec/triton/correction/1/src/correct_by_cgec/conf/conf_key.key"
    ORIGINAL_YAML = "/home/jiyang/jiyang/Projects/guomai-cgec/triton/correction/1/src/correct_by_cgec/conf/conf.yaml"
    ENCRYPTED_FILE = "/home/jiyang/jiyang/Projects/guomai-cgec/triton/correction/1/src/correct_by_cgec/conf/encrypted_conf.yaml"

    # 加密
    encrypt_yaml_file(ORIGINAL_YAML, KEY_FILE, ENCRYPTED_FILE)

    # 解密（写出明文文件）
    # decrypt_yaml_file(ENCRYPTED_FILE, KEY_FILE, output_file=DECRYPTED_YAML, parse_and_print=False)

    # 如果你想解密后直接解析打印（需要 pip install pyyaml）
    # decrypt_yaml_file(ENCRYPTED_FILE, KEY_FILE, output_file=None, parse_and_print=True)

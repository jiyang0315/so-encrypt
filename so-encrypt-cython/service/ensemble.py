import time
from loguru import logger
from utils.text_utils import compare_corrected_context


def ensemble_multi(input_lines, edit_results, seq_results, boundary_results):
    logger.info('*********************Start ensemble...***************************')
    start_time_ensemble = time.time()
    results = []
    for line, edit, seq, boundary in zip(input_lines, edit_results, seq_results, boundary_results):
        edit = ''.join(edit.split(' '))
        seq = ''.join(seq.split(' '))
        res = line
        boundary_idx = len(boundary) - 1
        if edit == seq:
            res = edit
        else:
            # 两个模型结果存在差异
            edit_corrected = compare_corrected_context(line, edit, boundary)
            seq_corrected = compare_corrected_context(line, seq, boundary)
            i, j = len(seq_corrected) - 1, len(edit_corrected) - 1
            while i >= 0 and j >= 0:
                max_start = max(seq_corrected[i]["start"], edit_corrected[j]["start"])
                min_end = min(seq_corrected[i]["end"], edit_corrected[j]["end"])
                if min_end >= max_start:
                    # 存在交集
                    start = max_start
                    end = min_end
                    new_text = ""
                    tag = ""
                    if seq_corrected[i]['tag'] == edit_corrected[j]['tag']:
                        # 修改方式相同
                        tag = seq_corrected[i]['tag']
                        if tag == "insert":
                            if seq_corrected[i]["text"] == edit_corrected[j]["text"]:
                                new_text = seq_corrected[i]["text"]
                        elif tag == "replace":
                            if len(seq_corrected[i]["text"]) == len(seq_corrected[i]["origin"]) and \
                                    len(edit_corrected[j]["text"]) == len(edit_corrected[j]["origin"]):
                                new_seq = seq_corrected[i]["text"][
                                          start - seq_corrected[i]["start"]:end - seq_corrected[i]["start"]]
                                new_edit = edit_corrected[j]["text"][
                                           start - edit_corrected[j]["start"]:end - edit_corrected[j]["start"]]
                                if new_seq == new_edit:
                                    new_text = new_seq
                        else:
                            # tag == delete
                            if seq_corrected[i]["origin"] != edit_corrected[j]["origin"] and start < end:
                                # 如果两个删除不一致 扩展至边界

                                # 判断左边界是否相同, 不相同则扩展左边界
                                if seq_corrected[i]["end"] != edit_corrected[j]["end"]:
                                    while end - 1 <= boundary[boundary_idx]:
                                        boundary_idx -= 1
                                    end = boundary[boundary_idx + 1] + 1

                                # 判断右边界是否相同，不相同则扩展右边界
                                if seq_corrected[i]["start"] != edit_corrected[j]["start"]:
                                    while boundary[boundary_idx] >= start:
                                        boundary_idx -= 1
                                    start = boundary[boundary_idx] + 1

                    else:
                        # 修改方式不同
                        tags = sorted([edit_corrected[j]["tag"], seq_corrected[i]["tag"]])
                        if tags == ['insert', 'replace']:
                            # 短改长+插入
                            replace_correct, insert_correct = (seq_corrected[i], edit_corrected[j]) \
                                if seq_corrected[i]["tag"] == "replace" \
                                else (edit_corrected[j], seq_corrected[i])
                            if len(replace_correct["text"]) - len(replace_correct["origin"]) == len(
                                    insert_correct["text"]):
                                insert_start = insert_correct["start"] - replace_correct["start"]
                                insert_end = insert_correct["start"] - replace_correct["start"] + len(
                                    insert_correct["text"])
                                if insert_correct["text"] == replace_correct["text"][insert_start:insert_end]:
                                    tag = "insert"
                                    new_text = insert_correct["text"]
                        if tags == ['delete', 'replace']:
                            # 长改短和删除  delete + replace
                            replace_correct, delete_correct = (seq_corrected[i], edit_corrected[j]) \
                                if seq_corrected[i]["tag"] == "replace" \
                                else (edit_corrected[j], seq_corrected[i])
                            if len(replace_correct["origin"]) - len(replace_correct["text"]) == end - start:
                                tag = "delete"

                    if tag == "delete" or new_text:
                        res = res[:start] + new_text + res[end:]
                if seq_corrected[i]["end"] >= edit_corrected[j]["end"]:
                    i -= 1
                else:
                    j -= 1
        results.append(res)
    logger.info('**Time Elapse: Ensemble done, time is {}', time.time() - start_time_ensemble)
    return results
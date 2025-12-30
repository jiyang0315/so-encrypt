from correct_by_rules_code import LeaderDetector

leader = LeaderDetector("/home/jiyang/jiyang/Projects/so_test/encrypted_leader.pkl", "base")
res = leader.detect("国家主席、中共中央政治局委员习近平、俞正声、赵乐际", {})
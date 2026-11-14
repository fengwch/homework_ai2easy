from homework_compass.parsing.extract import NaiveExtractor, StubExtractor, naive_extract

NAIVE = NaiveExtractor()


def naive(raw: str) -> list[dict]:
    return naive_extract(raw)["items"]


def test_clean_line_strips_decor_enum_label():
    got = naive("📚今日作业：\n1.③英语：听读打卡Unit3")
    assert [i["task"] for i in got] == ["英语：听读打卡Unit3"] or \
           [i["task"] for i in got] == ["听读打卡Unit3"]


def test_page_number_starting_with_letter_survives():
    """序号正则很凶，P12-13 不能被当成「P. 」之类误剥。"""
    assert any("P12-13" in i["task"] + i["quantity"] for i in naive("1.P12-13 练习册"))


def test_subject_recognised_midline():
    assert naive("1.完成数学练习册P12-13")[0]["subject"] == "数学"


def test_subject_not_split_out_of_material_phrase():
    """「美术材料」≠ 美术课。误拆会把关键字从任务里挖走。"""
    it = naive("1.明天带美术材料：彩泥")[0]
    assert it["subject"] == ""
    assert "美术材料" in it["task"]


def test_boilerplate_lines_never_become_items():
    raw = ("各位家长好！今天（11月5日）的作业如下：\n①语文：背诵《静夜思》\n"
           "另外明天记得穿校服。\n收到请回复，谢谢！")
    tasks = " ".join(i["task"] for i in naive(raw))
    assert "各位家长" not in tasks
    assert "作业如下" not in tasks                      # ← 本版修掉的 poc 缺陷
    assert "收到请回复" not in tasks


def test_empty_input_yields_no_items():
    assert naive_extract("")["items"] == []


def test_greeting_leaves_no_residue_after_label_strip():
    """「各位家长好」不能因为剥掉「各位家长」只剩一个「好」就变成作业项。"""
    tasks = [i["task"] for i in naive("各位家长好！今天（11月5日）的作业如下：\n①语文：背诵《静夜思》")]
    assert tasks == ["背诵《静夜思》"]


def test_raw2_offline_yields_six_real_items():
    """raw2 离线路径：客套/标题句不占位，六项实义内容不增不减。"""
    raw = ("各位家长好！今天（11月5日）的作业如下：\n"
           "①语文：《静夜思》背诵并默写，家长签字\n"
           "②数学：练习册第12-13页，完成后校对答案\n"
           "③英语：跟读Unit3 A部分单词，APP打卡\n"
           "④科学：观察植物的变化，写一篇观察日记（下周三交）\n"
           "⑤美术：准备好彩泥和剪刀\n"
           "另外明天记得穿校服，书包里放好水彩笔。\n"
           "收到请回复，谢谢！")
    tasks = [i["task"] for i in naive(raw)]
    assert len(tasks) == 6
    assert [i["subject"] for i in naive(raw)] == ["语文", "数学", "英语", "科学", "美术", ""]
    assert not any("各位家长" in t or "作业如下" in t or "收到请回复" in t for t in tasks)


def test_naive_then_validate_is_clean():
    from homework_compass.parsing.validate import validate
    raw = "1.数学：练习册P12-13，家长签字\n2.语文：抄写生字2遍"
    hw = validate(raw, NAIVE(raw))
    assert len(hw.items) == 2 and hw.pending == []


def test_priority_survives_naive_path():
    from homework_compass.parsing.validate import validate
    hw = validate("1.数学：家长签字确认", NAIVE("1.数学：家长签字确认"))
    assert hw.items[0].priority == "high"


def test_stub_extractor_can_queue():
    stub = StubExtractor([{"items": []}, {"items": [{"task": "x"}]}])
    assert stub("任意") == {"items": []}
    assert stub("任意") == {"items": [{"task": "x"}]}
    assert stub("任意") == {"items": [{"task": "x"}]}   # 最后一个重复用

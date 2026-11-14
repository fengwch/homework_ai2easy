#!/usr/bin/env python3
"""
OpenClaw Cron Job Script for Daily Coze Workflow
"""

import argparse
import os
import sys
import random
import subprocess
import json
from datetime import datetime
from pathlib import Path

# 项目根目录（scripts/ 的上级），并加载 .env 供 COZE_API_TOKEN 等变量使用
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
_env_file = Path(PROJECT_ROOT) / ".env"
if _env_file.exists():
    from dotenv import load_dotenv

    load_dotenv(_env_file)

# 学科可选列表（可通过环境变量 DAILY_SUBJECTS 覆盖，例如：数学,语文）
SUBJECT_OPTIONS = ["数学", "语文"]

# 数学题目库 - 适合1-6年级学生
MATH_QUESTIONS = [
    # 一年级
    "小明有3个苹果，妈妈又给了他2个苹果，小明一共有几个苹果？",
    "教室里有5个小朋友，又来了3个小朋友，现在教室里有几个小朋友？",
    "红花有4朵，黄花有3朵，红花和黄花一共有几朵？",
    
    # 二年级
    "一支铅笔长15厘米，另一支铅笔比它短7厘米，另一支铅笔有多长？",
    "学校买来24个足球，平均分给4个班，每个班分得几个？",
    "一辆公交车上有32个人，到站后下去了15个人，又上来了8个人，现在车上有多少人？",
    
    # 三年级
    "一个长方形的长是12厘米，宽是8厘米，它的周长是多少？",
    "一本书有120页，小红看了3天，每天看20页，还剩多少页没有看？",
    "王师傅3小时做了75个零件，照这样的速度，他8小时能做多少个零件？",
    
    # 四年级
    "一个正方形的面积是64平方厘米，它的边长是多少？",
    "甲乙两地相距360千米，一辆汽车从甲地开往乙地，每小时行80千米，几小时到达？",
    "小明买了3支钢笔和2本笔记本，钢笔每支8元，笔记本每本5元，一共花了多少钱？",
    
    # 五年级
    "一个圆柱形水桶，底面半径是3分米，高是8分米，它的体积是多少立方分米？",
    "一项工程，甲单独做需要12天完成，乙单独做需要15天完成，两人合作几天可以完成？",
    "一块地有5公顷，其中2/5种小麦，其余种玉米，种玉米的面积是多少公顷？",
    
    # 六年级
    "某种商品先提价20%，再降价20%，现在的价格是原价的百分之几？",
    "一个圆锥形沙堆，底面直径是6米，高是2米，如果每立方米沙重1.5吨，这堆沙重多少吨？",
    "甲乙两车分别从AB两地同时出发相向而行，甲车每小时行60千米，乙车每小时行40千米，经过3小时相遇，AB两地相距多少千米？",

    # 一年级（新增）
    "小红有6颗糖，吃了2颗，还剩几颗？",
    "树上原来有4只小鸟，又飞来了5只，现在一共有几只小鸟？",
    "小朋友排队做操，前面有7人，后面有2人，这一排一共有多少人？",

    # 二年级（新增）
    "一个文具盒18元，小明给了20元，应找回多少元？",
    "有36本练习本，平均分给6个小组，每组分到几本？",
    "操场跑道一圈是200米，小华跑了3圈，一共跑了多少米？",

    # 三年级（新增）
    "一个长方形花坛长15米，宽9米，它的周长是多少米？",
    "超市有250个鸡蛋，上午卖出86个，下午卖出74个，还剩多少个？",
    "每盒彩笔12支，买了5盒，一共有多少支彩笔？",

    # 四年级（新增）
    "一辆汽车每小时行驶75千米，4小时行驶多少千米？",
    "一个正方形边长是11厘米，它的周长和面积分别是多少？",
    "书店进了480本书，第一天卖出125本，第二天卖出98本，还剩多少本？",

    # 五年级（新增）
    "一根绳子长12米，用去3/4，还剩多少米？",
    "一桶油重24千克，用去了5/8，用去了多少千克？",
    "一件上衣原价160元，打九折后售价多少元？",

    # 六年级（新增）
    "一项工程，甲队单独做10天完成，乙队单独做15天完成，两队合作4天后还剩几分之几？",
    "圆的半径是5厘米，它的面积是多少平方厘米？（π取3.14）",
    "甲数与乙数的比是3:5，甲数是24，乙数是多少？"
]

# 语文题目库（成语方向）
CHINESE_QUESTIONS = [
    "成语“画龙点睛”中，“点睛”比喻什么？",
    "“亡羊补牢”这个成语告诉我们什么道理？",
    "成语“滥竽充数”通常用来形容哪类人？",
    "“守株待兔”这个成语讽刺了什么样的做法？",
    "成语“刻舟求剑”为什么不可取？",
    "“掩耳盗铃”中的人物犯了什么错误？",
    "成语“胸有成竹”通常形容一个人怎样？",
    "“井底之蛙”比喻什么样的人？",
    "成语“专心致志”和“心不在焉”是一对什么关系？",
    "请说出一个表示勤奋学习的成语，并简单解释其含义。",
    "成语“水滴石穿”告诉我们学习上要具备什么品质？",
    "“狐假虎威”这个成语中的狐狸是怎样做的？",
    "成语“叶公好龙”讽刺了哪种人？",
    "“对牛弹琴”一般用来形容什么情况？",
    "成语“自相矛盾”中的“矛盾”为什么会冲突？",
    "“拔苗助长”给我们的启示是什么？",
    "成语“闻鸡起舞”常用来赞扬什么精神？",
    "“负荆请罪”中体现了人物怎样的品格？",
    "成语“雪中送炭”和“锦上添花”在意思上有什么区别？",
    "请说出一个含有“学”字的成语，并解释它的意思。",
]

# 年龄、性别与姓名可控列表
AGE_OPTIONS = [str(i) for i in range(3, 11)]  # 3-10岁
GENDER_OPTIONS = ["男", "女"]
NAMES_BY_GENDER = {
    "男": ["冯玉桥", "子轩", "浩然", "宇航", "乐乐"],
    "女": ["冯昱乔", "欣怡", "若溪", "可馨", "萌萌"],
}

# 学科题库映射
QUESTION_BANK_BY_SUBJECT = {
    "数学": MATH_QUESTIONS,
    "语文": CHINESE_QUESTIONS,
}

# 动画主题库
ANIME_THEMES = [
    "海绵宝宝",
    "熊出没",
    "喜羊羊与灰太狼", 
    "超级飞侠",
    "汪汪队立大功",
    "小猪佩奇",
    "米奇妙妙屋",
    "托马斯和他的朋友们",
    "巴布工程师",
    "粉红猪小妹",
    "哆啦A梦",
    "蜡笔小新",
    "名侦探柯南",
    "宝可梦",
    "数码宝贝",
    "猫和老鼠",
    "汤姆杰瑞",
    "大头儿子小头爸爸",
    "蓝精灵",
    "葫芦娃"
]

def get_random_math_question():
    """随机获取一个数学题目"""
    return random.choice(MATH_QUESTIONS)


def get_env_list(name, default_values):
    """从环境变量读取逗号分隔列表；为空时回退默认值。"""
    raw = os.environ.get(name, "").strip()
    if not raw:
        return list(default_values)
    values = [item.strip() for item in raw.split(",") if item.strip()]
    return values if values else list(default_values)


def pick_child_profile():
    """按可控列表随机生成儿童档案，并确保姓名与性别配对。"""
    ages = get_env_list("DAILY_AGES", AGE_OPTIONS)
    genders = get_env_list("DAILY_GENDERS", GENDER_OPTIONS)
    gender = random.choice(genders)
    names_default = NAMES_BY_GENDER.get(gender, ["小朋友"])
    names = get_env_list(f"DAILY_NAMES_{gender}", names_default)
    name = random.choice(names)
    age = random.choice(ages)

    return {
        "character_name": name,
        "child_profile": {
            "age": age,
            "grade": gender,
            "name": name,
        },
    }


def pick_subject_and_question():
    """按学科随机抽题，支持数学/语文。"""
    subjects = get_env_list("DAILY_SUBJECTS", SUBJECT_OPTIONS)
    valid_subjects = [s for s in subjects if s in QUESTION_BANK_BY_SUBJECT]
    if not valid_subjects:
        valid_subjects = SUBJECT_OPTIONS
    subject = random.choice(valid_subjects)
    question_bank = QUESTION_BANK_BY_SUBJECT[subject]
    question = random.choice(question_bank)
    return subject, question


def get_random_anime_theme():
    """随机获取一个动画主题"""
    return random.choice(ANIME_THEMES)

def run_daily_coze_workflow(background: bool = False) -> str:
    """运行每日Coze工作流；background=True 时以后台方式启动子进程。"""
    # 从环境变量获取配置（COZE_API_TOKEN 由上方 load_dotenv 从 .env 注入）
    api_token = (os.environ.get("COZE_API_TOKEN") or "").strip()
    workflow_id = (os.environ.get("COZE_WORKFLOW_ID") or "7613788373953953834").strip()
    app_id = (os.environ.get("COZE_APP_ID") or "7613730010209878070").strip()
    max_wait_seconds = (os.environ.get("COZE_MAX_WAIT_SECONDS") or "1800").strip()

    if not api_token:
        err = (
            "COZE_API_TOKEN 未配置或为空：请在项目根目录的 .env 中设置 COZE_API_TOKEN（PAT），"
            f"本脚本已尝试加载 {_env_file}。"
        )
        print(err, file=sys.stderr)
        return err
    
    # 随机选择学科、题目和主题
    subject, question = pick_subject_and_question()
    theme = get_random_anime_theme()
    profile = pick_child_profile()
    
    # 构建参数
    parameters = {
        "character_name": profile["character_name"],
        "child_profile": {
            "age": profile["child_profile"]["age"],
            "grade": profile["child_profile"]["grade"],
            "interests": theme,
            "name": profile["child_profile"]["name"],
        },
        "include_dialogue": True,
        "line_art": False,
        "mode": "1",
        "panels_in_image": "12",
        "panels_layout": "3x4",
        "panels_per_prompt": "3",
        "questions": question,
        "style": "儿童漫画，卡通，2d, 连环画，活泼童趣氛围，可爱拟人化",
        "subject": subject,
        "theme": theme,
    }
    
    # 构建命令
    cmd = [
        sys.executable,  # 使用当前Python解释器
        f"{PROJECT_ROOT}/scripts/call_coze_workflow.py",
        "--token", api_token,
        "--workflow-id", workflow_id,
        "--app-id", app_id,
        "--parameters-json", json.dumps(parameters, ensure_ascii=False),
        "--max-wait-seconds", max_wait_seconds,
        "--poll-interval", "1.5"
    ]
    
    print(f"开始运行每日Coze工作流 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"儿童: {profile['child_profile']['name']} / {profile['child_profile']['grade']} / {profile['child_profile']['age']}岁")
    print(f"学科: {subject}")
    print(f"题目: {question}")
    print(f"主题: {theme}")
    
    log_path = None  # type: str | None
    if background:
        timestamp_fs = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_dir = os.path.join(PROJECT_ROOT, "logs")
        os.makedirs(log_dir, exist_ok=True)
        log_path = os.path.join(log_dir, f"openclaw_daily_coze_job_{timestamp_fs}.log")
        print(f"后台执行模式：日志写入 {log_path}")

    try:
        if background:
            # 子进程脱离当前会话，避免终端关闭导致子进程被一起回收
            assert log_path is not None  # 仅为了类型检查
            with open(log_path, "a", encoding="utf-8") as f:
                proc = subprocess.Popen(
                    cmd,
                    cwd=PROJECT_ROOT,
                    text=True,
                    stdout=f,
                    stderr=subprocess.STDOUT,
                    start_new_session=True,
                )
            msg = f"后台任务已启动，pid={proc.pid}（日志：{log_path}）"
            print(msg)
            return msg

        # 前台执行：不捕获输出，子进程 stdout/stderr 直接打印到当前终端
        result = subprocess.run(cmd, cwd=PROJECT_ROOT, text=True)
        if result.returncode != 0:
            raise subprocess.CalledProcessError(result.returncode, cmd)

        success_msg = f"""【每日{subject}练习】{datetime.now().strftime('%Y-%m-%d')}
        
题目：{question}
主题：{theme}
学科：{subject}
儿童：{profile['child_profile']['name']}（{profile['child_profile']['grade']}，{profile['child_profile']['age']}岁）

执行成功！

任务执行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        
        print(success_msg)
        return success_msg
        
    except subprocess.CalledProcessError as e:
        error_msg = f"""【任务执行失败】{datetime.now().strftime('%Y-%m-%d')}
        
题目：{question}
主题：{theme}
学科：{subject}
儿童：{profile['child_profile']['name']}（{profile['child_profile']['grade']}，{profile['child_profile']['age']}岁）

错误信息：{str(e)}
（子进程 stdout/stderr 已输出到上方控制台）

任务执行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""
        
        print(error_msg, file=sys.stderr)
        return error_msg
    except Exception as e:
        log_suffix = f"\n（后台日志：{log_path}）" if background and log_path else ""
        error_msg = f"""【任务执行失败】{datetime.now().strftime('%Y-%m-%d')}

题目：{question}
主题：{theme}
学科：{subject}
儿童：{profile['child_profile']['name']}（{profile['child_profile']['grade']}，{profile['child_profile']['age']}岁）

错误信息：{str(e)}{log_suffix}

任务执行时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

        print(error_msg, file=sys.stderr)
        return error_msg

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="OpenClaw 每日 Coze 工作流：默认前台执行；加 --background 后后台执行"
    )
    parser.add_argument(
        "--background",
        action="store_true",
        help="后台执行：子进程输出写入日志文件，并立即返回（不阻塞当前终端）",
    )
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()
    result = run_daily_coze_workflow(background=args.background)
    if not args.background:
        print(result)
    raise SystemExit(0)
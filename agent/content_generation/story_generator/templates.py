"""故事模板：按兴趣标签选择，含 introduction、challenge、solution、conclusion。"""
TEMPLATES = {
    "奥特曼": {
        "introduction": "在光之国的世界里，{character_name}是一位勇敢的光之战士。",
        "challenge": "今天，{character_name}遇到了一个难题：{problem_description}",
        "solution": "通过思考和努力，{character_name}想出了解决办法：{solution}",
        "conclusion": "最终，{character_name}成功地解决了问题，获得了{reward}！",
    },
    "海底小纵队": {
        "introduction": "在神秘的海底世界里，{character_name}和朋友们正在探险。",
        "challenge": "突然，他们遇到了一个挑战：{problem_description}",
        "solution": "团队合作，大家想出了好办法：{solution}",
        "conclusion": "问题解决了，海洋世界恢复了和平，{character_name}学到了新知识！",
    },
    "恐龙": {
        "introduction": "在远古的恐龙世界里，{character_name}是一只聪明的小恐龙。",
        "challenge": "今天，{character_name}需要完成一个任务：{problem_description}",
        "solution": "动动脑筋，{character_name}找到了答案：{solution}",
        "conclusion": "任务完成啦，{character_name}开心极了！",
    },
    "小动物学习": {
        "introduction": "森林学校里，{character_name}和伙伴们一起学习。",
        "challenge": "老师出了一道题：{problem_description}",
        "solution": "{character_name}认真思考，终于明白了：{solution}",
        "conclusion": "答对啦，{character_name}得到了老师的表扬！",
    },
}

DEFAULT_THEME = "小动物学习"

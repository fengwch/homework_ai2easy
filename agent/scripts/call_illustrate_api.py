#!/usr/bin/env python3
"""
模拟 curl 调用 POST /content/illustrate，用于本地测试。

等价于：
  curl -X POST 'http://localhost:8001/content/illustrate' \\
    -H 'Content-Type: application/json' \\
    -d '{"illustration_prompts":["小明和奥特曼在森林里数星星"],"interests":["奥特曼"]}' \\
    --max-time 400

接口仅接受 illustration_prompts、interests；style/panels/provider 等由 configs/content_generation.yaml 的 illustration 段控制。

环境变量（可选）：
  AGENT_BASE_URL       默认 http://localhost:8001
  ILLUSTRATE_TIMEOUT   默认 400（秒）
  ILLUSTRATE_PROMPTS   逗号分隔的插图描述，默认为博陆/苹果星故事长文案
  ILLUSTRATE_INTERESTS 逗号分隔的兴趣爱好，默认 "奥特曼,海底小纵队"，用于指定连环画角色

用法：
  python scripts/call_illustrate_api.py
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if (ROOT / ".env").exists():
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")

import httpx

#DEFAULT_PROMPT = """博陆是个戴红蓝手环的三年级男孩，最爱在窗台摆弄奥特曼小模型。每天放学，他都幻想自己是光之战士，守护星光小学的和平。今天，他刚把赛罗奥特曼摆上书桌，窗外忽然飘来一缕金光——咦？手环“叮”地亮起，浮现出一行闪亮字：“能量不足！请解开光之数学题，唤醒光之力量！”\n\n博陆眨眨眼，桌面自动展开一张发光卡片，上面画着1个星星+3个星星，还写着：“1+3=（ ）”，下面有三个按钮：A.2颗星、B.4颗星、C.5颗星。博陆挠挠头：“咦？1颗星星加3颗星星……不是变多了吗？”他赶紧拿出彩色铅笔，在纸上画：★ + ★★★ = ★★★★！数一数——1、2、3、4！“呀，是4颗！”他开心地按下B按钮。\n\n“叮咚！”手环绽放彩虹光柱，赛罗奥特曼的迷你光影在房间中央跃出，双臂交叉成L形，胸前水晶闪闪发亮！“答对啦，小光战士！”光影说，“加法就像集合光粒——1粒光+3粒光，合起来就是4粒更亮的光！”博陆举起手环，和光影一起比出“耶”的姿势，窗外的云朵也悄悄变成四颗连在一起的笑脸太阳。\n\n第二天课间，博陆主动帮同桌小雅算练习册上的加法题。他笑着说：“加法不是难题，是把小光点聚成大光束！”老师表扬他“像奥特曼一样用智慧发光”。放学路上，他仰望天空，仿佛看见银河里正飞过一道温柔的金色光痕——原来，最厉害的光之力量，就藏在认真思考的每一秒里。\n\n【学习要点】  \n• 加法的意义：把两个数量合起来  \n• 1 + 3 = 4 的直观理解（实物/图画计数）  \n• 鼓励独立思考与乐于助人"""
DEFAULT_PROMPT = """冯昱乔是海底小纵队最棒的“数学小海豚”！她戴着闪亮的蓝色潜水镜，背着会发光的小贝壳书包，每天和章鱼老师、小螃蟹助手一起在珊瑚湾探险。今天，小纵队接到新任务：帮迷路的小海马找回它丢失的“幸运珍珠”——可珍珠藏在三座神秘贝壳门后，每扇门上都写着一个成语谜题！游到第一扇门，门上画着一根针在蓝蓝的海水里飘呀飘，写着“海底捞针”；第二扇门挂着熟透的西瓜，滴着甜甜的汁水，“瓜熟蒂落”；第三扇门升起金灿灿的太阳，“旭日东升”；第四扇门下，一滴水正轻轻落在石头上，石头已有了小坑，“水滴穿石”。章鱼老师挥挥触手：“昱乔，哪件事最难发生？选对了，贝壳门才会打开哦！”冯昱乔摸摸小下巴，眨眨眼：“‘瓜熟蒂落’是西瓜熟了自己掉下来——天天都发生！‘旭日东升’太阳每天早上都出来，像闹钟一样准！‘水滴穿石’虽然慢，但小水滴坚持敲呀敲，石头真的会穿洞呢！可‘海底捞针’……大海那么大，针那么小，又没有GPS，找它就像数清所有沙粒一样难！”她举起小海星计数器：“所以——它发生的可能性最小！”贝壳门“哗啦”打开，珍珠在光里闪闪发亮！小海马开心地转圈圈，送给她一颗彩虹海螺。冯昱乔把海螺贴在耳边，听见温柔的声音：“坚持思考，再难的问题也会发光！”  """

def main():
    base_url = os.getenv("AGENT_BASE_URL", "http://localhost:8001").rstrip("/")
    prompts_str = os.getenv("ILLUSTRATE_PROMPTS", DEFAULT_PROMPT)
    prompts = [p.strip() for p in prompts_str.split(",") if p.strip()]
    if not prompts:
        prompts = [DEFAULT_PROMPT]

    interests_str = os.getenv("ILLUSTRATE_INTERESTS", "奥特曼,海底小纵队")
    interests = [s.strip() for s in interests_str.split(",") if s.strip()]
    if not interests:
        interests = ["奥特曼", "海底小纵队"]
    body = {
        "illustration_prompts": prompts,
        "interests": interests,
    }

    url = f"{base_url}/content/illustrate"
    timeout = float(os.getenv("ILLUSTRATE_TIMEOUT", "400"))

    print("=== 请求（模拟 curl）===")
    print(f"POST {url}")
    print("Content-Type: application/json")
    print("body:", json.dumps(body, ensure_ascii=False))
    print(f"timeout: {timeout}s")
    print("=== 响应 ===")

    try:
        r = httpx.post(url, json=body, timeout=timeout)
    except httpx.ConnectError as e:
        print("连接失败:", e, file=sys.stderr)
        return 1
    except httpx.TimeoutException as e:
        print("请求超时:", e, file=sys.stderr)
        return 1
    except Exception as e:
        print("请求异常:", e, file=sys.stderr)
        return 1

    print("status:", r.status_code)
    try:
        text = r.text
        print("body:", text[:1500] + ("..." if len(text) > 1500 else ""))
    except Exception:
        print("body: (无法读取)")

    if r.status_code >= 400:
        return 1
    try:
        data = r.json()
        items = data.get("items", [])
        print("items:", len(items))
        for i, item in enumerate(items):
            print(f"  [{i}] prompt: {(item.get('prompt') or '')[:60]}...")
            print(f"      images: {len(item.get('images') or [])} 个")
    except Exception as e:
        print("解析 JSON:", e, file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

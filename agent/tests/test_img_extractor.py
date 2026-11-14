import base64, json, requests

base = "/Users/fengwanchang/Documents/homework_ai2easy/agent"
img_path = base + "/imgs/story/2026091001/story.png"

with open(img_path, "rb") as f:
    b64 = base64.b64encode(f.read()).decode("utf-8")
data_url = f"data:image/png;base64,{b64}"

payload = {
    "image": data_url,
    "max_panels": 12  # 或不传
}

resp = requests.post("https://hw.gameyeah.net/agent/img_extractor", json=payload)
print(resp.status_code)
print(json.dumps(resp.json(), ensure_ascii=False, indent=2))
import requests
import json

# 测试配置
API_KEY = "ark-1cee974c-e577-4b3b-846b-43d3643223d1-fa964"
BASE_URL = "http://localhost:5000"

print("=== 测试豆包AI角色图片生成 ===")

# 测试1: 测试单个角色生成
print("\n=== 测试1: 单个角色生成 ===")
try:
    response = requests.post(
        f"{BASE_URL}/api/doubao/images/generate-pixel-character",
        headers={"Content-Type": "application/json"},
        json={
            "character_name": "孙悟空",
            "character_description": "美猴王",
            "api_key": API_KEY
        },
        timeout=60
    )
    
    print(f"状态码: {response.status_code}")
    data = response.json()
    print(f"响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
    
except Exception as e:
    print(f"请求失败: {str(e)}")

# 测试2: 测试背景生成
print("\n=== 测试2: 背景生成 ===")
try:
    response = requests.post(
        f"{BASE_URL}/api/doubao/images/generate-pixel-background",
        headers={"Content-Type": "application/json"},
        json={
            "scene_description": "fantasy forest",
            "api_key": API_KEY
        },
        timeout=60
    )
    
    print(f"状态码: {response.status_code}")
    data = response.json()
    print(f"响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
    
except Exception as e:
    print(f"请求失败: {str(e)}")

# 测试3: 测试批量生成
print("\n=== 测试3: 批量生成 ===")
try:
    response = requests.post(
        f"{BASE_URL}/api/doubao/images/generate-all",
        headers={"Content-Type": "application/json"},
        json={
            "text": "孙悟空三打白骨精",
            "characters": [
                {"name": "孙悟空", "description": "主角"},
                {"name": "白骨精", "description": "反派"}
            ],
            "api_key": API_KEY
        },
        timeout=120
    )
    
    print(f"状态码: {response.status_code}")
    data = response.json()
    print(f"响应: {json.dumps(data, ensure_ascii=False, indent=2)}")
    
except Exception as e:
    print(f"请求失败: {str(e)}")
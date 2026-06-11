import requests
import json

# 测试配置
API_KEY = "ark-1cee974c-e577-4b3b-846b-43d3643223d1-fa964"
API_URL = "http://localhost:5000/api/doubao/images/generate-all"

print("=== 测试豆包AI批量图片生成 ===")
print(f"API地址: {API_URL}")
print(f"API Key存在: {'是' if API_KEY else '否'}")
print()

# 先测试配置接口
try:
    config_response = requests.get("http://localhost:5000/api/test/config", timeout=10)
    print(f"配置接口响应: {config_response.status_code}")
    if config_response.status_code == 200:
        config_data = config_response.json()
        print(f"ARK_API_KEY配置: {'已配置' if config_data.get('ARK_API_KEY_exists') else '未配置'}")
except Exception as e:
    print(f"连接失败: {str(e)}")
    exit()

# 测试数据
test_data = {
    "text": "孙悟空三打白骨精",
    "characters": [
        {"name": "孙悟空", "description": "主角，美猴王，会七十二变"},
        {"name": "白骨精", "description": "反派，妖怪"},
        {"name": "唐僧", "description": "师傅"},
        {"name": "猪八戒", "description": "配角"},
        {"name": "沙僧", "description": "配角"}
    ],
    "api_key": API_KEY
}

print(f"\n故事文本: {test_data['text']}")
print(f"角色数量: {len(test_data['characters'])}")

try:
    print("\n正在发送请求...")
    response = requests.post(
        API_URL,
        headers={"Content-Type": "application/json"},
        json=test_data,
        timeout=120
    )
    
    print(f"\n响应状态码: {response.status_code}")
    print(f"响应头: {dict(response.headers)}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"\n响应JSON: {json.dumps(data, ensure_ascii=False, indent=2)}")
        
        print(f"\n生成结果: {'成功' if data.get('success') else '失败'}")
        
        if data.get('success'):
            # 打印背景信息
            if data.get('background'):
                print(f"\n=== 背景图片 ===")
                print(f"场景类型: {data.get('scene_type')}")
                print(f"图片URL: {data.get('background', {}).get('image_url')}")
            
            # 打印角色信息
            characters = data.get('characters', [])
            print(f"\n=== 角色图片 ({len(characters)}个) ===")
            success_count = 0
            fail_count = 0
            for i, char in enumerate(characters):
                print(f"\n角色 {i+1}: {char.get('name')}")
                if char.get('image_url'):
                    print(f"  - 图片URL: {char.get('image_url')[:50]}...")
                    success_count += 1
                elif char.get('error'):
                    print(f"  - 错误: {char.get('error')}")
                    fail_count += 1
            
            print(f"\n生成统计: 成功 {success_count} 个, 失败 {fail_count} 个")
        else:
            print(f"错误信息: {data.get('error')}")
    else:
        print(f"响应内容: {response.text[:500]}")
        
except Exception as e:
    print(f"请求失败: {str(e)}")
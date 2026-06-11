#!/usr/bin/env python
"""
测试图片生成和素材管理流程
"""

import json
import requests

# 配置
API_BASE = "http://localhost:5000"

def test_prompt_generation():
    """测试提示词生成"""
    print("\n=== 测试提示词生成 ===")
    
    # 测试地图提示词
    data = {
        "text": "小红帽走进了森林，阳光透过树叶洒下来，形成斑驳的光影。",
        "scene": "森林"
    }
    response = requests.post(f"{API_BASE}/api/image-prompts/generate-map", json=data)
    print(f"地图提示词生成: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"提示词: {result.get('prompt', '')[:100]}...")
    
    # 测试角色提示词
    data = {
        "character": {
            "name": "小红帽",
            "description": "戴着红色帽子的小女孩",
            "role": "主角"
        },
        "transparent": True
    }
    response = requests.post(f"{API_BASE}/api/image-prompts/generate-character", json=data)
    print(f"\n角色提示词生成: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"提示词: {result.get('prompt', '')[:100]}...")

def test_asset_management():
    """测试素材管理"""
    print("\n=== 测试素材管理 ===")
    
    # 测试获取地图素材列表
    response = requests.get(f"{API_BASE}/api/assets/list-maps")
    print(f"获取地图素材列表: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"地图素材数量: {len(result.get('assets', []))}")
    
    # 测试获取角色素材列表
    response = requests.get(f"{API_BASE}/api/assets/list-characters")
    print(f"\n获取角色素材列表: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"角色素材数量: {len(result.get('assets', []))}")

def test_generate_all_prompts():
    """测试一键生成所有提示词"""
    print("\n=== 测试一键生成所有提示词 ===")
    
    data = {
        "text": "小红帽走进了森林，遇到了一只大灰狼。大灰狼问她要去哪里，小红帽说要去奶奶家送蛋糕。",
        "characters": [
            {"name": "小红帽", "description": "戴着红色帽子的小女孩", "role": "主角"},
            {"name": "大灰狼", "description": "森林里的坏蛋", "role": "反派"}
        ]
    }
    
    response = requests.post(f"{API_BASE}/api/image-prompts/generate-all", json=data)
    print(f"一键生成提示词: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"场景类型: {result.get('scene_type')}")
        print(f"地图提示词: {result.get('map', {}).get('prompt', '')[:100]}...")
        chars = result.get('characters', [])
        print(f"角色数量: {len(chars)}")
        for char in chars:
            print(f"  - {char.get('character_name')}: {char.get('prompt')[:50]}...")

def main():
    """主测试函数"""
    print("="*50)
    print("测试童话镇多智能体系统 - 图片生成流程")
    print("="*50)
    
    # 测试提示词生成
    test_prompt_generation()
    
    # 测试素材管理
    test_asset_management()
    
    # 测试一键生成提示词
    test_generate_all_prompts()
    
    print("\n" + "="*50)
    print("测试完成！")
    print("注意：完整的图片生成需要配置有效的nanobanana API密钥")
    print("="*50)

if __name__ == "__main__":
    main()

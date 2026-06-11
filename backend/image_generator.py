"""
童话镇多智能体系统 - 图片生成器（豆包AI版）

职责：
- 调用豆包AI API生成地图背景图片
- 调用豆包AI API生成角色人物图片（透明底）
- 使用火山引擎方舟API Key认证
"""

import requests
import json
import os
from typing import Dict, Any, Optional, List


# 配置从环境变量读取
DOUBAO_IMAGE_URL = os.getenv('DOUBAO_IMAGE_URL', 'https://ark.cn-beijing.volces.com/api/v3/images/generations')
DOUBAO_IMAGE_MODEL = os.getenv('DOUBAO_IMAGE_MODEL', 'doubao-seedream-4-5-251128')


class DoubaoImageGenerator:
    """
    豆包AI图片生成器
    
    功能：
    1. 生成地图背景图片
    2. 生成角色人物图片（支持透明底）
    """
    
    def __init__(self, api_key: str):
        """
        初始化图片生成器
        
        参数：
        - api_key: 火山引擎方舟API Key
        """
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    def generate_image(self, prompt: str, size: str = "2K", n: int = 1, watermark: bool = False) -> Dict[str, Any]:
        """
        同步生成图片
        
        参数：
        - prompt: 图片生成提示词
        - size: 图片大小，可选 2K（默认）、1:1、4:3、3:4、16:9、9:16、3:2、2:3、21:9
        - n: 生成图片数量，默认1，范围1-4
        - watermark: 是否添加水印，默认False
        
        返回：
        - 包含图片URL的字典
        """
        payload = {
            "model": DOUBAO_IMAGE_MODEL,
            "prompt": prompt,
            "size": size,
            "n": n,
            "watermark": watermark
        }
        
        try:
            response = requests.post(
                DOUBAO_IMAGE_URL,
                headers=self.headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            
            if "data" in result and len(result["data"]) > 0:
                image_url = result["data"][0].get("url", "")
                if image_url:
                    return {
                        "success": True,
                        "image_url": image_url,
                        "prompt": prompt,
                        "image_size": size,
                        "aspect_ratio": size if ":" in size else "16:9"
                    }
            
            return {"success": False, "error": "未返回图片URL", "response": result}
                
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"请求失败: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"生成失败: {str(e)}"}
    
    def generate_map_image(self, prompt: str, image_size: str = "2K", 
                          aspect_ratio: str = "16:9") -> Dict[str, Any]:
        """
        生成地图背景图片
        
        参数：
        - prompt: 图片生成提示词
        - image_size: 图片大小，可选 1K、2K、4K，默认2K
        - aspect_ratio: 宽高比，可选 1:1、3:4、4:3、9:16、16:9，默认16:9
        
        返回：
        - 包含图片URL的字典
        """
        # 根据aspect_ratio选择合适的size参数
        size_map = {
            "1:1": "1:1",
            "4:3": "4:3",
            "3:4": "3:4",
            "16:9": "2K",
            "9:16": "9:16",
            "3:2": "3:2",
            "2:3": "2:3",
            "21:9": "21:9"
        }
        
        size = size_map.get(aspect_ratio, image_size)
        return self.generate_image(prompt, size)
    
    def generate_character_image(self, prompt: str, image_size: str = "2K", 
                                aspect_ratio: str = "3:4") -> Dict[str, Any]:
        """
        生成角色人物图片（透明背景）
        
        参数：
        - prompt: 图片生成提示词
        - image_size: 图片大小，可选 1K、2K、4K，默认2K
        - aspect_ratio: 宽高比，可选 1:1、3:4、4:3、9:16、16:9，默认3:4
        
        返回：
        - 包含图片URL的字典
        """
        # 根据aspect_ratio选择合适的size参数
        size_map = {
            "1:1": "1:1",
            "4:3": "4:3",
            "3:4": "3:4",
            "16:9": "2K",
            "9:16": "9:16",
            "3:2": "3:2",
            "2:3": "2:3",
            "21:9": "21:9"
        }
        
        size = size_map.get(aspect_ratio, image_size)
        
        # 添加透明背景提示
        full_prompt = f"{prompt}, transparent background"
        return self.generate_image(full_prompt, size)


# ==================== 便捷函数 ====================

def create_image_generator(api_key: str) -> DoubaoImageGenerator:
    """创建图片生成器实例"""
    return DoubaoImageGenerator(api_key)


def generate_map_image(api_key: str, prompt: str, image_size: str = "2K", 
                      aspect_ratio: str = "16:9") -> Dict[str, Any]:
    """便捷函数：生成地图图片"""
    generator = DoubaoImageGenerator(api_key)
    return generator.generate_map_image(prompt, image_size, aspect_ratio)


def generate_character_image(api_key: str, prompt: str, image_size: str = "2K", 
                            aspect_ratio: str = "3:4") -> Dict[str, Any]:
    """便捷函数：生成角色图片"""
    generator = DoubaoImageGenerator(api_key)
    return generator.generate_character_image(prompt, image_size, aspect_ratio)
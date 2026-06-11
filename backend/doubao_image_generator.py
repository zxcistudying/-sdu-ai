"""
童话镇多智能体系统 - 豆包图片生成器（火山引擎版）

职责：
- 调用豆包AI API生成像素画风的背景图片和人物图片
- 使用火山引擎API Key（Bearer Token）认证方式
"""

import requests
import json
from typing import Dict, Any, Optional, List


class DoubaoImageGenerator:
    """
    豆包图片生成器（火山引擎版）
    
    功能：
    1. 生成像素画风的地图背景图片
    2. 生成像素画风的角色人物图片
    3. 支持同步模式
    """
    
    def __init__(self, api_key: str, api_url: str = "https://ark.cn-beijing.volces.com/api/v3/images/generations", model: str = "doubao-seedream-4-5-251128"):
        """
        初始化图片生成器
        
        参数：
        - api_key: 火山引擎方舟API Key（在方舟控制台API Key管理中获取）
        - api_url: 豆包图片生成API地址
        - model: 使用的模型名称
        """
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
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
            "model": self.model,
            "prompt": prompt,
            "size": size,
            "n": n,
            "watermark": watermark
        }
        
        try:
            response = requests.post(
                self.api_url,
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
                        "size": size,
                        "model": self.model
                    }
            
            return {"success": False, "error": "未返回图片URL", "response": result}
                
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"请求失败: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": f"生成失败: {str(e)}"}
    
    def generate_pixel_background(self, scene_description: str) -> Dict[str, Any]:
        """
        生成像素画风的背景图片
        
        参数：
        - scene_description: 场景描述
        
        返回：
        - 包含图片URL的字典
        """
        prompt = f"Pixel art style top-down map, {scene_description}, overhead perspective, 2D flat map view, game background"
        return self.generate_image(prompt, "2K")
    
    def generate_pixel_character(self, character_name: str, character_description: str = "") -> Dict[str, Any]:
        """
        生成像素画风的角色人物图片（只有单个角色）
        
        参数：
        - character_name: 角色名称
        - character_description: 角色描述
        
        返回：
        - 包含图片URL的字典
        """
        prompt = f"Pixel art style single character portrait, {character_name}, {character_description}, solo, alone, isolated on background, only one person, game sprite, 2D character art"
        return self.generate_image(prompt, "2K")


# ==================== 便捷函数 ====================

def create_doubao_image_generator(api_key: str, api_url: str = None, model: str = None) -> DoubaoImageGenerator:
    """创建豆包图片生成器实例"""
    url = api_url or "https://ark.cn-beijing.volces.com/api/v3/images/generations"
    model_name = model or "doubao-seedream-4-5-251128"
    return DoubaoImageGenerator(api_key, url, model_name)


def generate_pixel_background(api_key: str, scene_description: str, api_url: str = None, model: str = None) -> Dict[str, Any]:
    """便捷函数：生成像素画风背景图片"""
    generator = create_doubao_image_generator(api_key, api_url, model)
    return generator.generate_pixel_background(scene_description)


def generate_pixel_character(api_key: str, character_name: str, character_description: str = "", api_url: str = None, model: str = None) -> Dict[str, Any]:
    """便捷函数：生成像素画风角色图片"""
    generator = create_doubao_image_generator(api_key, api_url, model)
    return generator.generate_pixel_character(character_name, character_description)
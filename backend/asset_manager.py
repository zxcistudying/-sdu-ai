"""
童话镇多智能体系统 - 素材管理器

职责：
- 下载生成的图片
- 将地图图片保存为背景素材
- 将角色图片保存为角色素材
- 管理素材目录结构
- 提供素材访问接口
"""

import os
import requests
import uuid
from typing import Dict, Any, Optional
from datetime import datetime

# 素材目录结构
ASSET_DIR = os.path.join(os.path.dirname(__file__), '..', 'frontend', 'assets')
MAP_DIR = os.path.join(ASSET_DIR, 'maps')
CHARACTER_DIR = os.path.join(ASSET_DIR, 'characters')


class AssetManager:
    """
    素材管理器
    
    功能：
    1. 下载远程图片到本地
    2. 管理地图背景素材
    3. 管理角色人物素材
    4. 提供素材路径和URL
    """
    
    def __init__(self):
        """初始化素材管理器，确保目录存在"""
        self._ensure_directories()
    
    def _ensure_directories(self):
        """确保素材目录存在"""
        for dir_path in [ASSET_DIR, MAP_DIR, CHARACTER_DIR]:
            if not os.path.exists(dir_path):
                os.makedirs(dir_path)
                print(f"创建目录: {dir_path}")
    
    def download_image(self, url: str, save_path: str) -> bool:
        """
        下载图片到指定路径
        
        参数：
        - url: 图片URL
        - save_path: 保存路径
        
        返回：
        - 是否成功
        """
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
            
            with open(save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"图片下载成功: {save_path}")
            return True
            
        except Exception as e:
            print(f"图片下载失败 {url}: {e}")
            return False
    
    def save_map_asset(self, image_url: str, scene_name: str) -> Dict[str, Any]:
        """
        保存地图背景素材
        
        参数：
        - image_url: 地图图片URL
        - scene_name: 场景名称
        
        返回：
        - 包含素材信息的字典
        """
        # 生成唯一文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"map_{scene_name}_{timestamp}.png"
        save_path = os.path.join(MAP_DIR, filename)
        
        # 下载图片
        if self.download_image(image_url, save_path):
            # 返回相对路径（供前端使用）
            relative_path = f"assets/maps/{filename}"
            
            return {
                "success": True,
                "asset_id": filename,
                "scene_name": scene_name,
                "local_path": save_path,
                "url": relative_path,
                "created_at": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "error": "图片下载失败",
                "scene_name": scene_name
            }
    
    def save_character_asset(self, image_url: str, character_name: str, emotion: str = "neutral") -> Dict[str, Any]:
        """
        保存角色人物素材（透明底）
        
        参数：
        - image_url: 角色图片URL
        - character_name: 角色名称
        - emotion: 角色情绪
        
        返回：
        - 包含素材信息的字典
        """
        # 生成唯一文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"char_{character_name}_{emotion}_{timestamp}.png"
        save_path = os.path.join(CHARACTER_DIR, filename)
        
        # 下载图片
        if self.download_image(image_url, save_path):
            # 返回相对路径（供前端使用）
            relative_path = f"assets/characters/{filename}"
            
            return {
                "success": True,
                "asset_id": filename,
                "character_name": character_name,
                "emotion": emotion,
                "local_path": save_path,
                "url": relative_path,
                "created_at": datetime.now().isoformat()
            }
        else:
            return {
                "success": False,
                "error": "图片下载失败",
                "character_name": character_name
            }
    
    def save_all_assets(self, map_info: Dict[str, Any], characters_info: list) -> Dict[str, Any]:
        """
        批量保存所有素材
        
        参数：
        - map_info: 地图信息（包含image_url和scene_type）
        - characters_info: 角色信息列表（包含name、image_url、emotion）
        
        返回：
        - 保存结果
        """
        results = {
            "map": None,
            "characters": [],
            "success_count": 0,
            "failed_count": 0
        }
        
        # 保存地图
        if map_info.get('image_url'):
            map_result = self.save_map_asset(
                map_info['image_url'],
                map_info.get('scene_type', 'unknown')
            )
            results["map"] = map_result
            if map_result["success"]:
                results["success_count"] += 1
            else:
                results["failed_count"] += 1
        
        # 保存角色
        for char_info in characters_info:
            if char_info.get('image_url'):
                char_result = self.save_character_asset(
                    char_info['image_url'],
                    char_info.get('name', 'unknown'),
                    char_info.get('emotion', 'neutral')
                )
                results["characters"].append(char_result)
                if char_result["success"]:
                    results["success_count"] += 1
                else:
                    results["failed_count"] += 1
        
        return results
    
    def list_map_assets(self) -> list:
        """列出所有地图素材"""
        assets = []
        if os.path.exists(MAP_DIR):
            for filename in os.listdir(MAP_DIR):
                if filename.endswith('.png') or filename.endswith('.jpg'):
                    filepath = os.path.join(MAP_DIR, filename)
                    mtime = os.path.getmtime(filepath)
                    assets.append({
                        "asset_id": filename,
                        "url": f"assets/maps/{filename}",
                        "modified_at": datetime.fromtimestamp(mtime).isoformat(),
                        "size": os.path.getsize(filepath)
                    })
        return sorted(assets, key=lambda x: x['modified_at'], reverse=True)
    
    def list_character_assets(self) -> list:
        """列出所有角色素材"""
        assets = []
        if os.path.exists(CHARACTER_DIR):
            for filename in os.listdir(CHARACTER_DIR):
                if filename.endswith('.png') or filename.endswith('.jpg'):
                    filepath = os.path.join(CHARACTER_DIR, filename)
                    mtime = os.path.getmtime(filepath)
                    # 从文件名提取角色名和情绪
                    parts = filename.split('_')
                    char_name = parts[1] if len(parts) > 1 else 'unknown'
                    emotion = parts[2] if len(parts) > 2 else 'neutral'
                    assets.append({
                        "asset_id": filename,
                        "character_name": char_name,
                        "emotion": emotion,
                        "url": f"assets/characters/{filename}",
                        "modified_at": datetime.fromtimestamp(mtime).isoformat(),
                        "size": os.path.getsize(filepath)
                    })
        return sorted(assets, key=lambda x: x['modified_at'], reverse=True)
    
    def get_asset_info(self, asset_id: str, asset_type: str = "character") -> Optional[Dict[str, Any]]:
        """
        获取素材信息
        
        参数：
        - asset_id: 素材ID（文件名）
        - asset_type: 素材类型（map或character）
        
        返回：
        - 素材信息字典
        """
        if asset_type == "map":
            directory = MAP_DIR
            url_prefix = "assets/maps/"
        else:
            directory = CHARACTER_DIR
            url_prefix = "assets/characters/"
        
        filepath = os.path.join(directory, asset_id)
        
        if os.path.exists(filepath):
            mtime = os.path.getmtime(filepath)
            return {
                "asset_id": asset_id,
                "url": f"{url_prefix}{asset_id}",
                "local_path": filepath,
                "modified_at": datetime.fromtimestamp(mtime).isoformat(),
                "size": os.path.getsize(filepath)
            }
        else:
            return None
    
    def delete_asset(self, asset_id: str, asset_type: str = "character") -> bool:
        """
        删除素材
        
        参数：
        - asset_id: 素材ID（文件名）
        - asset_type: 素材类型（map或character）
        
        返回：
        - 是否成功
        """
        if asset_type == "map":
            filepath = os.path.join(MAP_DIR, asset_id)
        else:
            filepath = os.path.join(CHARACTER_DIR, asset_id)
        
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"删除素材: {filepath}")
            return True
        else:
            print(f"素材不存在: {filepath}")
            return False


# ==================== 便捷函数 ====================

def create_asset_manager() -> AssetManager:
    """创建素材管理器实例"""
    return AssetManager()


def save_map_asset(image_url: str, scene_name: str) -> Dict[str, Any]:
    """便捷函数：保存地图素材"""
    manager = AssetManager()
    return manager.save_map_asset(image_url, scene_name)


def save_character_asset(image_url: str, character_name: str, emotion: str = "neutral") -> Dict[str, Any]:
    """便捷函数：保存角色素材"""
    manager = AssetManager()
    return manager.save_character_asset(image_url, character_name, emotion)


def save_all_assets(map_info: Dict[str, Any], characters_info: list) -> Dict[str, Any]:
    """便捷函数：批量保存所有素材"""
    manager = AssetManager()
    return manager.save_all_assets(map_info, characters_info)

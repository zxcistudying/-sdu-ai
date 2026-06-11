"""
童话镇多智能体系统 - AI图片提示词生成器

职责：
- 根据剧情文本生成地图/场景的AI图片生成提示词
- 根据角色信息生成人物的AI图片生成提示词（透明底）
- 支持多种风格和场景类型
"""

import re
from typing import List, Dict, Any, Optional


# ==================== 场景风格映射 ====================
SCENE_STYLES = {
    '童话': {
        'keywords': ['童话', '童话镇', 'fairy', 'fairytale'],
        'style_prompt': 'fantasy fairy tale style, magical, dreamlike, colorful, whimsical'
    },
    '森林': {
        'keywords': ['森林', '树林', 'forest', 'woods'],
        'style_prompt': 'dense enchanted forest, magical woods, fantasy landscape, lush green trees, mysterious atmosphere'
    },
    '城堡': {
        'keywords': ['城堡', '宫殿', 'castle', 'palace'],
        'style_prompt': 'grand fairy tale castle, majestic towers, magical kingdom, fantasy architecture'
    },
    '村庄': {
        'keywords': ['村庄', '小镇', 'village', 'town'],
        'style_prompt': 'charming medieval village, cozy cottages, cobblestone streets, fairy tale town'
    },
    '河流': {
        'keywords': ['河流', '小溪', 'river', 'stream'],
        'style_prompt': 'peaceful river flowing through forest, magical water stream, fantasy landscape'
    },
    '草地': {
        'keywords': ['草地', '草原', 'meadow', 'grassland'],
        'style_prompt': 'beautiful meadow with colorful flowers, sunny grassland, fantasy landscape'
    },
    '雪山': {
        'keywords': ['雪山', '雪地', 'snow', 'mountain'],
        'style_prompt': 'majestic snow covered mountains, winter wonderland, fantasy landscape'
    },
    '海洋': {
        'keywords': ['海洋', '海边', 'ocean', 'beach'],
        'style_prompt': 'magical ocean beach, sparkling sea, fantasy coastal scene'
    },
    '洞穴': {
        'keywords': ['洞穴', '山洞', 'cave', 'underground'],
        'style_prompt': 'mysterious underground cave, glowing crystals, fantasy underground world'
    },
    '花园': {
        'keywords': ['花园', '花园', 'garden', 'flower'],
        'style_prompt': 'beautiful enchanted garden, colorful flowers, magical plants, fantasy garden'
    }
}


# ==================== 角色风格映射 ====================
CHARACTER_STYLES = {
    '童话': 'cute fairy tale character, whimsical style, colorful',
    '奇幻': 'fantasy RPG character, detailed design, magical elements',
    '卡通': 'cartoon character design, cute and expressive',
    '手绘': 'hand drawn illustration style, artistic',
    '像素': 'pixel art character, retro game style'
}


# ==================== 角色职业/身份映射 ====================
CHARACTER_ROLES = {
    '小红帽': 'Little Red Riding Hood, girl wearing red hooded cloak, carrying basket',
    '大灰狼': 'Big Bad Wolf, anthropomorphic wolf, cunning expression',
    '猎人': 'hunter, woodsman, carrying bow and arrow, rugged appearance',
    '奶奶': 'old grandmother, kind face, wearing shawl',
    '公主': 'beautiful princess, elegant gown, crown or tiara',
    '王子': 'handsome prince, royal attire, noble appearance',
    '巫师': 'wizard or witch, magical robes, holding wand or staff',
    '骑士': 'knight in shining armor, sword and shield',
    '小精灵': 'cute fairy or elf, small stature, magical wings',
    '矮人': 'dwarf character, stout build, mining tools',
    '巨龙': 'majestic dragon, scales, wings, magical creature',
    '魔法师': 'powerful magician, mystical robes, glowing eyes'
}


class PromptGenerator:
    """
    AI图片提示词生成器
    
    功能：
    1. 根据剧情文本生成场景/地图的图片提示词
    2. 根据角色信息生成人物图片提示词（支持透明底）
    """
    
    def __init__(self):
        self.scene_descriptions = {}
        self.character_descriptions = {}
    
    def _detect_scene_type(self, text: str) -> str:
        """检测场景类型"""
        for scene_type, config in SCENE_STYLES.items():
            for keyword in config['keywords']:
                if keyword.lower() in text.lower():
                    return scene_type
        return '童话'  # 默认童话风格
    
    def _detect_time_of_day(self, text: str) -> str:
        """检测时间描述"""
        time_keywords = {
            '白天': ['白天', '正午', '上午', '下午', '阳光', 'sunny', 'day'],
            '夜晚': ['夜晚', '黑夜', '晚上', '月光', '星星', 'moon', 'night'],
            '黄昏': ['黄昏', '傍晚', '夕阳', '落日', 'sunset', 'dusk'],
            '黎明': ['黎明', '清晨', '破晓', 'sunrise', 'dawn']
        }
        
        for time_of_day, keywords in time_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text.lower():
                    return time_of_day
        return '白天'
    
    def _detect_weather(self, text: str) -> str:
        """检测天气描述"""
        weather_keywords = {
            '晴朗': ['晴朗', '阳光明媚', 'sunny', 'clear'],
            '下雨': ['下雨', '雨天', 'rain', 'raining'],
            '下雪': ['下雪', '雪天', 'snow', 'snowing'],
            '阴天': ['阴天', '多云', 'cloudy', 'overcast'],
            '雾': ['雾', '雾气', 'fog', 'mist'],
            '彩虹': ['彩虹', 'rainbow']
        }
        
        for weather, keywords in weather_keywords.items():
            for keyword in keywords:
                if keyword.lower() in text.lower():
                    return weather
        return '晴朗'
    
    def _extract_scene_details(self, text: str) -> Dict[str, str]:
        """提取场景细节"""
        details = {
            'scene_type': self._detect_scene_type(text),
            'time_of_day': self._detect_time_of_day(text),
            'weather': self._detect_weather(text)
        }
        return details
    
    def generate_map_prompt(self, text: str, scene_name: Optional[str] = None) -> str:
        """
        生成地图/场景背景的AI图片提示词
        
        参数：
        - text: 剧情文本
        - scene_name: 场景名称（可选）
        
        返回：
        - 适合AI图片生成的提示词字符串
        """
        details = self._extract_scene_details(text)
        scene_type = details['scene_type']
        time_of_day = details['time_of_day']
        weather = details['weather']
        
        # 获取风格提示词
        style_prompt = SCENE_STYLES.get(scene_type, SCENE_STYLES['童话'])['style_prompt']
        
        # 时间描述
        time_descriptions = {
            '白天': 'bright daylight, sunny',
            '夜晚': 'dark night, moonlight, stars',
            '黄昏': 'golden sunset, twilight',
            '黎明': 'early morning, sunrise'
        }
        
        # 天气描述
        weather_descriptions = {
            '晴朗': 'clear sky, beautiful weather',
            '下雨': 'raining, wet ground',
            '下雪': 'snowing, snow covered ground',
            '阴天': 'cloudy sky, moody atmosphere',
            '雾': 'foggy, misty atmosphere',
            '彩虹': 'beautiful rainbow in sky'
        }
        
        # 构建完整提示词
        prompt_parts = [
            f"beautiful {scene_type} landscape",
            style_prompt,
            time_descriptions.get(time_of_day, ''),
            weather_descriptions.get(weather, ''),
            "detailed background, fantasy setting",
            "high quality, detailed artwork",
            "game background style",
            "wide panoramic view"
        ]
        
        # 如果有场景名称，添加到提示词
        if scene_name:
            prompt_parts.insert(0, f"scene of {scene_name}")
        
        # 移除空字符串并拼接
        full_prompt = ', '.join(filter(None, prompt_parts))
        
        # 添加负面提示词
        negative_prompt = "text, watermark, logo, low quality, blurry, ugly, distorted, cluttered"
        
        return {
            'prompt': full_prompt,
            'negative_prompt': negative_prompt,
            'scene_type': scene_type,
            'time_of_day': time_of_day,
            'weather': weather
        }
    
    def generate_character_prompt(self, character_info: Dict[str, Any], transparent_background: bool = True) -> str:
        """
        生成人物图片的AI图片提示词
        
        参数：
        - character_info: 角色信息字典，包含 name, description, role 等
        - transparent_background: 是否需要透明背景（默认True）
        
        返回：
        - 适合AI图片生成的提示词字符串（包含透明底要求）
        """
        name = character_info.get('name', '')
        description = character_info.get('description', '')
        role = character_info.get('role', '')
        emotion = character_info.get('emotion', 'neutral')
        
        # 获取角色职业描述
        role_prompt = CHARACTER_ROLES.get(name, '')
        
        # 情绪描述
        emotion_descriptions = {
            'happy': 'happy expression, smiling',
            'sad': 'sad expression, sorrowful',
            'angry': 'angry expression, furious',
            'surprised': 'surprised expression, shocked',
            'neutral': 'neutral expression, calm',
            'excited': 'excited expression, energetic',
            'worried': 'worried expression, concerned'
        }
        
        # 构建提示词部分
        prompt_parts = []
        
        # 角色名称和类型
        if name:
            prompt_parts.append(f"character portrait of {name}")
        
        # 职业/身份描述
        if role_prompt:
            prompt_parts.append(role_prompt)
        elif description:
            prompt_parts.append(description)
        
        # 情绪描述
        prompt_parts.append(emotion_descriptions.get(emotion, 'neutral expression'))
        
        # 风格描述
        prompt_parts.append("fantasy fairy tale style")
        prompt_parts.append("detailed character design")
        prompt_parts.append("beautiful artwork")
        prompt_parts.append("high quality")
        prompt_parts.append("full body character")
        
        # 透明背景（关键）
        if transparent_background:
            prompt_parts.append("transparent background")
            prompt_parts.append("PNG format")
            prompt_parts.append("cutout character")
        
        # 移除空字符串并拼接
        full_prompt = ', '.join(filter(None, prompt_parts))
        
        # 负面提示词
        negative_prompt = "text, watermark, logo, low quality, blurry, ugly, distorted, "
        if transparent_background:
            negative_prompt += "background, solid color background, shadow, messy background"
        
        return {
            'prompt': full_prompt,
            'negative_prompt': negative_prompt,
            'character_name': name,
            'emotion': emotion,
            'transparent': transparent_background
        }
    
    def generate_prompts_from_text(self, text: str, characters: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        从剧情文本和角色列表生成完整的提示词集合
        
        参数：
        - text: 剧情文本
        - characters: 角色列表
        
        返回：
        - 包含地图提示词和所有角色提示词的字典
        """
        # 生成地图提示词
        scene_name = self._detect_scene_type(text)
        map_prompt = self.generate_map_prompt(text, scene_name)
        
        # 生成每个角色的提示词
        character_prompts = []
        for char in characters:
            char_prompt = self.generate_character_prompt(char, transparent_background=True)
            character_prompts.append(char_prompt)
        
        return {
            'map': map_prompt,
            'characters': character_prompts,
            'scene_type': scene_name,
            'total_characters': len(character_prompts)
        }


# ==================== 辅助函数 ====================

def generate_map_prompt(text: str, scene_name: Optional[str] = None) -> Dict[str, str]:
    """便捷函数：生成地图提示词"""
    generator = PromptGenerator()
    return generator.generate_map_prompt(text, scene_name)


def generate_character_prompt(character_info: Dict[str, Any], transparent: bool = True) -> Dict[str, str]:
    """便捷函数：生成角色提示词"""
    generator = PromptGenerator()
    return generator.generate_character_prompt(character_info, transparent)


def generate_all_prompts(text: str, characters: List[Dict[str, Any]]) -> Dict[str, Any]:
    """便捷函数：生成所有提示词"""
    generator = PromptGenerator()
    return generator.generate_prompts_from_text(text, characters)

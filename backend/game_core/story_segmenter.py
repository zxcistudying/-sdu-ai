"""
game_core/story_segmenter.py

职责：
- 智能将长剧本/动作序列分成多个段落
- 基于场景变化、动作密度、叙事节奏进行智能分段
- 为每段生成独立的表演序列，支持连续演出
"""

from __future__ import annotations

import re
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class StorySegment:
    """故事段落"""
    segment_id: int
    actions: List[Dict[str, Any]]
    narrative: str
    scene_context: str
    characters_in_segment: List[str]
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            'segment_id': self.segment_id,
            'actions': self.actions,
            'action_count': len(self.actions),
            'narrative': self.narrative,
            'scene_context': self.scene_context,
            'characters': self.characters_in_segment,
            'metadata': self.metadata
        }


class StorySegmenter:
    """
    剧本分段器

    分段策略（按优先级）：
    1. 场景切换 - 检测到 enter_scene 动作时自然分段
    2. 动作密度 - 单段超过最大动作数时强制分段
    3. 叙事节奏 - 对话密集区与叙述区的转换点
    4. 文本长度 - 原始文本过长时按语义切分
    """

    # 配置参数
    MAX_ACTIONS_PER_SEGMENT = 8  # 每段最大动作数
    MAX_TEXT_LENGTH_PER_SEGMENT = 300  # 每段最大文本长度（字符）
    MIN_ACTIONS_PER_SEGMENT = 2  # 每段最小动作数
    SCENE_CHANGE_ACTIONS = {'enter_scene', 'exit_scene'}  # 触发分段的场景动作

    def __init__(self, config: Optional[Dict[str, int]] = None):
        if config:
            self.MAX_ACTIONS_PER_SEGMENT = config.get('max_actions', self.MAX_ACTIONS_PER_SEGMENT)
            self.MAX_TEXT_LENGTH_PER_SEGMENT = config.get('max_text_length', self.MAX_TEXT_LENGTH_PER_SEGMENT)

    def segment_story(
            self,
            raw_text: str,
            actions: List[Dict[str, Any]],
            characters: List[Dict[str, Any]],
            current_scene: str = "童话镇广场"
    ) -> List[StorySegment]:
        """
        将完整的故事分成多个段落

        参数：
        - raw_text: 原始输入文本
        - actions: AI提取的完整动作序列
        - characters: 角色列表
        - current_scene: 当前场景名称

        返回：
        - StorySegment 列表，每个段落可独立演出
        """
        logger.info(f"开始剧本分段：文本长度={len(raw_text)}, 动作数量={len(actions)}")

        if not actions:
            logger.warning("没有动作需要分段")
            return []

        # 判断是否需要分段
        needs_segmentation = self._needs_segmentation(raw_text, actions)

        if not needs_segmentation:
            logger.info("剧本较短，不需要分段，作为单段处理")
            return [self._create_single_segment(actions, raw_text, current_scene)]

        # 执行分段算法
        segments = self._execute_segmentation(raw_text, actions, characters, current_scene)

        logger.info(f"分段完成：共 {len(segments)} 个段落")
        for i, seg in enumerate(segments):
            logger.info(f"  段落 {i + 1}: {seg.action_count}个动作, 场景={seg.scene_context}")

        return segments

    def _needs_segmentation(self, text: str, actions: List[Dict[str, Any]]) -> bool:
        """判断是否需要分段"""
        # 条件1：动作数量过多
        if len(actions) > self.MAX_ACTIONS_PER_SEGMENT * 1.5:
            return True

        # 条件2：文本过长
        if len(text) > self.MAX_TEXT_LENGTH_PER_SEGMENT * 2:
            return True

        # 条件3：存在场景切换
        for action in actions:
            if action.get('type') in self.SCENE_CHANGE_ACTIONS:
                return True

        return False

    def _create_single_segment(
            self,
            actions: List[Dict[str, Any]],
            text: str,
            scene: str
    ) -> StorySegment:
        """创建单一段落（不分段时使用）"""
        chars_in_seg = list(set(
            action.get('character', '')
            for action in actions
            if action.get('character')
        ))

        return StorySegment(
            segment_id=1,
            actions=actions,
            narrative=text[:200] + "..." if len(text) > 200 else text,
            scene_context=scene,
            characters_in_segment=chars_in_seg,
            metadata={'is_single_segment': True}
        )

    def _execute_segmentation(
            self,
            raw_text: str,
            actions: List[Dict[str, Any]],
            characters: List[Dict[str, Any]],
            current_scene: str
    ) -> List[StorySegment]:
        """执行核心分段算法"""

        # 策略1：基于场景切换的自然分段点
        split_points = self._find_scene_change_points(actions)

        # 如果找到场景切换点，优先在这些位置分割
        if split_points:
            return self._split_at_points(
                actions, raw_text, characters, current_scene, split_points
            )

        # 策略2：基于动作密度的均匀分段
        if len(actions) > self.MAX_ACTIONS_PER_SEGMENT:
            return self._split_by_action_density(
                actions, raw_text, characters, current_scene
            )

        # 策略3：基于文本长度的语义分段
        return self._split_by_semantics(
            actions, raw_text, characters, current_scene
        )

    def _find_scene_change_points(self, actions: List[Dict[str, Any]]) -> List[int]:
        """查找场景切换的位置索引"""
        points = []
        for i, action in enumerate(actions):
            if action.get('type') in self.SCENE_CHANGE_ACTIONS:
                points.append(i)
        return points

    def _split_at_points(
            self,
            actions: List[Dict[str, Any]],
            text: str,
            characters: List[Dict[str, Any]],
            current_scene: str,
            split_points: List[int]
    ) -> List[StorySegment]:
        """在指定位置分割"""
        segments = []
        start_idx = 0
        segment_id = 1
        scene = current_scene

        # 将split_points转换为包含结尾的完整区间
        all_points = split_points + [len(actions)]

        for end_idx in all_points:
            if end_idx <= start_idx:
                continue

            segment_actions = actions[start_idx:end_idx]

            if len(segment_actions) < self.MIN_ACTIONS_PER_SEGMENT and segments:
                # 如果太短，合并到上一段
                segments[-1].actions.extend(segment_actions)
                continue

            # 更新场景上下文
            for action in segment_actions:
                if action.get('type') == 'enter_scene':
                    scene = action.get('content', scene)

            # 提取该段的叙述文本
            segment_text = self._extract_segment_text(text, start_idx, end_idx, actions)

            # 收集该段的角色
            chars_in_seg = list(set(
                action.get('character', '')
                for action in segment_actions
                if action.get('character')
            ))

            segment = StorySegment(
                segment_id=segment_id,
                actions=segment_actions,
                narrative=segment_text,
                scene_context=scene,
                characters_in_segment=chars_in_seg,
                metadata={
                    'start_index': start_idx,
                    'end_index': end_idx,
                    'split_reason': 'scene_change'
                }
            )
            segments.append(segment)
            segment_id += 1
            start_idx = end_idx + 1

        return segments

    def _split_by_action_density(
            self,
            actions: List[Dict[str, Any]],
            text: str,
            characters: List[Dict[str, Any]],
            current_scene: str
    ) -> List[StorySegment]:
        """基于动作密度均匀分段"""
        segments = []
        total_actions = len(actions)
        num_segments = max(2, (total_actions + self.MAX_ACTIONS_PER_SEGMENT - 1) // self.MAX_ACTIONS_PER_SEGMENT)

        actions_per_segment = total_actions // num_segments
        remainder = total_actions % num_segments

        segment_id = 1
        idx = 0
        scene = current_scene

        while idx < total_actions:
            # 计算当前段的大小（前remainder段多分配1个）
            current_size = actions_per_segment + (1 if segment_id <= remainder else 0)
            end_idx = min(idx + current_size, total_actions)

            segment_actions = actions[idx:end_idx]

            # 提取该段的叙述文本
            segment_text = self._extract_segment_text(text, idx, end_idx, actions)

            # 收集角色
            chars_in_seg = list(set(
                action.get('character', '')
                for action in segment_actions
                if action.get('character')
            ))

            segment = StorySegment(
                segment_id=segment_id,
                actions=segment_actions,
                narrative=segment_text,
                scene_context=scene,
                characters_in_segment=chars_in_seg,
                metadata={
                    'start_index': idx,
                    'end_index': end_idx,
                    'split_reason': 'action_density'
                }
            )
            segments.append(segment)

            idx = end_idx
            segment_id += 1

        return segments

    def _split_by_semantics(
            self,
            actions: List[Dict[str, Any]],
            text: str,
            characters: List[Dict[str, Any]],
            current_scene: str
    ) -> List[StorySegment]:
        """基于语义（句子/段落）分段"""
        # 将文本按句子分割
        sentences = re.split(r'[。！？!?\n]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        if len(sentences) <= 1:
            return [self._create_single_segment(actions, text, current_scene)]

        # 尝试将动作映射到句子
        segments = []
        segment_id = 1
        current_text_parts = []
        current_actions = []
        current_text_len = 0
        scene = current_scene

        # 简化策略：将文本和动作按比例分配
        # 这里我们假设动作是按时间顺序排列的
        text_ratio = len(text) / max(len(actions), 1)

        for i, action in enumerate(actions):
            current_actions.append(action)

            # 估算对应的文本范围
            estimated_text_len = int(i * text_ratio)

            if (len(current_actions) >= self.MAX_ACTIONS_PER_SEGMENT or
                    current_text_len >= self.MAX_TEXT_LENGTH_PER_SEGMENT):
                # 创建当前段
                segment_text = text[
                               current_text_len:min(current_text_len + self.MAX_TEXT_LENGTH_PER_SEGMENT, len(text))]

                chars_in_seg = list(set(
                    a.get('character', '') for a in current_actions if a.get('character')
                ))

                segment = StorySegment(
                    segment_id=segment_id,
                    actions=current_actions[:],
                    narrative=segment_text,
                    scene_context=scene,
                    characters_in_segment=chars_in_seg,
                    metadata={
                        'split_reason': 'semantic',
                        'text_range': (
                        current_text_len, min(current_text_len + self.MAX_TEXT_LENGTH_PER_SEGMENT, len(text)))
                    }
                )
                segments.append(segment)

                current_actions.clear()
                current_text_len += self.MAX_TEXT_LENGTH_PER_SEGMENT
                segment_id += 1

        # 处理剩余的动作
        if current_actions:
            segment_text = text[current_text_len:] if current_text_len < len(text) else text[-100:]

            chars_in_seg = list(set(
                a.get('character', '') for a in current_actions if a.get('character')
            ))

            segment = StorySegment(
                segment_id=segment_id,
                actions=current_actions,
                narrative=segment_text,
                scene_context=scene,
                characters_in_segment=chars_in_seg,
                metadata={
                    'split_reason': 'semantic_remainder'
                }
            )
            segments.append(segment)

        return segments if segments else [self._create_single_segment(actions, text, current_scene)]

    def _extract_segment_text(
            self,
            full_text: str,
            start_action_idx: int,
            end_action_idx: int,
            actions: List[Dict[str, Any]]
    ) -> str:
        """从完整文本中提取对应段的叙述内容"""
        if not full_text:
            return ""

        # 简化实现：按比例截取文本
        total_actions = len(actions) or 1
        start_ratio = start_action_idx / total_actions
        end_ratio = end_action_idx / total_actions

        start_char = int(len(full_text) * start_ratio)
        end_char = int(len(full_text) * end_ratio)

        segment_text = full_text[start_char:end_char].strip()

        # 截断过长的文本
        if len(segment_text) > 200:
            segment_text = segment_text[:197] + "..."

        return segment_text or f"第{start_action_idx + 1}-{end_action_idx}个动作"


# ==================== 辅助函数 ====================

def create_segmenter(config: Optional[Dict[str, int]] = None) -> StorySegmenter:
    """便捷函数：创建分段器实例"""
    return StorySegmenter(config)


def segment_story_auto(
        text: str,
        actions: List[Dict[str, Any]],
        characters: List[Dict[str, Any]],
        scene: str = "童话镇广场",
        config: Optional[Dict[str, int]] = None
) -> List[Dict[str, Any]]:
    """
    自动分段故事的便捷函数

    参数：
    - text: 原始文本
    - actions: 动作序列
    - characters: 角色列表
    - scene: 当前场景
    - config: 自定义配置

    返回：
    - 分段后的字典列表（可直接JSON序列化）
    """
    segmenter = create_segmenter(config)
    segments = segmenter.segment_story(text, actions, characters, scene)

    return [seg.to_dict() for seg in segments]

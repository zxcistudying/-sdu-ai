"""
test_story_segmenter.py

测试剧本分段功能
"""

import sys
import os

# 添加backend目录到路径
sys.path.insert(0, os.path.dirname(__file__))

from game_core.story_segmenter import StorySegmenter, segment_story_auto


def test_basic_segmentation():
    """基础分段测试"""
    print("=" * 60)
    print("测试1: 基础分段功能")
    print("=" * 60)

    # 测试数据：较长的故事文本和多个动作
    long_text = """
    小红帽告别妈妈，独自走进森林。阳光透过树叶洒在小路上，她哼着歌，提着篮子向前走。
    突然，一只大灰狼从树后跳出来，拦住了她的去路。大灰狼说："小姑娘，你要去哪里呀？"
    小红帽有些害怕，但还是礼貌地回答："我要去奶奶家，给她送蛋糕和葡萄酒。"
    大灰狼眼珠一转，想到了坏主意。他说："你看，这边的花多美啊！为什么不采一些送给奶奶呢？"
    小红帽觉得有道理，就离开小路去采花了。大灰狼趁机抄近路跑向奶奶家。
    大灰狼到了奶奶家，敲门假装是小红帽。奶奶开门后，大灰狼一口把她吞进了肚子。
    然后大灰狼穿上奶奶的衣服，躺在床上等小红帽。过了一会儿，小红帽来到了奶奶家。
    """

    # 模拟多个动作（超过阈值）
    actions = [
        {'type': 'appear', 'character': '小红帽', 'content': '小红帽出现'},
        {'type': 'speak', 'character': '小红帽', 'content': '妈妈再见，我去奶奶家了'},
        {'type': 'move', 'character': '小红帽', 'target': '森林', 'content': '小红帽走进森林'},
        {'type': 'enter_scene', 'content': '进入森林'},
        {'type': 'appear', 'character': '大灰狼', 'content': '大灰狼出现'},
        {'type': 'speak', 'character': '大灰狼', 'content': '小姑娘，你要去哪里呀？'},
        {'type': 'speak', 'character': '小红帽', 'content': '我要去奶奶家，给她送蛋糕和葡萄酒'},
        {'type': 'speak', 'character': '大灰狼', 'content': '你看，这边的花多美啊！为什么不采一些送给奶奶呢？'},
        {'type': 'move', 'character': '小红帽', 'target': '花丛', 'content': '小红帽去采花'},
        {'type': 'move', 'character': '大灰狼', 'target': '奶奶家', 'content': '大灰狼跑去奶奶家'},
        {'type': 'enter_scene', 'content': '进入奶奶家'},
        {'type': 'action', 'character': '大灰狼', 'content': '大灰狼吞掉了奶奶'},
        {'type': 'appear', 'character': '小红帽', 'content': '小红帽来到奶奶家'},
    ]

    characters = [
        {'name': '小红帽', 'role': '主角', 'description': '戴着红色帽子的小女孩'},
        {'name': '大灰狼', 'role': '反派', 'description': '森林里的坏蛋'}
    ]

    # 执行分段
    segmenter = StorySegmenter()
    segments = segmenter.segment_story(
        raw_text=long_text,
        actions=actions,
        characters=characters,
        current_scene="童话镇广场"
    )

    print(f"\n原始文本长度: {len(long_text)} 字符")
    print(f"动作数量: {len(actions)} 个")
    print(f"分段结果: {len(segments)} 个段落\n")

    for i, seg in enumerate(segments):
        print(f"段落 {seg.segment_id}:")
        print(f"  - 动作数: {len(seg.actions)}")
        print(f"  - 叙述: {seg.narrative[:50]}...")
        print(f"  - 场景: {seg.scene_context}")
        print(f"  - 角色: {seg.characters_in_segment}")
        print(f"  - 分段原因: {seg.metadata.get('split_reason', 'N/A')}")
        print()

    assert len(segments) > 1, "应该分成多个段落"
    print("✅ 测试通过：成功将长剧本分段\n")


def test_short_story_no_segmentation():
    """短剧本不分段测试"""
    print("=" * 60)
    print("测试2: 短剧本不分段")
    print("=" * 60)

    short_text = "小红帽遇到了大灰狼。"

    actions = [
        {'type': 'meet', 'character': '小红帽', 'target': '大灰狼', 'content': '两人相遇'}
    ]

    characters = [
        {'name': '小红帽', 'role': '主角'},
        {'name': '大灰狼', 'role': '反派'}
    ]

    segmenter = StorySegmenter()
    segments = segmenter.segment_story(
        raw_text=short_text,
        actions=actions,
        characters=characters
    )

    print(f"\n原始文本: '{short_text}'")
    print(f"动作数量: {len(actions)} 个")
    print(f"分段结果: {len(segments)} 个段落\n")

    assert len(segments) == 1, "短剧本不应该分段"
    assert segments[0].metadata.get('is_single_segment'), "应该是单一段落"
    print("✅ 测试通过：短剧本未分段\n")


def test_scene_change_segmentation():
    """场景切换分段测试"""
    print("=" * 60)
    print("测试3: 场景切换自动分段")
    print("=" * 60)

    text = "小红帽从家里出发，经过广场，最后到达森林深处的奶奶家。"

    actions = [
        {'type': 'move', 'character': '小红帽', 'target': '门口', 'content': '走出家门'},
        {'type': 'enter_scene', 'content': '进入广场'},
        {'type': 'move', 'character': '小红帽', 'target': '广场中心', 'content': '穿过广场'},
        {'type': 'enter_scene', 'content': '进入森林'},
        {'type': 'move', 'character': '小红帽', 'target': '森林深处', 'content': '走向森林深处'},
        {'type': 'enter_scene', 'content': '到达奶奶家'},
    ]

    characters = [{'name': '小红帽', 'role': '主角'}]

    segmenter = StorySegmenter()
    segments = segmenter.segment_story(
        raw_text=text,
        actions=actions,
        characters=characters,
        current_scene="家中"
    )

    print(f"\n包含场景切换的动作数量: {len(actions)} 个")
    print(f"分段结果: {len(segments)} 个段落\n")

    for seg in segments:
        print(f"段落 {seg.segment_id}: 场景={seg.scene_context}, 动作数={len(seg.actions)}")

    # 应该在场景切换处分段
    assert len(segments) >= 2, "场景切换时应该分段"
    print("\n✅ 测试通过：场景切换时正确分段\n")


def test_action_density_segmentation():
    """动作密度分段测试"""
    print("=" * 60)
    print("测试4: 动作密度均匀分段")
    print("=" * 60)

    text = "这是一个很长的故事，包含很多对话和动作。" * 50  # 很长的文本

    # 创建大量动作（超过MAX_ACTIONS_PER_SEGMENT的1.5倍）
    actions = []
    for i in range(15):
        if i % 2 == 0:
            actions.append({
                'type': 'speak',
                'character': '角色A' if i % 4 == 0 else '角色B',
                'content': f'这是第{i + 1}句对话'
            })
        else:
            actions.append({
                'type': 'action',
                'character': '角色A',
                'content': f'第{i + 1}个动作'
            })

    characters = [
        {'name': '角色A', 'role': '主角'},
        {'name': '角色B', 'role': '配角'}
    ]

    segmenter = StorySegmenter()
    segments = segmenter.segment_story(
        raw_text=text,
        actions=actions,
        characters=characters
    )

    print(f"\n文本长度: {len(text)} 字符")
    print(f"动作数量: {len(actions)} 个 (阈值: {segmenter.MAX_ACTIONS_PER_SEGMENT})")
    print(f"分段结果: {len(segments)} 个段落\n")

    for seg in segments:
        print(f"段落 {seg.segment_id}: {len(seg.actions)}个动作 (≤{segmenter.MAX_ACTIONS_PER_SEGMENT})")
        assert len(seg.actions) <= segmenter.MAX_ACTIONS_PER_SEGMENT + 1, f"段落{seg.segment_id}动作数超限"

    assert len(segments) > 1, "动作过多时应该分段"
    print("\n✅ 测试通过：按动作密度均匀分段\n")


def test_convenience_function():
    """便捷函数测试"""
    print("=" * 60)
    print("测试5: 便捷函数 segment_story_auto")
    print("=" * 60)

    text = "测试文本" * 100
    actions = [{'type': 'speak', 'character': 'A', 'content': f'对话{i}'} for i in range(12)]
    characters = [{'name': 'A'}]

    # 使用便捷函数
    result = segment_story_auto(text, actions, characters)

    print(f"\n便捷函数返回类型: {type(result)}")
    print(f"返回段落数量: {len(result)}")

    if result:
        print(f"第一个段落结构: {list(result[0].keys())}")

        # 验证可以JSON序列化
        import json
        json_str = json.dumps(result, ensure_ascii=False, indent=2)
        print(f"JSON序列化成功，长度: {len(json_str)} 字符")

    print("\n✅ 测试通过：便捷函数正常工作\n")


def main():
    """运行所有测试"""
    print("\n" + "=" * 60)
    print("开始测试剧本分段功能")
    print("=" * 60 + "\n")

    try:
        test_basic_segmentation()
        test_short_story_no_segmentation()
        test_scene_change_segmentation()
        test_action_density_segmentation()
        test_convenience_function()

        print("=" * 60)
        print("🎉 所有测试通过！")
        print("=" * 60)

    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        return 1
    except Exception as e:
        print(f"\n❌ 测试异常: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == '__main__':
    exit(main())

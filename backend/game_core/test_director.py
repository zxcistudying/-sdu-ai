"""
测试剧情导演系统
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from game_core.game_state import GameState
from game_core.director import PlotDirector

def test_director():
    """测试剧情导演的核心功能"""
    
    print("=" * 60)
    print("测试剧情导演系统")
    print("=" * 60)
    
    # 1. 初始化游戏状态
    gs = GameState(
        story_background="童话镇是一个充满魔法的地方",
        characters=[
            {
                'name': '小红帽',
                'persona': '戴着红色帽子的小女孩',
                'goal': '去奶奶家',
                'position': {'x': 20, 'y': 30},
                'emotion': 'happy'
            },
            {
                'name': '大灰狼',
                'persona': '森林里的坏蛋',
                'goal': '吃掉小红帽',
                'position': {'x': 70, 'y': 40},
                'emotion': 'neutral'
            }
        ]
    )
    
    print(f"\n✓ 游戏状态初始化成功")
    print(f"  角色数量: {len(gs.characters)}")
    
    # 2. 创建导演
    director = PlotDirector(gs)
    print(f"✓ 剧情导演创建成功")
    
    # 3. 测试动作序列
    test_actions = [
        {
            'type': 'move',
            'character': '小红帽',
            'target': '森林深处',
            'content': '小红帽走向森林深处'
        },
        {
            'type': 'meet',
            'character': '小红帽',
            'target': '大灰狼',
            'content': '两人相遇'
        },
        {
            'type': 'speak',
            'character': '大灰狼',
            'content': '你好啊，小姑娘！',
            'emotion': 'friendly'
        },
        {
            'type': 'emotion',
            'character': '小红帽',
            'emotion': 'surprised'
        }
    ]
    
    print(f"\n✓ 准备测试 {len(test_actions)} 个动作")
    
    # 4. 执行导演
    response = director.direct_turn(
        raw_actions=test_actions,
        narrative="场景：森林",
        next_options=[
            {'label': '继续对话', 'action_input': 'continue'},
            {'label': '逃跑', 'action_input': 'run away'}
        ]
    )
    
    print(f"\n{'=' * 60}")
    print("导演输出结果:")
    print(f"{'=' * 60}")
    
    # 5. 展示结果
    print(f"\n📖 回合ID: {response['turn_id']}")
    print(f"\n📝 旁白:")
    print(f"   {response['narrative']}")
    
    if response['character_action']:
        action = response['character_action']
        print(f"\n🎭 主要动作:")
        print(f"   角色: {action['name']}")
        print(f"   动画: {action['animation']}")
        print(f"   表情: {action['expression']}")
        if action.get('target'):
            print(f"   目标: {action['target']}")
    
    if response['dialogue']:
        dialogue = response['dialogue']
        print(f"\n💬 对话:")
        print(f"   {dialogue['speaker']}: \"{dialogue['text']}\"")
        print(f"   情绪: {dialogue['emotion']}")
    
    print(f"\n🌍 状态变更:")
    changes = response['world_state_update']['state_changes']
    for i, change in enumerate(changes, 1):
        print(f"   {i}. {change['type']}: {change.get('character', '')}")
    
    print(f"\n🔘 后续选项:")
    for opt in response['next_options']:
        print(f"   - {opt['label']}")
    
    print(f"\n📊 元数据:")
    meta = response['metadata']
    print(f"   总动作数: {meta['total_actions']}")
    print(f"   有效动作: {meta['valid_actions']}")
    print(f"   已执行: {meta['executed_actions']}")
    
    print(f"\n{'=' * 60}")
    print("✅ 测试完成！")
    print(f"{'=' * 60}\n")
    
    return response


if __name__ == '__main__':
    try:
        result = test_director()
        print("所有测试通过！✨")
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

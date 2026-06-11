"""
测试人物移动功能
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from game_core.game_state import GameState
from game_core.director import PlotDirector, StateUpdater

def test_movement():
    """测试移动功能"""
    
    print("Testing movement functionality...")
    
    # 1. 初始化游戏状态
    gs = GameState(
        story_background="Fairy tale forest",
        characters=[
            {
                'name': 'Little Red',
                'persona': 'A little girl with red hat',
                'goal': 'Visit grandmother',
                'position': {'x': 20, 'y': 30},
                'emotion': 'happy'
            },
            {
                'name': 'Wolf',
                'persona': 'A big bad wolf',
                'goal': 'Eat Little Red',
                'position': {'x': 70, 'y': 40},
                'emotion': 'neutral'
            }
        ]
    )
    
    print("Game state initialized")
    print(f"Characters: {len(gs.characters)}")
    
    # 2. 测试 StateUpdater 的移动功能
    updater = StateUpdater(gs)
    
    # 测试移动动作
    move_action = {
        'type': 'move',
        'character': 'Little Red',
        'target': 'deep forest',
        'content': 'Little Red walks to the deep forest'
    }
    
    print("\nTesting move action...")
    result = updater.apply_move(move_action)
    
    print(f"Move result: {result}")
    
    # 检查位置是否更新
    character = gs.characters[0]
    print(f"Character position after move: {character.get('position')}")
    
    # 3. 测试 PlotDirector 生成表演序列
    director = PlotDirector(gs)
    
    test_actions = [
        {
            'type': 'move',
            'character': 'Little Red',
            'target': 'forest entrance',
            'content': 'Little Red goes to forest entrance'
        }
    ]
    
    print("\nTesting director with move action...")
    response = director.direct_turn(
        raw_actions=test_actions,
        narrative="Scene: Forest",
        next_options=[
            {'label': 'Continue', 'action_input': 'continue'}
        ]
    )
    
    print(f"Director response keys: {list(response.keys())}")
    
    # 检查是否生成了表演序列
    if 'director_output' in response and 'performance_sequence' in response['director_output']:
        sequence = response['director_output']['performance_sequence']
        print(f"\nGenerated performance sequence:")
        for step in sequence:
            print(f"  - Type: {step.get('type')}, Character: {step.get('character', 'N/A')}")
            if step.get('type') == 'character_move':
                print(f"    Target position: {step.get('target_position')}")
    
    print("\nMovement tests completed!")
    return True

def test_target_position_mapping():
    """测试位置描述到坐标的映射"""
    
    print("\nTesting target position mapping...")
    
    gs = GameState(
        characters=[{
            'name': 'TestChar',
            'position': {'x': 50, 'y': 50}
        }]
    )
    
    updater = StateUpdater(gs)
    
    # 测试各种位置描述
    test_targets = [
        'center',
        'left',
        'right',
        'top',
        'bottom',
        'top-left',
        'top-right',
        'bottom-left',
        'bottom-right',
        'forest entrance',
        'deep forest',
        'grandmother house',
        'door'
    ]
    
    print("Testing position mappings:")
    for target in test_targets:
        position = updater._target_to_position(target)
        print(f"  '{target}' -> {position}")
    
    return True

if __name__ == '__main__':
    try:
        test_movement()
        test_target_position_mapping()
        print("\nAll movement tests passed!")
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

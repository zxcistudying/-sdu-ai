// @vitest-environment jsdom

import fs from 'node:fs';
import path from 'node:path';
import { createRequire } from 'node:module';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

const require = createRequire(import.meta.url);
const appPath = path.resolve(__dirname, '../app.js');
const htmlPath = path.resolve(__dirname, '../index.html');

function loadAppShell() {
    const html = fs.readFileSync(htmlPath, 'utf-8');
    document.open();
    document.write(html);
    document.close();
}

function createSystem() {
    delete require.cache[require.resolve(appPath)];
    const { FairyTownSystem, MovementController } = require(appPath);
    
    // 模拟必要的DOM元素
    if (!document.getElementById('characters-container')) {
        const container = document.createElement('div');
        container.id = 'characters-container';
        container.style.position = 'relative';
        container.style.width = '100%';
        container.style.height = '500px';
        document.body.appendChild(container);
    }
    
    const system = new FairyTownSystem();
    return {
        system,
        movementController: new MovementController(system)
    };
}

describe('人物移动功能', () => {
    beforeEach(() => {
        vi.useFakeTimers();
        global.fetch = vi.fn();
        global.alert = vi.fn();
        global.confirm = vi.fn(() => true);
        
        loadAppShell();
        
        // 添加角色容器
        if (!document.getElementById('characters-container')) {
            const container = document.createElement('div');
            container.id = 'characters-container';
            container.style.position = 'relative';
            container.style.width = '100%';
            container.style.height = '500px';
            document.body.appendChild(container);
        }
    });

    afterEach(() => {
        vi.clearAllTimers();
        vi.useRealTimers();
        vi.restoreAllMocks();
    });

    it('初始化时角色应在默认位置', () => {
        const { system } = createSystem();
        
        // 添加测试角色
        system.characters = [{
            id: 'char-1',
            name: '小红帽',
            position: { x: 50, y: 50 },
            emotion: 'neutral'
        }];
        
        expect(system.characters[0].position).toEqual({ x: 50, y: 50 });
    });

    it('通过方向移动角色', () => {
        const { system, movementController } = createSystem();
        
        // 添加测试角色
        system.characters = [{
            id: 'char-1',
            name: '小红帽',
            position: { x: 50, y: 50 },
            emotion: 'neutral'
        }];
        
        // 向右移动
        const result = movementController.moveByDirection('char-1', 'right');
        
        expect(result.success).toBe(true);
        expect(system.characters[0].position.x).toBe(52); // defaultSpeed = 2
        expect(system.characters[0].position.y).toBe(50);
    });

    it('移动时应限制在边界内', () => {
        const { system, movementController } = createSystem();
        
        system.characters = [{
            id: 'char-1',
            name: '小红帽',
            position: { x: 5, y: 50 },  // 已在左边界
            emotion: 'neutral'
        }];
        
        // 尝试向左移动（应该被边界限制）
        const result = movementController.moveByDirection('char-1', 'left');
        
        expect(result.success).toBe(true);
        expect(result.clamped).toBe(true);
        expect(system.characters[0].position.x).toBe(5); // 保持在边界
    });

    it('支持8个方向的移动', () => {
        const { movementController } = createSystem();
        
        // 测试所有方向
        const directions = ['up', 'down', 'left', 'right', 
                           'up-left', 'up-right', 'down-left', 'down-right'];
        
        directions.forEach(direction => {
            const system2 = createSystem().system;
            system2.characters = [{
                id: 'char-1',
                name: '小红帽',
                position: { x: 50, y: 50 },
                emotion: 'neutral'
            }];
            
            const result = movementController.moveByDirection('char-1', direction);
            expect(result.success).toBe(true);
            expect(result.position).toBeDefined();
        });
    });

    it('持续移动功能', async () => {
        const { system, movementController } = createSystem();
        
        system.characters = [{
            id: 'char-1',
            name: '小红帽',
            position: { x: 50, y: 50 },
            emotion: 'neutral'
        }];
        
        // 开始持续向右移动
        movementController.startContinuousMovement('char-1', 'right');
        
        // 模拟时间流逝（多次间隔）
        vi.advanceTimersByTime(100); // 约6个间隔
        
        expect(system.characters[0].position.x).toBeGreaterThan(50);
        
        // 停止移动
        movementController.stopContinuousMovement('char-1');
        
        const finalX = system.characters[0].position.x;
        
        // 再等一下，位置不应变化
        vi.advanceTimersByTime(50);
        expect(system.characters[0].position.x).toBe(finalX);
    });

    it('平滑移动到指定位置', async () => {
        const { system, movementController } = createSystem();
        
        system.characters = [{
            id: 'char-1',
            name: '小红帽',
            position: { x: 10, y: 10 },
            emotion: 'neutral'
        }];
        
        // 启动平滑移动
        const promise = movementController.moveToPosition('char-1', 90, 90, { smooth: true });
        
        // 模拟动画完成
        vi.advanceTimersByTime(5000);
        
        await promise;
        
        expect(system.characters[0].position.x).toBe(90);
        expect(system.characters[0].position.y).toBe(90);
    });

    it('移动不存在的角色应返回错误', () => {
        const { movementController } = createSystem();
        
        const result = movementController.moveByDirection('char-999', 'right');
        
        expect(result.success).toBe(false);
        expect(result.error).toBe('Character not found');
    });

    it('速度应限制在最小和最大值之间', () => {
        const { system, movementController } = createSystem();
        
        system.characters = [{
            id: 'char-1',
            name: '小红帽',
            position: { x: 50, y: 50 },
            emotion: 'neutral'
        }];
        
        // 测试超出范围的速度
        const result = movementController.moveByDirection('char-1', 'right', 20); // 超过maxSpeed=10
        
        expect(result.success).toBe(true);
        // 速度被限制后，实际移动距离应该基于maxSpeed
        const movedX = system.characters[0].position.x - 50;
        expect(movedX).toBe(10); // maxSpeed
    });
});

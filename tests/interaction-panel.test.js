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

function setViewport({ width, height, windowWidth = width, windowHeight = height }) {
    Object.defineProperty(document.documentElement, 'clientWidth', {
        configurable: true,
        value: width
    });
    Object.defineProperty(document.documentElement, 'clientHeight', {
        configurable: true,
        value: height
    });
    Object.defineProperty(window, 'innerWidth', {
        configurable: true,
        writable: true,
        value: windowWidth
    });
    Object.defineProperty(window, 'innerHeight', {
        configurable: true,
        writable: true,
        value: windowHeight
    });
}

function mockPanelRect(panel) {
    panel.getBoundingClientRect = vi.fn(() => {
        const left = parseFloat(panel.style.left) || 0;
        const top = parseFloat(panel.style.top) || 0;
        const width = parseFloat(panel.style.width) || 600;
        const height = parseFloat(panel.style.height) || 500;

        return {
            x: left,
            y: top,
            left,
            top,
            right: left + width,
            bottom: top + height,
            width,
            height,
            toJSON() {
                return {};
            }
        };
    });
}

function dispatchMouse(target, type, x, y) {
    target.dispatchEvent(new window.MouseEvent(type, {
        bubbles: true,
        clientX: x,
        clientY: y
    }));
}

function createSystem() {
    delete require.cache[require.resolve(appPath)];
    const { FairyTownSystem } = require(appPath);
    const system = new FairyTownSystem();
    const panel = document.getElementById('interaction-panel');
    mockPanelRect(panel);

    return {
        system,
        panel,
        resizeHandle: document.getElementById('interaction-resize-handle'),
        selectedName: document.getElementById('selected-character-name'),
        dialogueHistory: document.getElementById('dialogue-history')
    };
}

describe('角色交互框缩放', () => {
    beforeEach(() => {
        vi.useFakeTimers();
        window.__FAIRY_TOWN_DISABLE_AUTO_INIT__ = true;
        window.requestAnimationFrame = vi.fn((cb) => {
            cb();
            return 1;
        });
        window.cancelAnimationFrame = vi.fn();
        global.requestAnimationFrame = window.requestAnimationFrame;
        global.cancelAnimationFrame = window.cancelAnimationFrame;
        global.fetch = vi.fn();
        global.alert = vi.fn();
        global.confirm = vi.fn(() => true);

        loadAppShell();
        setViewport({ width: 1024, height: 768 });
    });

    afterEach(() => {
        vi.clearAllTimers();
        vi.useRealTimers();
        vi.restoreAllMocks();
        delete window.__FAIRY_TOWN_DISABLE_AUTO_INIT__;
    });

    it('通过鼠标拖拽手柄实时更新宽高且保留角色内容', () => {
        const { system, panel, resizeHandle, selectedName, dialogueHistory } = createSystem();
        const character = system.characters[0];

        system.openInteractionPanel(character);
        system.applyInteractionPanelRect({
            left: 180,
            top: 100,
            width: 600,
            height: 500
        });
        system.addDialogueToHistory('user', '你好，Sam');

        dispatchMouse(resizeHandle, 'mousedown', 400, 400);
        dispatchMouse(document, 'mousemove', 520, 460);
        dispatchMouse(document, 'mouseup', 520, 460);

        expect(panel.style.width).toBe('720px');
        expect(panel.style.height).toBe('560px');
        expect(selectedName.textContent).toBe(character.name);
        expect(dialogueHistory.textContent).toContain('你好，Sam');
    });

    it('鼠标移动到角色交互框边缘时显示对应缩放方向', () => {
        const { system, panel } = createSystem();

        system.openInteractionPanel(system.characters[0]);
        system.applyInteractionPanelRect({
            left: 180,
            top: 100,
            width: 600,
            height: 500
        });

        dispatchMouse(panel, 'mousemove', 778, 350);
        expect(panel.dataset.resizeDirection).toBe('e');

        dispatchMouse(panel, 'mousemove', 181, 101);
        expect(panel.dataset.resizeDirection).toBe('nw');

        panel.dispatchEvent(new window.MouseEvent('mouseleave', { bubbles: true }));
        expect(panel.dataset.resizeDirection).toBeUndefined();
    });

    it('直接拖拽角色交互框右边缘时可以缩放', () => {
        const { system, panel } = createSystem();

        system.openInteractionPanel(system.characters[0]);
        system.applyInteractionPanelRect({
            left: 180,
            top: 100,
            width: 600,
            height: 500
        });

        dispatchMouse(panel, 'mousemove', 778, 350);
        dispatchMouse(panel, 'mousedown', 778, 350);
        dispatchMouse(document, 'mousemove', 838, 350);
        dispatchMouse(document, 'mouseup', 838, 350);

        expect(panel.style.width).toBe('660px');
        expect(panel.style.height).toBe('500px');
    });

    it('缩放时不会小于最小尺寸 300x200', () => {
        const { system, panel, resizeHandle } = createSystem();

        system.openInteractionPanel(system.characters[0]);

        dispatchMouse(resizeHandle, 'mousedown', 500, 500);
        dispatchMouse(document, 'mousemove', -200, -200);
        dispatchMouse(document, 'mouseup', -200, -200);

        expect(panel.style.width).toBe('300px');
        expect(panel.style.height).toBe('200px');
    });

    it('在视口右下边界附近缩放时会发生边界碰撞并限制尺寸', () => {
        const { system, panel, resizeHandle } = createSystem();

        system.openInteractionPanel(system.characters[0]);
        system.applyInteractionPanelRect({
            left: 700,
            top: 520,
            width: 300,
            height: 220
        });

        dispatchMouse(resizeHandle, 'mousedown', 998, 738);
        dispatchMouse(document, 'mousemove', 1200, 1200);
        dispatchMouse(document, 'mouseup', 1200, 1200);

        const width = parseFloat(panel.style.width);
        const height = parseFloat(panel.style.height);
        const left = parseFloat(panel.style.left);
        const top = parseFloat(panel.style.top);

        expect(width).toBe(324);
        expect(height).toBe(248);
        expect(left + width).toBeLessThanOrEqual(1024);
        expect(top + height).toBeLessThanOrEqual(768);
    });

    it('在缺少 window.innerWidth/innerHeight 时仍可回退到 documentElement 视口尺寸', () => {
        loadAppShell();
        setViewport({
            width: 900,
            height: 700,
            windowWidth: 0,
            windowHeight: 0
        });

        const { FairyTownSystem } = require(appPath);
        const system = new FairyTownSystem();

        expect(system.getViewportSize()).toEqual({
            width: 900,
            height: 700
        });
    });
});

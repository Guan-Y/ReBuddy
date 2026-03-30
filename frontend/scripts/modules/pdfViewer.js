import { StreamingMarkdownRenderer } from '../utils/renderer.js';
import { api } from '../services/api.js';
import { escapeHtml } from '../utils/helpers.js';

let currentPaper = null;
const elements = {}; // 缓存 DOM 元素

export function initPdfViewer() {
    // 获取元素
    elements.viewer = document.getElementById('pdfViewer');
    elements.closeBtn = document.getElementById('pdfCloseBtn');
    elements.frame = document.getElementById('pdfFrame');
    elements.fileName = document.getElementById('pdfFileName');
    elements.chatMessages = document.getElementById('paperChatMessages');
    elements.chatInput = document.getElementById('paperChatInput');
    elements.sendBtn = document.getElementById('paperSendButton');
    elements.displayArea = document.getElementById('pdfDisplayArea');
    elements.chatArea = document.getElementById('paperChatArea');
    elements.resizer = document.getElementById('pdfResizer');
    elements.toggleSidebarBtn = document.getElementById('pdfToggleSidebar');
    elements.toggleChatBtn = document.getElementById('chatToggleBtn');
    
    // 调试：检查元素是否存在
    console.log('PDF Viewer elements initialized:', {
        viewer: !!elements.viewer,
        toggleChatBtn: !!elements.toggleChatBtn,
        chatArea: !!elements.chatArea
    });
    
    // PDF功能开关
    elements.pdfSwitches = {
        net: document.getElementById('pdfSwitchNet'),
        deep: document.getElementById('pdfSwitchDeep')
    };
    
    // 绑定事件
    elements.closeBtn.addEventListener('click', closePDF);
    elements.sendBtn.addEventListener('click', sendPaperMessage);
    elements.chatInput.addEventListener('keypress', e => { 
        if (e.key === 'Enter') sendPaperMessage(); 
    });
    
    // 折叠/展开功能
    elements.toggleSidebarBtn.addEventListener('click', toggleSidebar);
    elements.toggleChatBtn.addEventListener('click', toggleChat);
    
    // 确保按钮可以被点击
    elements.toggleChatBtn.addEventListener('click', (e) => {
        e.preventDefault();
        e.stopPropagation();
        console.log('Toggle chat button clicked'); // 调试日志
        toggleChat();
    });
    
    // PDF功能开关点击事件
    Object.values(elements.pdfSwitches).forEach(switchElement => {
        switchElement.addEventListener('click', () => {
            switchElement.classList.toggle('active');
        });
    });
    
    // 拖拽调整功能
    initResizer();
    
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && elements.viewer.classList.contains('active')) closePDF();
    });
}

// 供外部调用
export async function openPDF(fileId, fileName) {
    // 记录当前页面状态
    const chatView = document.getElementById('chatView');
    const papersView = document.getElementById('papersView');
    
    // 判断当前页面状态：优先检查显示状态，然后检查active类
    let wasInChatView = false;
    if (chatView.style.display === 'flex' || chatView.classList.contains('active')) {
        wasInChatView = true;
    } else if (papersView.style.display === 'flex') {
        wasInChatView = false;
    } else {
        // 如果都不可见，默认认为在论文页面
        wasInChatView = false;
    }
    
    elements.viewer.classList.add('active');
    // 隐藏主内容区域
    papersView.style.display = 'none';
    chatView.style.display = 'none';
    
    // 确保文件空间正确显示
    const fileSpace = document.querySelector('.file-space');
    fileSpace.style.display = 'flex';
    fileSpace.style.visibility = 'visible';
    fileSpace.style.position = 'relative';
    fileSpace.style.zIndex = '1001';
    
    // 调整PDF阅读器布局，为左侧边栏留出空间
    elements.viewer.style.paddingLeft = '220px'; // 为左侧边栏留出空间
    elements.viewer.style.boxSizing = 'border-box';
    
    // 保存状态以便关闭时恢复
    elements.viewer.dataset.previousView = wasInChatView ? 'chat' : 'papers';

    elements.fileName.textContent = fileName;
    elements.frame.src = `/api/file/view?id=${encodeURIComponent(fileId)}`;
    currentPaper = { id: fileId, name: fileName };

    // 初始化欢迎语
    elements.chatMessages.innerHTML = `<div class="message ai">...正在加载 **${fileName}**...</div>`;

    try {
        await api.startPaperChat(fileId, fileName);
        elements.chatMessages.innerHTML = `
                <div class="message ai">
                    <div class="message-bubble">
                        <div class="markdown-content">
                            已加载 **${fileName}**，您可以开始询问关于这篇论文的任何问题！
                            
                            例如：
                            - 这篇论文的主要贡献是什么？
                            - 论文使用了什么方法？
                            - 实验结果如何？
                            - 有哪些局限性？
                        </div>
                    </div>
                </div>
            `;
    } catch (e) {
        console.error(e);
    }
}

async function closePDF() {
    if (currentPaper) {
        await api.endPaperChat(currentPaper.id);
    }
    elements.viewer.classList.remove('active');
    
    // 恢复主内容区域显示 - 使用保存的状态
    const previousView = elements.viewer.dataset.previousView || 'papers';
    const chatView = document.getElementById('chatView');
    const papersView = document.getElementById('papersView');
    
    if (previousView === 'chat') {
        // 恢复对话页面
        papersView.style.display = 'none';
        chatView.style.display = 'flex';
        chatView.classList.add('active'); // 确保添加active类
    } else {
        // 恢复论文列表页面
        papersView.style.display = 'flex';
        chatView.style.display = 'none';
        chatView.classList.remove('active'); // 确保移除active类
    }
    
    // 恢复PDF阅读器布局
    elements.viewer.style.paddingLeft = '';
    elements.viewer.style.boxSizing = '';
    
    // 确保文件空间恢复显示
    const fileSpace = document.querySelector('.file-space');
    fileSpace.style.display = 'flex';
    fileSpace.style.visibility = 'visible';
    fileSpace.style.position = '';
    fileSpace.style.zIndex = '';
    
    elements.frame.src = '';
    currentPaper = null;
    // 清除保存的状态
    delete elements.viewer.dataset.previousView;
}

async function sendPaperMessage() {
    const msg = elements.chatInput.value.trim();
    if (!msg || !currentPaper) return;

    // UI 更新逻辑（此处省略部分重复的 append HTML 代码，与原代码逻辑一致）
    addMessageToDom(msg, 'user');
    elements.chatInput.value = '';
    
    // 创建 AI 回复容器
    const aiContainer = addMessageToDom('', 'ai');
    const streamingContent = aiContainer.querySelector('.streaming-target');

    // 核心流式逻辑
    const renderer = new StreamingMarkdownRenderer();
    let isRendering = true;
    
    // 渲染循环
    const renderLoop = () => {
        if (!isRendering) return;
        const safeHtml = renderer.processChunk("");
        streamingContent.innerHTML = safeHtml + '<span class="inline-cursor">▋</span>';
        elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
        requestAnimationFrame(renderLoop);
    };
    requestAnimationFrame(renderLoop);

    try {
        const response = await fetch('/chat/stream', {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
            },
            body: JSON.stringify({
                query: msg,
                paper_id: currentPaper.id,
                net: elements.pdfSwitches.net.classList.contains('active'),
                kb: true,
                deep: elements.pdfSwitches.deep.classList.contains('active')
            })
        });
        
        // ... 此处复用原代码中的 reader 循环 ...
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            const chunk = decoder.decode(value, { stream: true });
            // 简单处理 data: json 逻辑
            const lines = chunk.split('\n');
            for(const line of lines) {
                if(line.startsWith('data: ')) {
                     try {
                        const data = JSON.parse(line.slice(6));
                        if(data.chunk) renderer.processChunk(data.chunk);
                     } catch(e){}
                }
            }
        }
    } catch (e) {
        console.error(e);
    } finally {
        isRendering = false;
        streamingContent.innerHTML = renderer.processChunk(""); // 移除光标
        // 高亮
        streamingContent.querySelectorAll('pre code').forEach(block => Prism.highlightElement(block));
    }
}

function addMessageToDom(text, sender) {
    const div = document.createElement('div');
    div.className = `message ${sender}`;
    const time = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
    
    if (sender === 'user') {
        div.innerHTML = `
            <div class="message-bubble">
                ${escapeHtml(text)}
                <div class="message-time">${time}</div>
            </div>
        `;
    } else {
        div.innerHTML = `
            <div class="message-bubble">
                <div class="markdown-content streaming-target"></div>
                <div class="message-time">${time}</div>
            </div>
        `;
    }
    
    elements.chatMessages.appendChild(div);
    elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
    return div;
}

/**
 * 切换侧边栏显示/隐藏
 */
function toggleSidebar() {
    const fileSpace = document.querySelector('.file-space');
    if (fileSpace.style.display === 'none') {
        // 显示侧边栏
        fileSpace.style.display = 'flex';
        fileSpace.style.visibility = 'visible';
        elements.viewer.style.paddingLeft = '220px';
        elements.toggleSidebarBtn.textContent = '☰';
    } else {
        // 隐藏侧边栏
        fileSpace.style.display = 'none';
        fileSpace.style.visibility = 'hidden';
        elements.viewer.style.paddingLeft = '0';
        elements.toggleSidebarBtn.textContent = '☰';
    }
}

/**
 * 切换对话区折叠/展开
 */
function toggleChat() {
    if (elements.chatArea.style.display === 'none') {
        // 显示对话区
        elements.chatArea.style.display = 'flex';
        elements.chatArea.style.visibility = 'visible';
        elements.displayArea.style.flex = '0 0 70%';
        elements.toggleChatBtn.textContent = '◀';
    } else {
        // 隐藏对话区
        elements.chatArea.style.display = 'none';
        elements.chatArea.style.visibility = 'hidden';
        elements.displayArea.style.flex = '1 1 auto';
        elements.toggleChatBtn.textContent = '▶';
    }
}

/**
 * 初始化拖拽调整功能
 */
function initResizer() {
    let isResizing = false;
    let startX = 0;
    let startWidth = 0;
    let animationId = null;
    
    elements.resizer.addEventListener('mousedown', (e) => {
        isResizing = true;
        startX = e.clientX;
        // 获取当前显示区域的实际宽度
        startWidth = elements.displayArea.offsetWidth;
        document.body.style.cursor = 'col-resize';
        e.preventDefault();
    });
    
    document.addEventListener('mousemove', (e) => {
        if (!isResizing) return;
        
        // 取消之前的动画帧
        if (animationId) {
            cancelAnimationFrame(animationId);
        }
        
        // 使用requestAnimationFrame优化性能
        animationId = requestAnimationFrame(() => {
            const deltaX = e.clientX - startX;
            // 获取实际可用宽度（考虑padding）
            const viewerStyle = window.getComputedStyle(elements.viewer);
            const paddingLeft = parseInt(viewerStyle.paddingLeft) || 0;
            const viewerWidth = elements.viewer.clientWidth - paddingLeft;
            let newDisplayWidth = startWidth + deltaX;
            let newChatWidth = viewerWidth - newDisplayWidth;
            
            // 限制最小和最大宽度
            const minDisplayWidth = viewerWidth * 0.3;
            const maxDisplayWidth = viewerWidth * 0.8;
            const minChatWidth = 40;
            
            if (newDisplayWidth < minDisplayWidth) {
                newDisplayWidth = minDisplayWidth;
                newChatWidth = viewerWidth - newDisplayWidth;
            } else if (newDisplayWidth > maxDisplayWidth) {
                newDisplayWidth = maxDisplayWidth;
                newChatWidth = viewerWidth - newDisplayWidth;
            } else if (newChatWidth < minChatWidth) {
                newChatWidth = minChatWidth;
                newDisplayWidth = viewerWidth - newChatWidth;
            }
            
            // 直接使用像素值，确保跟随鼠标
            elements.displayArea.style.width = `${newDisplayWidth}px`;
            elements.chatArea.style.width = `${newChatWidth}px`;
            elements.displayArea.style.flex = 'none';
            elements.chatArea.style.flex = 'none';
            
            // 如果对话区被隐藏，自动显示
            if (elements.chatArea.style.display === 'none' && newChatWidth > 100) {
                elements.chatArea.style.display = 'flex';
                elements.chatArea.style.visibility = 'visible';
                elements.toggleChatBtn.textContent = '◀';
            }
        });
    });
    
    document.addEventListener('mouseup', () => {
        if (isResizing) {
            isResizing = false;
            document.body.style.cursor = '';
            // 取消最后的动画帧
            if (animationId) {
                cancelAnimationFrame(animationId);
                animationId = null;
            }
            
            // 恢复flex布局，保持当前宽度比例
            const viewerStyle = window.getComputedStyle(elements.viewer);
            const paddingLeft = parseInt(viewerStyle.paddingLeft) || 0;
            const viewerWidth = elements.viewer.clientWidth - paddingLeft;
            const displayWidth = elements.displayArea.offsetWidth;
            const chatWidth = elements.chatArea.offsetWidth;
            
            // 确保比例正确
            const totalWidth = displayWidth + chatWidth;
            const displayPercent = (displayWidth / totalWidth * 100).toFixed(2);
            const chatPercent = (chatWidth / totalWidth * 100).toFixed(2);
            
            elements.displayArea.style.flex = `0 0 ${displayPercent}%`;
            elements.chatArea.style.flex = `0 0 ${chatPercent}%`;
            elements.displayArea.style.width = '';
            elements.chatArea.style.width = '';
        }
    });
}
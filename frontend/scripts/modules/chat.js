import { StreamingMarkdownRenderer } from '../utils/renderer.js';
import { escapeHtml } from '../utils/helpers.js';

// DOM 元素缓存
const elements = {
    // 视图容器
    papersView: document.getElementById('papersView'),
    chatView: document.getElementById('chatView'),
    
    // 主页聊天相关 - 英雄区
    inputMain: document.getElementById('chatInputMain'),
    sendBtnMain: document.getElementById('sendButtonMain'),
    
    // 聊天页面相关
    messages: document.getElementById('chatMessages'),
    input: document.getElementById('chatInput'),
    sendBtn: document.getElementById('sendButton'),
    typing: document.getElementById('typingIndicator'),
    
    // 开关状态 - 主页英雄区
    switchesMain: {
        net: document.getElementById('switchNetMain'),
        kb: document.getElementById('switchKbMain'),
        deep: document.getElementById('switchDeepMain')
    },
    
    // 开关状态 - 对话页面
    switches: {
        net: document.getElementById('switchNet'),
        kb: document.getElementById('switchKb'),
        deep: document.getElementById('switchDeep')
    }
};



/**
 * 模块初始化
 */
export function initChat() {
    console.log('Initializing Chat Module...');
    
    // 监听侧边栏的显示聊天视图事件
    document.addEventListener('show-chat-view', async () => {
        await showChatView();
    });
    
    // 绑定主页聊天事件 - 英雄区
    elements.sendBtnMain.addEventListener('click', handleSendMessageFromMain);
    elements.inputMain.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSendMessageFromMain();
    });
    
    
    
    // 绑定对话页面聊天事件
    elements.sendBtn.addEventListener('click', handleSendMessage);
    elements.input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') handleSendMessage();
    });
    
    // 绑定功能开关点击事件 - 主页英雄区
    Object.values(elements.switchesMain).forEach(switchElement => {
        switchElement.addEventListener('click', () => {
            switchElement.classList.toggle('active');
            // 同步状态到对话页面
            const switchType = switchElement.id.replace('Main', '');
            const targetSwitch = elements.switches[switchType];
            if (targetSwitch) {
                targetSwitch.classList.toggle('active', switchElement.classList.contains('active'));
            }
        });
    });
    
    // 绑定功能开关点击事件 - 对话页面
    Object.values(elements.switches).forEach(switchElement => {
        switchElement.addEventListener('click', () => {
            switchElement.classList.toggle('active');
            // 同步状态到主页英雄区
            const switchType = switchElement.id;
            const targetSwitch = elements.switchesMain[switchType];
            if (targetSwitch) {
                targetSwitch.classList.toggle('active', switchElement.classList.contains('active'));
            }
        });
    });
    
    
    
    
    
    // 监听会话状态变化
    document.addEventListener('conversationChanged', (event) => {
        console.log('📢 接收到会话状态变化通知:', event.detail);
        
        // 更新输入框状态，确保可以正常输入
        if (elements.input.disabled) {
            setInputState(true);
        }
        
        // 如果当前在聊天视图且没有活跃对话，显示欢迎消息
        if (elements.chatView.style.display === 'flex' && !event.detail.hasActiveConversation) {
            window.conversationManager.clearChatMessages();
            window.conversationManager.addWelcomeMessage();
        }
        
        // 确保输入框聚焦
        if (elements.chatView.style.display === 'flex') {
            setTimeout(() => elements.input.focus(), 100);
        }
    });
    
    // 初始聚焦主页输入框
    elements.inputMain.focus();
}

/**
 * 显示论文列表视图
 */
function showPapersView() {
    elements.papersView.style.display = 'flex';
    elements.chatView.style.display = 'none';
    elements.chatView.classList.remove('active');
    
    // 确保文件空间始终可见
    const fileSpace = document.querySelector('.file-space');
    fileSpace.style.display = 'flex';
    fileSpace.style.visibility = 'visible';
    fileSpace.style.position = 'relative';
    fileSpace.style.zIndex = '1001';
    
    // 同步开关状态回主页
    if (elements.switchesMain.net && elements.switches.net) {
        elements.switchesMain.net.classList.toggle('active', elements.switches.net.classList.contains('active'));
    }
    if (elements.switchesMain.kb && elements.switches.kb) {
        elements.switchesMain.kb.classList.toggle('active', elements.switches.kb.classList.contains('active'));
    }
    if (elements.switchesMain.deep && elements.switches.deep) {
        elements.switchesMain.deep.classList.toggle('active', elements.switches.deep.classList.contains('active'));
    }
    
    // 聚焦主页输入框
    setTimeout(() => elements.inputMain.focus(), 100);
}

/**
 * 显示对话视图
 */
export async function showChatView() {
    elements.papersView.style.display = 'none';
    elements.chatView.style.display = 'flex';
    elements.chatView.classList.add('active');
    
    // 确保文件空间始终可见
    const fileSpace = document.querySelector('.file-space');
    if (fileSpace) {
        fileSpace.style.display = 'flex';
        fileSpace.style.visibility = 'visible';
        fileSpace.style.position = 'relative';
        fileSpace.style.zIndex = '1001';
    }
    
    // 调用对话管理器的 showChatView 方法来处理消息加载
    await window.conversationManager.showChatView();
    
    // 如果没有活跃对话，创建一个新对话
    if (!window.conversationManager.hasActiveConversation()) {
        window.conversationManager.createNewConversation();
    }
    
    // 聚焦输入框
    setTimeout(() => elements.input.focus(), 100);
}

/**
 * 主页聊天处理函数
 */
async function handleSendMessageFromMain() {
    // 使用Gemini滚动管理器获取当前输入框的值
    const msg = window.geminiScrollManager.getCurrentInputValue();
    if (!msg) return;

    // 1. 获取当前开关状态
    const switchStates = window.geminiScrollManager.getCurrentSwitchStates();

    // 2. 同步开关状态到对话页面
    if (elements.switches.net) {
        elements.switches.net.classList.toggle('active', switchStates.net);
    }
    if (elements.switches.kb) {
        elements.switches.kb.classList.toggle('active', switchStates.kb);
    }
    if (elements.switches.deep) {
        elements.switches.deep.classList.toggle('active', switchStates.deep);
    }

    // 3. 确保有活跃对话（如果从主界面发送消息，总是创建新对话）
    await window.conversationManager.createNewConversation();
    
    // 4. 切换到对话视图
    await showChatView();
    
    // 5. 清空当前输入框
    window.geminiScrollManager.clearCurrentInput();
    
    // 6. 直接调用发送消息逻辑，传递消息内容，并标记来自主页面
    await sendMessageWithContent(msg, true);
}

/**
 * 发送消息主逻辑
 */
async function handleSendMessage() {
    const msg = elements.input.value.trim();
    if (!msg) return;

    // 清空输入框
    elements.input.value = '';
    
    // 调用通用发送函数
    await sendMessageWithContent(msg);
}

/**

 * 通用发送消息逻辑（可指定消息内容）

 */

async function sendMessageWithContent(msg, fromMainPage = false) {

    let conversationId = null;

    

    // 0. 验证和确保有活跃对话

    

        if (fromMainPage) {

    

            // 从主页面发送，总是创建新对话

    

            await window.conversationManager.createNewConversation();

    

            conversationId = window.conversationManager.getActiveConversationId();

    

        } else {

    

            // 验证当前活跃对话的有效性

    

            const validation = window.conversationManager.validateActiveConversation();

    

            

    

            if (!validation.isValid) {

    

                console.error('无法获取有效的对话ID');

    

                appendMessage('无法发送消息：当前对话无效，请返回主界面重新开始', 'system');

    

                return;

    

            }

    

            

    

            conversationId = validation.conversationId;

    

        }

    

        

    

        console.log('🔍 准备发送消息，使用会话ID:', conversationId);
    
    // 1. UI 状态更新：显示用户消息，禁用输入
    appendMessage(msg, 'user');
    setInputState(false);
    showTyping();

    // 2. 准备 AI 回复容器
    const aiMessageContainer = createAiMessageContainer();
    const streamingContentDiv = aiMessageContainer.querySelector('.streaming-target');

    // 3. 初始化 Markdown 渲染器
    const renderer = new StreamingMarkdownRenderer();
    let isRendering = true;

    // 4. 启动 UI 渲染循环 (RequestAnimationFrame)
    // 这种机制把数据接收和 UI 渲染解耦，保证高性能
    const uiRenderLoop = () => {
        if (!isRendering) return;
        
        // 获取当前渲染结果
        let html = renderer.processChunk(""); 
        
        // 物理挂载光标
        html += '<span class="inline-cursor">▋</span>';
        
        // 更新 DOM
        if (streamingContentDiv.innerHTML !== html) {
            streamingContentDiv.innerHTML = html;
            scrollToBottom();
        }
        
        requestAnimationFrame(uiRenderLoop);
    };
    requestAnimationFrame(uiRenderLoop);

    try {
        hideTyping(); // 开始流式接收前隐藏 "正在输入..."
        
        // 5. 发起 Fetch 请求
        // 注意：流式请求通常需要直接操作 response body，所以这里没有封装进 api.js
        // 使用已经验证过的会话ID
        console.log('🔍 发送请求到会话:', conversationId);
        
        const endpoint = `/conversations/${conversationId}/stream`;
        const requestBody = {
            query: msg,
            net: elements.switches.net ? elements.switches.net.classList.contains('active') : false,
            kb: elements.switches.kb ? elements.switches.kb.classList.contains('active') : false,
            deep: elements.switches.deep ? elements.switches.deep.classList.contains('active') : false
        };
        
        console.log('🔍 请求体:', requestBody);
        
        const response = await fetch(endpoint, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
            },
            body: JSON.stringify(requestBody)
        });

        if (!response.ok) {
            // 如果是404错误（对话不存在），尝试创建新对话并重试
            if (response.status === 404) {
                console.log('❌ 对话不存在，创建新对话并重试');
                await window.conversationManager.createNewConversation();
                
                // 获取新的对话ID并重试
                const newConversationId = window.conversationManager.getActiveConversationId();
                console.log('🔄 使用新会话ID重试:', newConversationId);
                
                const retryEndpoint = `/conversations/${newConversationId}/stream`;
                
                const retryRequestBody = {
                    query: msg,
                    net: elements.switches.net ? elements.switches.net.classList.contains('active') : false,
                    kb: elements.switches.kb ? elements.switches.kb.classList.contains('active') : false,
                    deep: elements.switches.deep ? elements.switches.deep.classList.contains('active') : false
                };
                
                const retryResponse = await fetch(retryEndpoint, {
                    method: 'POST',
                    headers: { 
                        'Content-Type': 'application/json',
                        'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
                    },
                    body: JSON.stringify(retryRequestBody)
                });
                
                if (!retryResponse.ok) {
                    throw new Error(`重试失败: HTTP Error ${retryResponse.status}`);
                }
                
                // 使用重试的响应继续处理
                response = retryResponse;
                console.log('✅ 重试成功，继续处理响应');
            } else {
                throw new Error(`HTTP Error ${response.status}`);
            }
        }

        // 6. 读取流数据
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            // 解码二进制流
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || ''; // 保留未完整的行

            for (const line of lines) {
                const trimmed = line.trim();
                if (!trimmed.startsWith('data: ')) continue;

                try {
                    const jsonStr = trimmed.slice(6);
                    if (jsonStr === '[DONE]') break;

                    const data = JSON.parse(jsonStr);

                    // 核心：喂数据给渲染器
                    if (data && typeof data.chunk === 'string') {
                        renderer.processChunk(data.chunk);
                    }

                    console.log('Received chunk:', data);
                    
                    if (data && data.error) {
                        streamingContentDiv.innerHTML += `<br><span style="color:red">Error: ${data.error}</span>`;
                    }
                } catch (e) {
                    // console.warn('JSON parse error in stream', e);
                }
            }
        }

    } catch (error) {
        console.error('Chat Error:', error);
        streamingContentDiv.innerHTML += `<br><span style="color:red">[连接中断: ${error.message}]</span>`;
    } finally {
        // 7. 收尾工作
        isRendering = false; // 停止渲染循环
        
        // 最后一次渲染，移除光标
        streamingContentDiv.innerHTML = renderer.processChunk("");
        
        // 触发 Prism 代码高亮
        if (typeof Prism !== 'undefined') {
            streamingContentDiv.querySelectorAll('pre code').forEach(block => Prism.highlightElement(block));
        }

        // 恢复输入框
        setInputState(true);
        scrollToBottom();
    }
}

// --- 辅助函数 ---

function appendMessage(text, sender) {
    const div = document.createElement('div');
    div.className = `message ${sender}`;
    const time = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
    
    div.innerHTML = `
        <div class="message-bubble">
            ${sender === 'user' ? escapeHtml(text) : `<div class="markdown-content">${text}</div>`}
            <div class="message-time">${time}</div>
        </div>
    `;
    elements.messages.appendChild(div);
    scrollToBottom();
}

function createAiMessageContainer() {
    const div = document.createElement('div');
    div.className = 'message ai';
    const time = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
    div.innerHTML = `
        <div class="message-bubble">
            <div class="markdown-content streaming-target"></div>
            <div class="message-time">${time}</div>
        </div>
    `;
    elements.messages.appendChild(div);
    return div;
}

function setInputState(enabled) {
    elements.input.disabled = !enabled;
    elements.sendBtn.disabled = !enabled;
    if (enabled) elements.input.focus();
}

function showTyping() {
    elements.typing.style.display = 'block';
    scrollToBottom();
}

function hideTyping() {
    elements.typing.style.display = 'none';
}

function scrollToBottom() {
    // 平滑滚动到底部
    elements.messages.scrollTo({
        top: elements.messages.scrollHeight,
        behavior: 'instant' 
    });
}
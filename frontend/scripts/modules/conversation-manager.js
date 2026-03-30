/**
 * 对话窗口管理模块
 * 处理多对话窗口的创建、切换、删除等功能
 */

class ConversationManager {
    constructor() {
        this.conversations = new Map(); // conversationId -> conversationData
        this.activeConversationId = null;
        this.isInitialized = false;
    }

    /**
     * 初始化对话管理器
     */
    async init() {
        if (this.isInitialized) return;
        
        try {
            // 加载用户的对话列表
            await this.loadConversations();
            
            // 绑定事件
            this.bindEvents();
            
            this.isInitialized = true;
            console.log('对话管理器初始化完成');
        } catch (error) {
            console.error('对话管理器初始化失败:', error);
        }
    }

    /**
     * 绑定事件
     */
    bindEvents() {
        // 文件空间的新对话按钮
        const newConversationBtn = document.getElementById('newConversationBtn');
        if (newConversationBtn) {
            newConversationBtn.addEventListener('click', async () => {
                await this.createNewConversationFromSidebar();
            });
        }
        
        // 聊天页面内的新建对话按钮（如果存在）
        const newChatBtn = document.getElementById('newChatBtn');
        if (newChatBtn) {
            newChatBtn.addEventListener('click', () => this.createNewConversation());
        }
    }

    /**
     * 加载对话列表
     */
    async loadConversations() {
        try {
            const response = await fetch('/conversations');
            const data = await response.json();
            
            if (data.status === 'success') {
                this.conversations.clear();
                data.conversations.forEach(conv => {
                    // 使用正确的字段名：后端返回的是 id，不是 conversation_id
                    const conversationId = conv.id || conv.conversation_id;
                    this.conversations.set(conversationId, conv);
                });
                
                // 如果有对话，激活第一个
                if (data.conversations.length > 0) {
                    const firstConv = data.conversations[0];
                    this.activeConversationId = firstConv.id || firstConv.conversation_id;
                }
                
                this.renderTabs();
            }
        } catch (error) {
            console.error('加载对话列表失败:', error);
        }
    }

    /**
     * 创建新对话
     */
    async createNewConversation() {
        try {
            // 检查当前是否有空对话
            const currentConversationId = this.activeConversationId;
            const currentConversation = currentConversationId ? 
                this.conversations.get(currentConversationId) : null;
            
            // 如果当前对话为空（没有消息），直接返回该对话
            if (currentConversation && 
                (!currentConversation.messages || currentConversation.messages.length === 0)) {
                console.log('📝 当前有空对话，直接返回');
                return currentConversationId;
            }
            
            const title = `对话 ${this.conversations.size + 1}`;
            
            const response = await fetch('/conversations', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ title })
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                const conversation = data.conversation;
                // 使用正确的字段名：后端返回的是 id，不是 conversation_id
                const conversationId = conversation.id || conversation.conversation_id;
                this.conversations.set(conversationId, conversation);
                this.activeConversationId = conversationId;
                
                // 触发事件通知侧边栏更新
                const event = new CustomEvent('conversation-created', {
                    detail: { conversationId, conversation }
                });
                document.dispatchEvent(event);
                console.log('📢 触发 conversation-created 事件:', conversationId);
                
                this.renderTabs();
                this.clearChatMessages();
                
                // 显示欢迎消息
                this.addWelcomeMessage();
            } else {
                console.error('创建对话失败:', data.message);
            }
        } catch (error) {
            console.error('创建对话失败:', error);
        }
    }

    /**
     * 从侧边栏创建新对话并返回主页面
     */
    async createNewConversationFromSidebar() {
        try {
            console.log('🔍 调试：开始创建新对话，当前是否在对话页面:', this.isChatViewVisible());
            
            // 检查当前是否有空对话
            const currentConversationId = this.activeConversationId;
            const currentConversation = currentConversationId ? 
                this.conversations.get(currentConversationId) : null;
            
            // 如果当前对话为空（没有消息），直接返回该对话
            if (currentConversation && 
                (!currentConversation.messages || currentConversation.messages.length === 0)) {
                console.log('📝 当前有空对话，直接返回');
                
                // 检查是否在对话页面，如果是则返回主页面
                if (this.isChatViewVisible()) {
                    console.log('🔍 调试：检测到在对话页面，准备返回主页面');
                    this.returnToMainView();
                    console.log('🔍 调试：已执行返回主页面操作');
                } else {
                    console.log('🔍 调试：当前不在对话页面，无需返回');
                }
                return;
            }
            
            // 检查是否在对话页面，如果是则返回主页面
            if (this.isChatViewVisible()) {
                console.log('🔍 调试：检测到在对话页面，准备返回主页面');
                this.returnToMainView();
                console.log('🔍 调试：已执行返回主页面操作');
            } else {
                console.log('🔍 调试：当前不在对话页面，无需返回');
            }
            
            // 创建新对话（但不立即显示，等待用户发送消息）
            const title = `对话 ${this.conversations.size + 1}`;
            
            // const response = await fetch('/conversations', {
            //     method: 'POST',
            //     headers: {
            //         'Content-Type': 'application/json'
            //     },
            //     body: JSON.stringify({ title })
            // });
            
            // const data = await response.json();
            
            // if (data.status === 'success') {
            //     const conversation = data.conversation;
            //     // 使用正确的字段名：后端返回的是 id，不是 conversation_id
            //     const conversationId = conversation.id || conversation.conversation_id;
            //     this.conversations.set(conversationId, conversation);
                
            //     // 设置为活跃对话，但不立即显示聊天界面
            //     this.activeConversationId = conversationId;
                
            //     // 更新侧边栏显示（如果有的话）
            //     this.updateSidebarDisplay();
                
            //     console.log('✅ 新对话已创建，等待用户发送消息:', conversationId);
            // } else {
            //     console.error('❌ 创建对话失败:', data.message);
            // }

        } catch (error) {
            console.error('❌ 创建对话失败:', error);
        }
    }

    /**
     * 检查聊天视图是否可见
     */
    isChatViewVisible() {
        const chatView = document.getElementById('chatView');
        const papersView = document.getElementById('papersView');
        
        const chatVisible = chatView && chatView.style.display !== 'none';
        const papersHidden = papersView && (
            papersView.style.display === 'none' || 
            papersView.style.display === ''
        );
        
        console.log('🔍 调试：chatView.display =', chatView ? chatView.style.display : 'null');
        console.log('🔍 调试：papersView.display =', papersView ? papersView.style.display : 'null');
        console.log('🔍 调试：chatVisible =', chatVisible, 'papersHidden =', papersHidden);
        
        return chatVisible && papersHidden;
    }

    /**
     * 返回主页面
     */
    returnToMainView() {
        console.log('🔍 调试：开始执行返回主页面操作');
        
        const chatView = document.getElementById('chatView');
        const papersView = document.getElementById('papersView');
        
        console.log('🔍 调试：修改前 - chatView.display =', chatView ? chatView.style.display : 'null');
        console.log('🔍 调试：修改前 - papersView.display =', papersView ? papersView.style.display : 'null');
        
        // 强制隐藏聊天视图
        if (chatView) {
            chatView.style.display = 'none';
            chatView.classList.remove('active');
        }
        
        // 强制显示论文列表视图
        if (papersView) {
            papersView.style.display = 'flex';
            papersView.style.visibility = 'visible';
        }
        
        // 确保文件空间始终可见
        const fileSpace = document.querySelector('.file-space');
        if (fileSpace) {
            fileSpace.style.display = 'flex';
            fileSpace.style.visibility = 'visible';
            fileSpace.style.position = 'relative';
            fileSpace.style.zIndex = '1001';
        }
        
        console.log('🔍 调试：修改后 - chatView.display =', chatView ? chatView.style.display : 'null');
        console.log('🔍 调试：修改后 - papersView.display =', papersView ? papersView.style.display : 'null');
        console.log('✅ 调试：返回主页面操作完成');
    }

    /**
     * 显示聊天界面
     * @param {boolean} skipMessageLoad - 是否跳过消息加载（从 switchToConversation 调用时使用）
     */
    async showChatView(skipMessageLoad = false) {
        const chatView = document.getElementById('chatView');
        const papersView = document.getElementById('papersView');
        
        if (chatView) chatView.style.display = 'flex';
        if (papersView) papersView.style.display = 'none';
        
        // 确保文件空间始终可见
        const fileSpace = document.querySelector('.file-space');
        if (fileSpace) {
            fileSpace.style.display = 'flex';
            fileSpace.style.visibility = 'visible';
            fileSpace.style.position = 'relative';
            fileSpace.style.zIndex = '1001';
        }
        
        // this.renderTabs(); // 移除对话标签渲染
        this.clearChatMessages();
        
        // 如果有活跃对话且没有跳过加载，加载其消息；否则显示欢迎消息
        if (this.hasActiveConversation() && !skipMessageLoad) {
            await this.loadConversationMessages(this.activeConversationId);
        } else if (!this.hasActiveConversation()) {
            this.addWelcomeMessage();
        }
    }

    /**
     * 更新侧边栏显示（可选功能）
     */
    updateSidebarDisplay() {
        // 可以在这里添加侧边栏的对话列表显示逻辑
        // 比如显示最近使用的对话等
    }

    /**
     * 切换到指定对话
     */
    async switchToConversation(conversationId) {
        if (!this.conversations.has(conversationId)) {
            console.error('对话不存在:', conversationId);
            // 尝试重新加载对话列表
            await this.loadConversations();
            // 再次检查
            if (!this.conversations.has(conversationId)) {
                this.addErrorMessage('切换失败：对话不存在');
                return;
            }
        }
        
        try {
            console.log('🔄 开始切换到对话:', conversationId);
            
            // 如果已经是当前对话，无需切换
            if (this.activeConversationId === conversationId) {
                console.log('⚠️ 已经是当前对话，无需切换');
                return;
            }
            
            // 保存当前对话的窗口位置
            if (this.activeConversationId) {
                await this.updateConversationPosition(this.activeConversationId, this.getCurrentTabPosition());
            }
            
            // 更新活跃对话ID
            this.activeConversationId = conversationId;
            console.log('✅ 更新活跃对话ID为:', this.activeConversationId);
            
            // 立即通知聊天模块状态变化（在加载消息前）
            this.notifyChatModuleOfConversationChange();
            
            // 更新标签样式 - 已移除
            // this.updateTabStyles();
            
            // 加载对话消息
            await this.loadConversationMessages(conversationId);
            
            // 确保聊天视图可见
            if (!this.isChatViewVisible()) {
                // 跳过消息加载，因为已经加载了
                await this.showChatView(true);
            }
            
            // 再次通知状态变化（确保同步）
            this.notifyChatModuleOfConversationChange();
            
            console.log('✅ 对话切换完成:', conversationId);
            
        } catch (error) {
            console.error('❌ 切换对话失败:', error);
            this.addErrorMessage('切换对话时发生错误');
        }
    }

    /**
     * 删除对话
     */
    async deleteConversation(conversationId) {
        if (!this.conversations.has(conversationId)) return;
        
        try {
            const response = await fetch(`/conversations/${conversationId}`, {
                method: 'DELETE'
            });
            
            const data = await response.json();
            
            if (data.status === 'success') {
                // 从本地会话列表中移除
                this.conversations.delete(conversationId);
                
                // 如果删除的是当前活跃对话，需要切换到其他对话
                if (this.activeConversationId === conversationId) {
                    const remainingConversations = Array.from(this.conversations.keys());
                    
                    if (remainingConversations.length > 0) {
                        // 选择最新创建的对话作为活跃对话（而不是最新更新的）
                        const sortedConversations = remainingConversations.map(id => ({
                            id,
                            conversation: this.conversations.get(id)
                        })).sort((a, b) => new Date(b.conversation.created_at) - new Date(a.conversation.created_at));
                        
                        this.activeConversationId = sortedConversations[0].id;
                        console.log('删除活跃对话后切换到最新创建的对话:', this.activeConversationId);
                        
                        // 重新加载消息
                        await this.loadConversationMessages(this.activeConversationId);
                    } else {
                        // 没有其他对话，返回主界面
                        this.activeConversationId = null;
                        console.log('所有对话已删除，返回主界面');
                        this.returnToMainView();
                    }
                }
                
                // 重新渲染标签 - 已移除
                // this.renderTabs();
                
                // 通知聊天模块更新状态
                this.notifyChatModuleOfConversationChange();
                
            } else {
                console.error('删除对话失败:', data.message);
                this.addErrorMessage('删除对话失败: ' + data.message);
            }
        } catch (error) {
            console.error('删除对话失败:', error);
            this.addErrorMessage('删除对话时发生错误');
        }
    }

    /**
     * 更新对话标题
     * 暂未实现
     */
    async updateConversationTitle(conversationId, title) {
        return
    }

    /**
     * 加载对话消息
     */
    async loadConversationMessages(conversationId) {
        try {
            console.log('加载对话消息:', conversationId);
            const response = await fetch(`/conversations/${conversationId}/messages`);
            const data = await response.json();
            
            if (data.status === 'success') {
                console.log('成功加载消息:', data.messages.length, '条');
                this.clearChatMessages();
                
                // 渲染消息
                const chatMessages = document.getElementById('chatMessages');
                if (data.messages && data.messages.length > 0) {
                    data.messages.forEach(msg => {
                        this.addMessage(msg.content, msg.type, msg.timestamp);
                    });
                } else {
                    // 如果没有消息，显示欢迎消息
                    this.addWelcomeMessage();
                }
                
                // 滚动到底部
                chatMessages.scrollTop = chatMessages.scrollHeight;
            } else {
                console.error('加载消息失败:', data.message);
                this.addErrorMessage('加载对话消息失败: ' + data.message);
            }
        } catch (error) {
            console.error('加载对话消息失败:', error);
            this.addErrorMessage('加载对话消息时发生错误');
        }
    }

    /**
     * 渲染对话标签 - 已移除
     */
    renderTabs() {
        // 对话标签功能已移除，保留方法避免报错
        return;
        
        /*
        const tabsContainer = document.getElementById('tabsContainer');
        if (!tabsContainer) return;
        
        tabsContainer.innerHTML = '';
        
        // 按更新时间排序（最新的在前）
        const sortedConversations = Array.from(this.conversations.values())
            .sort((a, b) => new Date(b.updated_at) - new Date(a.updated_at));
        
        sortedConversations.forEach(conversation => {
            const tab = this.createTabElement(conversation);
            tabsContainer.appendChild(tab);
        });
        
        // 更新标签样式
        this.updateTabStyles();
        
        // 使标签可拖拽排序
        this.makeTabsSortable();
        */
    }

    /**
     * 创建标签元素 - 已移除
     */
    createTabElement(conversation) {
        // 对话标签功能已移除，返回空元素避免报错
        return document.createElement('div');
        
        /*
        const tab = document.createElement('div');
        tab.className = 'conversation-tab';
        // 使用正确的字段名：后端返回的是 id，不是 conversation_id
        const conversationId = conversation.id || conversation.conversation_id;
        tab.dataset.conversationId = conversationId;
        
        if (conversationId === this.activeConversationId) {
            tab.classList.add('active');
        }
        
        // 标题
        const title = document.createElement('span');
        title.className = 'tab-title';
        title.textContent = conversation.title;
        title.title = conversation.title; // 悬浮显示完整标题
        
        // 关闭按钮
        const closeBtn = document.createElement('span');
        closeBtn.className = 'tab-close';
        closeBtn.innerHTML = '×';
        closeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.deleteConversation(conversationId);
        });
        
        tab.appendChild(title);
        tab.appendChild(closeBtn);
        
        // 点击切换对话
        tab.addEventListener('click', () => {
            this.switchToConversation(conversationId);
        });
        
        // 双击编辑标题
        tab.addEventListener('dblclick', (e) => {
            e.stopPropagation();
            this.editTabTitle(conversationId, title);
        });
        
        return tab;
        */
    }

    /**
     * 更新标签样式 - 已移除
     */
    updateTabStyles() {
        // 对话标签功能已移除，保留方法避免报错
        return;
    }

    /**
     * 编辑标签标题 - 已移除
     */
    editTabTitle(conversationId, titleElement) {
        // 对话标签功能已移除，保留方法避免报错
        return;
    }

    /**
     * 使标签可拖拽排序 - 已移除
     */
    makeTabsSortable() {
        // 对话标签功能已移除，保留方法避免报错
        return;
    }

    /**
     * 获取拖拽后的位置 - 已移除
     */
    getDragAfterElement(container, x) {
        // 对话标签功能已移除，保留方法避免报错
        return null;
    }

    /**
     * 重新排序对话 - 已移除
     */
    async reorderConversations() {
        // 对话标签功能已移除，保留方法避免报错
        return;
    }

    /**
     * 获取当前标签位置 - 已移除
     */
    getCurrentTabPosition() {
        // 对话标签功能已移除，保留方法避免报错
        return 1;
    }

    /**
     * 更新对话位置 - 已移除
     */
    async updateConversationPosition(conversationId, position) {
        // 对话标签功能已移除，保留方法避免报错
        return;
    }

    /**
     * 清空聊天消息
     */
    clearChatMessages() {
        const chatMessages = document.getElementById('chatMessages');
        if (chatMessages) {
            chatMessages.innerHTML = '';
        }
    }

    /**
     * 添加欢迎消息
     */
    addWelcomeMessage() {
        this.addMessage(
            `你好！我是用于文献调研的 AI 助手  
            ### 我可以：  
            - ✅ 搜索文献  
            - ✅ 下载文献  
            - ✅ 总结论文  
            - ✅ 还有瞎说一通  

            > 提示：试试问"最近有哪些 shit 工作"`,
            'ai',
            new Date().toISOString()
        );
    }
    
    /**
     * 添加错误消息
     */
    addErrorMessage(message) {
        this.addMessage(
            `❌ 错误：${message}`,
            'system',
            new Date().toISOString()
        );
    }

    /**
     * 添加消息到聊天区域
     */
    addMessage(content, type, timestamp) {
        const chatMessages = document.getElementById('chatMessages');
        if (!chatMessages) return;
        
        // 映射消息类型：后端返回的 'assistant' 需要映射为 'ai'
        const mappedType = type === 'assistant' ? 'ai' : type;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${mappedType}`;
        
        // 获取时间
        const time = timestamp ? 
            new Date(timestamp).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' }) :
            new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
        
        // 使用与 chat.js 相同的 HTML 结构
        if (mappedType === 'system') {
            // 系统消息特殊处理
            messageDiv.innerHTML = `
                <div class="message-bubble">
                    <div class="system-content">${this.escapeHtml(content)}</div>
                    <div class="message-time">${time}</div>
                </div>
            `;
        } else if (mappedType === 'user') {
            // 用户消息：转义 HTML，不使用 markdown
            messageDiv.innerHTML = `
                <div class="message-bubble">
                    ${this.escapeHtml(content)}
                    <div class="message-time">${time}</div>
                </div>
            `;
        } else {
            // AI 消息：使用 markdown
            messageDiv.innerHTML = `
                <div class="message-bubble">
                    <div class="markdown-content">${marked.parse(content)}</div>
                    <div class="message-time">${time}</div>
                </div>
            `;
        }
        
        chatMessages.appendChild(messageDiv);
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        // 代码高亮（仅对 AI 消息）
        if (mappedType === 'ai' && typeof Prism !== 'undefined') {
            const markdownContent = messageDiv.querySelector('.markdown-content');
            if (markdownContent) {
                Prism.highlightAllUnder(markdownContent);
            }
        }
    }
    
    /**
     * HTML 转义函数
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * 获取当前活跃对话ID
     */
    getActiveConversationId() {
        return this.activeConversationId;
    }

    /**
     * 检查是否有活跃对话
     */
    hasActiveConversation() {
        return this.activeConversationId !== null && this.conversations.has(this.activeConversationId);
    }

    /**
     * 验证当前活跃对话的有效性
     * 只做验证，不自动创建对话
     * 返回验证结果对象 { isValid: boolean, conversationId: string|null }
     */
    validateActiveConversation() {
        console.log('🔍 验证活跃对话，当前ID:', this.activeConversationId);
        
        // 如果没有活跃对话
        if (!this.activeConversationId) {
            console.log('没有活跃对话');
            return { isValid: false, conversationId: null };
        }
        
        // 如果活跃对话不存在于本地列表中，说明可能已被删除
        if (!this.conversations.has(this.activeConversationId)) {
            console.log('活跃对话不存在于本地列表');
            return { isValid: false, conversationId: null };
        }
        
        // 验证通过
        console.log('✅ 活跃对话验证通过:', this.activeConversationId);
        return { isValid: true, conversationId: this.activeConversationId };
    }
    
    /**
     * 确保有活跃对话，如果没有则创建新对话
     * 主要用于从主界面进入对话时的逻辑
     */
    async ensureActiveConversation() {
        console.log('🔍 确保有活跃对话');
        
        const validation = this.validateActiveConversation();
        if (!validation.isValid) {
            console.log('没有有效对话，创建新对话');
            await this.createNewConversation();
        }
        
        return this.activeConversationId;
    }

    /**
     * 通知聊天模块会话状态已更改
     */
    notifyChatModuleOfConversationChange() {
        // 触发自定义事件，通知聊天模块
        const event = new CustomEvent('conversationChanged', {
            detail: {
                activeConversationId: this.activeConversationId,
                hasActiveConversation: this.hasActiveConversation()
            }
        });
        document.dispatchEvent(event);
    }
}

// 创建全局对话管理器实例
window.conversationManager = new ConversationManager();

// 导出模块
export default ConversationManager;
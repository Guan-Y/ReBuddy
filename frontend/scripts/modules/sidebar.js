/**
 * 现代化侧边栏管理模块
 * 实现可折叠侧边栏、历史对话管理等功能
 */

class SidebarManager {
    constructor() {
        this.sidebar = null;
        this.toggleBtn = null;
        this.historyList = null;
        this.isCollapsed = false;
        this.currentConversationId = 'default';
        this.conversations = new Map();
        
        // 绑定方法
        this.toggleSidebar = this.toggleSidebar.bind(this);
        this.handleHistoryClick = this.handleHistoryClick.bind(this);
        this.handleNewChat = this.handleNewChat.bind(this);
        this.handleKnowledgeBase = this.handleKnowledgeBase.bind(this);
        // this.handleFileUpload = this.handleFileUpload.bind(this);
        // this.clearHistory = this.clearHistory.bind(this);
        this.handleResize = this.handleResize.bind(this);
    }

    /**
     * 初始化侧边栏
     */
    init() {
        console.log('🔧 初始化侧边栏...');
        
        // 获取DOM元素
        this.sidebar = document.getElementById('sidebar');
        this.toggleBtn = document.getElementById('sidebarToggle');
        this.historyList = document.getElementById('historyList');
        this.newChatBtn = document.getElementById('newChatBtn');
        this.knowledgeBtn = document.getElementById('knowledgeBtn');
        this.historyClear = document.getElementById('historyClear');
        
        // 绑定事件
        this.bindEvents();
        
        // 绑定logo点击事件
        this.bindLogoClick();
        
        // 加载保存的状态
        this.loadSavedState();
        
        // 监听对话管理器事件
        this.setupConversationManagerEvents();
        
        // 设置键盘快捷键
        this.setupKeyboardShortcuts();
        
        // 添加搜索框
        this.addSearchBox();
        
        // 设置长按删除功能（移动端友好）
        this.setupLongPress();
        
        // 加载历史对话
        this.loadConversationHistory();
        
        console.log('✅ 侧边栏初始化完成');
    }

    /**
     * 绑定事件监听器
     */
    bindEvents() {
        // 侧边栏折叠
        this.toggleBtn.addEventListener('click', this.toggleSidebar);
        
        // 新对话按钮
        this.newChatBtn.addEventListener('click', this.handleNewChat);
        
        // 知识库按钮
        this.knowledgeBtn.addEventListener('click', this.handleKnowledgeBase);
        
        // 清空历史
        this.historyClear.addEventListener('click', this.deleteSelectedConversation);
        
        // 历史对话点击（事件委托）
        this.historyList.addEventListener('click', this.handleHistoryClick);
        
        // 窗口大小变化
        window.addEventListener('resize', this.handleResize);
    }

    /**
     * 绑定logo点击事件
     */
    bindLogoClick() {
        const logoText = document.querySelector('.logo-text');
        const logoIcon = document.querySelector('.logo-icon');
        const sidebarLogo = document.querySelector('.sidebar-logo');
        
        const handleLogoClick = () => {
            console.log('🏠 Logo点击，返回主界面');
            this.returnToMainView();
        };
        
        // 为logo相关元素添加点击事件
        if (logoText) logoText.addEventListener('click', handleLogoClick);
        if (logoIcon) logoIcon.addEventListener('click', handleLogoClick);
        if (sidebarLogo) sidebarLogo.addEventListener('click', handleLogoClick);
        
        // 添加鼠标样式，提示可点击
        if (logoText) logoText.style.cursor = 'pointer';
        if (logoIcon) logoIcon.style.cursor = 'pointer';
        if (sidebarLogo) sidebarLogo.style.cursor = 'pointer';
    }

    /**
     * 切换侧边栏折叠状态
     */
    toggleSidebar() {
        this.isCollapsed = !this.isCollapsed;
        this.sidebar.classList.toggle('collapsed', this.isCollapsed);
        
        // 保存状态到localStorage
        localStorage.setItem('sidebar-collapsed', this.isCollapsed);
        
        // 触发自定义事件
        this.dispatchEvent('sidebar-toggle', { isCollapsed: this.isCollapsed });
        
        console.log(`🔄 侧边栏${this.isCollapsed ? '折叠' : '展开'}`);
    }

    /**
     * 处理新对话
     */
    async handleNewChat() {
        console.log('💬 处理新对话请求');
        
        try {
            // 使用现有的对话管理器
            if (window.conversationManager) {
                // 检查当前是否有空对话
                const currentConversationId = window.conversationManager.getActiveConversationId();
                const currentConversation = currentConversationId ? 
                    window.conversationManager.conversations.get(currentConversationId) : null;
                
                // 如果当前对话为空（没有消息），直接返回该对话
                if (currentConversation && 
                    (!currentConversation.messages || currentConversation.messages.length === 0)) {
                    console.log('📝 当前有空对话，直接返回');
                    
                    // 更新当前对话ID和活动状态
                    this.currentConversationId = currentConversationId;
                    this.updateActiveConversation(currentConversationId);
                    
                    // 回到主界面
                    this.returnToMainView();
                    return;
                }
                
                // 创建新对话
                await window.conversationManager.createNewConversation();
                const newConversationId = window.conversationManager.getActiveConversationId();
                
                // 只添加新的对话项到列表顶部，避免重新渲染整个列表
                this.addNewConversationToTop(newConversationId);
                
                // 回到主界面
                this.returnToMainView();
            } else {
                // 降级处理：检查当前是否有空对话
                if (this.currentConversationId && this.conversations.has(this.currentConversationId)) {
                    const currentConversation = this.conversations.get(this.currentConversationId);
                    if (currentConversation && 
                        (!currentConversation.messages || currentConversation.messages.length === 0)) {
                        console.log('📝 当前有空对话，直接返回');
                        this.updateActiveConversation(this.currentConversationId);
                        this.returnToMainView();
                        return;
                    }
                }
                
                // 创建临时对话
                const conversationId = this.generateConversationId();
                this.addConversationToHistory({
                    id: conversationId,
                    title: '新对话',
                    preview: '开始新的对话...',
                    timestamp: new Date().toISOString(),
                    messages: []
                });
                this.switchToConversation(conversationId);
                // 回到主界面
                this.returnToMainView();
            }
        } catch (error) {
            console.error('处理新对话失败:', error);
        }
    }

    /**
     * 处理知识库按钮点击
     */
    handleKnowledgeBase() {
        console.log('📚 打开知识库');
        
        // 切换到知识库视图
        this.dispatchEvent('open-knowledge-base');
        
        // 直接调用知识库管理器的方法
        if (window.knowledgeBaseManager && typeof window.knowledgeBaseManager.showKnowledgeBaseView === 'function') {
            window.knowledgeBaseManager.showKnowledgeBaseView();
        } else {
            console.error('❌ 知识库管理器未初始化');
            this.showErrorToast('知识库功能暂时不可用');
        }
    }

    /**
     * 处理历史对话点击
     */
    handleHistoryClick(event) {
        // 如果点击的是删除按钮，不触发切换
        if (event.target.classList.contains('delete-history-btn')) {
            const historyItem = event.target.closest('.history-item');
            const conversationId = historyItem.dataset.conversationId;
            this.showDeleteConfirm(historyItem);
            return;
        }

        const historyItem = event.target.closest('.history-item');
        if (!historyItem) return;
        
        const conversationId = historyItem.dataset.conversationId;
        if (!conversationId) return;
        
        // 切换到指定对话
        this.switchToConversation(conversationId);
        
        // 加载对话内容
        this.loadConversationContent(conversationId);
    }

    /**
     * 切换到指定对话
     */
    async switchToConversation(conversationId) {
        try {
            // 更新当前对话ID
            this.currentConversationId = conversationId;
            
            // 更新UI状态
            this.updateActiveConversation(conversationId);
            
            // 使用对话管理器切换对话
            if (window.conversationManager) {
                await window.conversationManager.switchToConversation(conversationId);
            }
            
            // 触发对话切换事件
            this.dispatchEvent('conversation-switch', { conversationId });
            
            console.log(`🔄 切换到对话: ${conversationId}`);
        } catch (error) {
            console.error('切换对话失败:', error);
            this.showErrorToast('切换对话失败，请重试');
        }
    }

    /**
     * 更新活动对话状态
     */
    updateActiveConversation(conversationId) {
        // 如果当前已有活动对话且是同一个，避免重复操作
        const currentActive = this.historyList.querySelector('.history-item.active');
        if (currentActive && currentActive.dataset.conversationId === conversationId) {
            return;
        }
        
        // 移除当前活动状态
        if (currentActive) {
            currentActive.classList.remove('active');
        }
        
        // 添加新的活动状态
        const activeItem = this.historyList.querySelector(`[data-conversation-id="${conversationId}"]`);
        if (activeItem) {
            activeItem.classList.add('active');
        }
    }

    /**
     * 加载对话内容
     */
    async loadConversationContent(conversationId) {
        // 显示加载状态
        const historyItem = this.historyList.querySelector(`[data-conversation-id="${conversationId}"]`);
        if (historyItem) {
            historyItem.classList.add('loading');
        }
        
        try {
            // 首先隐藏所有其他视图，避免布局混乱
            this.hideAllOtherViews();
            
            // 使用对话管理器加载对话
            if (window.conversationManager) {
                await window.conversationManager.switchToConversation(conversationId);
                
                // 确保聊天视图可见 - 触发显示聊天视图事件
                this.dispatchEvent('show-chat-view');
            } else {
                // 降级处理：触发加载对话事件
                this.dispatchEvent('load-conversation', { conversationId });
            }
        } catch (error) {
            console.error('加载对话内容失败:', error);
            this.showErrorToast('加载对话失败，请重试');
        } finally {
            // 移除加载状态
            if (historyItem) {
                historyItem.classList.remove('loading');
            }
        }
    }

    /**
     * 隐藏所有其他视图（除了聊天视图）
     */
    hideAllOtherViews() {
        const viewsToHide = [
            'papersView',
            'pdfViewer',
            'knowledgeBaseView',
            'knowledgeBaseDetailView'
        ];
        
        viewsToHide.forEach(viewId => {
            const view = document.getElementById(viewId);
            if (view) {
                view.style.display = 'none';
                view.classList.remove('active');
            }
        });
        
        // 确保文件空间始终可见
        const fileSpace = document.querySelector('.file-space');
        if (fileSpace) {
            fileSpace.style.display = 'flex';
            fileSpace.style.visibility = 'visible';
            fileSpace.style.position = 'relative';
            fileSpace.style.zIndex = '1001';
        }
    }

    /**
     * 添加对话到历史列表
     */
    addConversationToHistory(conversation) {
        // 保存到内存
        this.conversations.set(conversation.id, conversation);
        
        // 创建历史项DOM
        const historyItem = this.createHistoryItem(conversation);
        
        // 添加到列表顶部
        this.historyList.insertBefore(historyItem, this.historyList.firstChild);
        
        // 保存到localStorage
        this.saveConversations();
    }

    /**
     * 将新对话添加到列表顶部（无闪烁）
     */
    addNewConversationToTop(conversationId) {
        if (!window.conversationManager || !conversationId) return;
        
        const conversation = window.conversationManager.conversations.get(conversationId);
        if (!conversation) return;
        
        // 更新当前对话ID
        this.currentConversationId = conversationId;
        
        // 创建新的历史项
        const historyItem = this.createHistoryItem({
            id: conversationId,
            title: conversation.title || '新对话',
            preview: conversation.last_message || conversation.messages?.[conversation.messages.length - 1]?.content || '开始新的对话...',
            timestamp: conversation.updated_at || conversation.created_at || new Date().toISOString()
        });
        
        // 添加到列表顶部
        if (this.historyList.firstChild) {
            this.historyList.insertBefore(historyItem, this.historyList.firstChild);
        } else {
            this.historyList.appendChild(historyItem);
        }
        
        // 更新活动状态
        this.updateActiveConversation(conversationId);
        
        // 添加淡入动画
        historyItem.style.opacity = '0';
        historyItem.style.transform = 'translateY(-10px)';
        
        requestAnimationFrame(() => {
            historyItem.style.transition = 'all 0.2s ease';
            historyItem.style.opacity = '1';
            historyItem.style.transform = 'translateY(0)';
        });
    }

    /**
     * 创建历史对话项DOM
     */
    createHistoryItem(conversation) {
        const div = document.createElement('div');
        div.className = 'history-item';
        div.dataset.conversationId = conversation.id;
        
        const timeAgo = this.getTimeAgo(conversation.timestamp);
        
        div.innerHTML = `
            <div class="history-icon">💬</div>
            <div class="history-content">
                <div class="history-title">${this.escapeHtml(conversation.title)}</div>
                <div class="history-preview">${this.escapeHtml(conversation.preview)}</div>
            </div>
            <div class="history-time">${timeAgo}</div>
            <button class="delete-history-btn" title="删除此对话">🗑️</button>
        `;
        
        return div;
    }

    /**
     * 更新对话信息
     */
    updateConversation(conversationId, updates) {
        const conversation = this.conversations.get(conversationId);
        if (!conversation) return;
        
        // 更新数据
        Object.assign(conversation, updates);
        conversation.timestamp = new Date().toISOString();
        
        // 更新DOM
        const historyItem = this.historyList.querySelector(`[data-conversation-id="${conversationId}"]`);
        if (historyItem) {
            const titleElement = historyItem.querySelector('.history-title');
            const previewElement = historyItem.querySelector('.history-preview');
            const timeElement = historyItem.querySelector('.history-time');
            
            if (titleElement) titleElement.textContent = conversation.title;
            if (previewElement) previewElement.textContent = conversation.preview;
            if (timeElement) timeElement.textContent = this.getTimeAgo(conversation.timestamp);
        }
        
        // 保存
        this.saveConversations();
    }

    /**
     * 通用的删除对话方法
     */
    async deleteConversationById(conversationId) {
        if (!conversationId) return;

        try {
            console.log('🗑️ 删除对话:', conversationId);

            // 调用管理器删除
            if (window.conversationManager) {
                await window.conversationManager.deleteConversation(conversationId);
            } else {
                this.conversations.delete(conversationId);
                this.saveConversations();
            }

            // 移除DOM
            const item = this.historyList.querySelector(`[data-conversation-id="${conversationId}"]`);
            if (item) item.remove();

            // 如果删除的是当前对话，处理后续
            if (this.currentConversationId === conversationId) {
                if (window.conversationManager?.conversations.size > 0) {
                    const newId = window.conversationManager.activeConversationId;
                    this.switchToConversation(newId);
                } else {
                    this.returnToMainView();
                    this.currentConversationId = null;
                }
            }

            this.dispatchEvent('conversation-deleted', { conversationId });
            this.showSuccessToast('对话已删除');
        } catch (error) {
            console.error('删除失败:', error);
            this.showErrorToast('删除失败，请重试');
        }
    }

    /**
     * 删除选中的对话
     */
    async deleteSelectedConversation() {
        // 如果没有有效选中项，提示用户先选择
        if (!this.currentConversationId || this.currentConversationId === 'default') {
            this.showErrorToast('请先选择一个对话进行删除');
            return;
        }

        const conversation = this.conversations.get(this.currentConversationId);
        const title = conversation?.title || '此对话';

        if (!confirm(`确定要删除对话 "${title}" 吗？此操作不可恢复。`)) {
            return;
        }

        // 使用通用删除方法
        await this.deleteConversationById(this.currentConversationId);
    }

    /**
     * 加载对话历史
     */
    async loadConversationHistory() {
        try {
            // 优先从conversation-manager加载后端数据
            if (window.conversationManager && window.conversationManager.isInitialized) {
                console.log('🔄 从conversation-manager同步对话数据');
                await window.conversationManager.loadConversations();
                this.syncWithConversationManager();
                return;
            }
            
            // 降级处理：从localStorage加载
            const saved = localStorage.getItem('conversations');
            if (saved) {
                const conversations = JSON.parse(saved);
                conversations.forEach(conv => {
                    this.conversations.set(conv.id, conv);
                    const historyItem = this.createHistoryItem(conv);
                    this.historyList.appendChild(historyItem);
                });
            }
        } catch (error) {
            console.error('❌ 加载对话历史失败:', error);
        }
    }

    /**
     * 保存对话到localStorage
     */
    saveConversations() {
        try {
            const conversations = Array.from(this.conversations.values());
            localStorage.setItem('conversations', JSON.stringify(conversations));
        } catch (error) {
            console.error('❌ 保存对话失败:', error);
        }
    }

    /**
     * 加载保存的状态
     */
    loadSavedState() {
        // 加载折叠状态
        const savedCollapsed = localStorage.getItem('sidebar-collapsed') === 'true';
        if (savedCollapsed) {
            this.isCollapsed = true;
            this.sidebar.classList.add('collapsed');
        }
        
        // 移动端默认折叠
        if (window.innerWidth <= 768) {
            this.isCollapsed = true;
            this.sidebar.classList.add('collapsed');
        }
    }

    /**
     * 处理窗口大小变化
     */
    handleResize() {
        const isMobile = window.innerWidth <= 768;
        
        // 移动端响应式处理
        if (isMobile) {
            // 移动端默认折叠
            this.sidebar.classList.add('collapsed');
            this.sidebar.classList.remove('open');
            
            // 添加移动端遮罩层
            this.addMobileOverlay();
        } else {
            // 桌面端恢复保存的状态
            const savedCollapsed = localStorage.getItem('sidebar-collapsed') === 'true';
            this.sidebar.classList.toggle('collapsed', savedCollapsed);
            
            // 移除移动端遮罩层
            this.removeMobileOverlay();
        }
        
        // 触发响应式变化事件
        this.dispatchEvent('sidebar-responsive', { isMobile });
    }

    /**
     * 设置对话管理器事件监听
     */
    setupConversationManagerEvents() {
        // 等待对话管理器初始化完成
        const checkConversationManager = () => {
            if (window.conversationManager && window.conversationManager.isInitialized) {
                // 监听对话列表变化
                document.addEventListener('conversations-loaded', (e) => {
                    this.syncWithConversationManager();
                });
                
                // 监听新对话创建
                document.addEventListener('conversation-created', (e) => {
                    this.syncWithConversationManager();
                });
                
                // 监听对话切换
                document.addEventListener('conversation-switched', (e) => {
                    const { conversationId } = e.detail;
                    this.switchToConversation(conversationId);
                });
                
                // 初始同步
                this.syncWithConversationManager();
            } else {
                // 如果对话管理器还未初始化，稍后重试
                setTimeout(checkConversationManager, 100);
            }
        };
        
        checkConversationManager();
    }

    /**
     * 与对话管理器同步
     */
    async syncWithConversationManager() {
        if (!window.conversationManager) return;
        
        // 保存当前活动项ID，避免状态丢失
        const prevActiveId = this.currentConversationId;
        
        // 清空当前历史列表
        this.historyList.innerHTML = '';
        
        // 从对话管理器获取对话列表
        const conversations = window.conversationManager.conversations;
        const activeId = window.conversationManager.activeConversationId;
        
        console.log('🔄 同步对话列表，对话数量:', conversations.size);
        
        // 添加到历史列表
        conversations.forEach((conversation, conversationId) => {
            const historyItem = this.createHistoryItem({
                id: conversationId,
                title: conversation.title || '未命名对话',
                preview: conversation.last_message || conversation.messages?.[conversation.messages.length - 1]?.content || '暂无消息',
                timestamp: conversation.updated_at || conversation.created_at || new Date().toISOString()
            });
            
            this.historyList.appendChild(historyItem);
        });
        
        // 设置活动对话
        if (activeId) {
            this.updateActiveConversation(activeId);
            this.currentConversationId = activeId;
        } else if (prevActiveId && !conversations.has(prevActiveId)) {
            // 原活动项已被删，回到主界面
            console.log('📝 原活动对话已被删除，返回主界面');
            this.returnToMainView();
            this.currentConversationId = null;
        }
        
        // 如果没有对话，创建默认对话
        if (conversations.size === 0) {
            console.log('📝 没有对话，创建默认对话');
            await window.conversationManager.createNewConversation();
            this.syncWithConversationManager();
        }
    }

    

    /**
     * 显示知识库视图
     */
    showKnowledgeBaseView() {
        // 如果有知识库管理器，调用其方法切换到知识库视图
        if (window.knowledgeBaseManager && typeof window.knowledgeBaseManager.showKnowledgeBaseView === 'function') {
            window.knowledgeBaseManager.showKnowledgeBaseView();
        } else {
            console.error('❌ 知识库管理器未初始化或showKnowledgeBaseView方法不可用');
            // 降级处理：派发事件让其他模块处理
            this.dispatchEvent('open-knowledge-base');
        }
    }

    /**
     * 生成对话ID
     */
    generateConversationId() {
        return `conv_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }

    /**
     * 获取相对时间
     */
    getTimeAgo(timestamp) {
        const now = new Date();
        const past = new Date(timestamp);
        const diffMs = now - past;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);
        
        if (diffMins < 1) return '刚刚';
        if (diffMins < 60) return `${diffMins}分钟前`;
        if (diffHours < 24) return `${diffHours}小时前`;
        if (diffDays < 7) return `${diffDays}天前`;
        
        return past.toLocaleDateString();
    }

    /**
     * HTML转义
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    /**
     * 显示成功提示
     */
    showSuccessToast(message) {
        this.showToast(message, 'success');
    }

    /**
     * 显示错误提示
     */
    showErrorToast(message) {
        this.showToast(message, 'error');
    }

    /**
     * 显示提示消息
     */
    showToast(message, type = 'success') {
        // 移除现有提示
        const existingToast = document.querySelector('.success-toast, .error-toast');
        if (existingToast) {
            existingToast.remove();
        }

        // 创建新提示
        const toast = document.createElement('div');
        toast.className = `${type}-toast`;
        toast.textContent = message;
        
        document.body.appendChild(toast);
        
        // 显示动画
        setTimeout(() => toast.classList.add('show'), 10);
        
        // 自动隐藏
        setTimeout(() => {
            toast.classList.remove('show');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }

    /**
     * 设置键盘快捷键
     */
    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + B 切换侧边栏
            if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
                e.preventDefault();
                this.toggleSidebar();
            }
            
            // Ctrl/Cmd + N 新对话
            if ((e.ctrlKey || e.metaKey) && e.key === 'n') {
                e.preventDefault();
                this.handleNewChat();
            }
            
            // Ctrl/Cmd + K 聚焦搜索（如果有的话）
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                // 这里可以添加搜索框聚焦逻辑
            }
            
            // ESC 关闭移动端侧边栏
            if (e.key === 'Escape' && window.innerWidth <= 768) {
                this.closeSidebar();
            }
        });
    }

    /**
     * 添加拖拽排序功能
     */
    setupDragSort() {
        let draggedItem = null;
        
        this.historyList.addEventListener('dragstart', (e) => {
            if (e.target.classList.contains('history-item')) {
                draggedItem = e.target;
                e.target.style.opacity = '0.5';
            }
        });
        
        this.historyList.addEventListener('dragend', (e) => {
            if (e.target.classList.contains('history-item')) {
                e.target.style.opacity = '';
            }
        });
        
        this.historyList.addEventListener('dragover', (e) => {
            e.preventDefault();
            const afterElement = this.getDragAfterElement(this.historyList, e.clientY);
            if (afterElement == null) {
                this.historyList.appendChild(draggedItem);
            } else {
                this.historyList.insertBefore(draggedItem, afterElement);
            }
        });
    }

    /**
     * 获取拖拽后的位置
     */
    getDragAfterElement(container, y) {
        const draggableElements = [...container.querySelectorAll('.history-item:not(.dragging)')];
        
        return draggableElements.reduce((closest, child) => {
            const box = child.getBoundingClientRect();
            const offset = y - box.top - box.height / 2;
            
            if (offset < 0 && offset > closest.offset) {
                return { offset: offset, element: child };
            } else {
                return closest;
            }
        }, { offset: Number.NEGATIVE_INFINITY }).element;
    }

    /**
     * 添加长按删除功能
     */
    setupLongPress() {
        let pressTimer;
        let isLongPress = false;
        
        this.historyList.addEventListener('mousedown', (e) => {
            const historyItem = e.target.closest('.history-item');
            if (!historyItem) return;
            
            pressTimer = setTimeout(() => {
                isLongPress = true;
                this.showDeleteConfirm(historyItem);
            }, 800);
        });
        
        this.historyList.addEventListener('mouseup', () => {
            clearTimeout(pressTimer);
        });
        
        this.historyList.addEventListener('mouseleave', () => {
            clearTimeout(pressTimer);
        });
        
        this.historyList.addEventListener('click', (e) => {
            if (isLongPress) {
                e.preventDefault();
                isLongPress = false;
            }
        });
    }

    /**
     * 显示删除确认
     */
    showDeleteConfirm(historyItem) {
        const conversationId = historyItem.dataset.conversationId;
        const title = historyItem.querySelector('.history-title').textContent;
        
        if (confirm(`确定要删除对话"${title}"吗？`)) {
            this.deleteConversation(conversationId, historyItem);
        }
    }

    /**
     * 删除对话（长按删除）
     */
    async deleteConversation(conversationId, historyItem) {
        if (!conversationId) return;
        
        // 添加删除动画
        historyItem.classList.add('deleting');
        
        try {
            // 使用通用删除方法
            await this.deleteConversationById(conversationId);
        } catch (error) {
            console.error('删除对话失败:', error);
            historyItem.classList.remove('deleting');
        }
    }

    /**
     * 搜索历史对话
     */
    searchConversations(query) {
        const historyItems = this.historyList.querySelectorAll('.history-item');
        
        historyItems.forEach(item => {
            const title = item.querySelector('.history-title').textContent.toLowerCase();
            const preview = item.querySelector('.history-preview').textContent.toLowerCase();
            const searchTerm = query.toLowerCase();
            
            if (title.includes(searchTerm) || preview.includes(searchTerm)) {
                item.style.display = 'flex';
            } else {
                item.style.display = 'none';
            }
        });
    }

    /**
     * 添加搜索框
     */
    addSearchBox() {
        const searchContainer = document.createElement('div');
        searchContainer.className = 'search-container';
        searchContainer.innerHTML = `
            <input type="text" class="search-input" placeholder="搜索历史对话...">
            <button class="search-clear" style="display: none;">✕</button>
        `;
        
        const searchInput = searchContainer.querySelector('.search-input');
        const clearBtn = searchContainer.querySelector('.search-clear');
        
        searchInput.addEventListener('input', (e) => {
            const query = e.target.value;
            this.searchConversations(query);
            clearBtn.style.display = query ? 'block' : 'none';
        });
        
        clearBtn.addEventListener('click', () => {
            searchInput.value = '';
            this.searchConversations('');
            clearBtn.style.display = 'none';
        });
        
        // 插入到历史列表之前
        this.historyList.parentNode.insertBefore(searchContainer, this.historyList);
    }

    /**
     * 触发自定义事件
     */
    dispatchEvent(eventName, detail = {}) {
        const event = new CustomEvent(eventName, { detail });
        document.dispatchEvent(event);
    }

    /**
     * 获取当前对话ID
     */
    getCurrentConversationId() {
        return this.currentConversationId;
    }

    /**
     * 获取对话数据
     */
    getConversation(conversationId) {
        return this.conversations.get(conversationId);
    }

    /**
     * 添加移动端遮罩层
     */
    addMobileOverlay() {
        if (!this.mobileOverlay) {
            this.mobileOverlay = document.createElement('div');
            this.mobileOverlay.className = 'sidebar-overlay';
            this.mobileOverlay.style.cssText = `
                position: fixed;
                top: 0;
                left: 0;
                right: 0;
                bottom: 0;
                background: rgba(0, 0, 0, 0.5);
                z-index: 999;
                opacity: 0;
                visibility: hidden;
                transition: all 0.3s ease;
            `;
            
            // 点击遮罩层关闭侧边栏
            this.mobileOverlay.addEventListener('click', () => {
                this.closeSidebar();
            });
            
            document.body.appendChild(this.mobileOverlay);
        }
    }

    /**
     * 移除移动端遮罩层
     */
    removeMobileOverlay() {
        if (this.mobileOverlay) {
            this.mobileOverlay.remove();
            this.mobileOverlay = null;
        }
    }

    /**
     * 移动端打开侧边栏
     */
    openSidebar() {
        const isMobile = window.innerWidth <= 768;
        
        if (isMobile) {
            this.sidebar.classList.add('open');
            
            // 显示遮罩层
            if (this.mobileOverlay) {
                setTimeout(() => {
                    this.mobileOverlay.style.opacity = '1';
                    this.mobileOverlay.style.visibility = 'visible';
                }, 10);
            }
            
            // 防止背景滚动
            document.body.style.overflow = 'hidden';
        } else {
            // 桌面端直接切换折叠状态
            this.toggleSidebar();
        }
    }

    /**
     * 移动端关闭侧边栏
     */
    closeSidebar() {
        const isMobile = window.innerWidth <= 768;
        
        if (isMobile) {
            this.sidebar.classList.remove('open');
            
            // 隐藏遮罩层
            if (this.mobileOverlay) {
                this.mobileOverlay.style.opacity = '0';
                this.mobileOverlay.style.visibility = 'hidden';
            }
            
            // 恢复背景滚动
            document.body.style.overflow = '';
        }
    }

    /**
     * 回到主界面
     */
    returnToMainView() {
        console.log('🏠 回到主界面');
        
        // 隐藏所有视图
        const views = [
            'chatView',
            'pdfViewer', 
            'knowledgeBaseView',
            'knowledgeBaseDetailView'
        ];
        
        views.forEach(viewId => {
            const view = document.getElementById(viewId);
            if (view) {
                view.style.display = 'none';
                view.classList.remove('active');
            }
        });
        
        // 显示主界面
        const papersView = document.getElementById('papersView');
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
        
        // 聚焦主页输入框
        const heroInput = document.getElementById('chatInputMain');
        if (heroInput) {
            setTimeout(() => heroInput.focus(), 100);
        }
    }
}

// 创建全局实例
window.sidebarManager = new SidebarManager();

// 导出初始化函数
export function initSidebar() {
    window.sidebarManager.init();
}
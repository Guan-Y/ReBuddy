/**
 * 知识库管理模块
 * 处理知识库集合页面和详情页面的显示、交互和模拟路由
 */

import { api } from '../services/api.js';

class KnowledgeBaseManager {
    constructor() {
        // DOM 元素
        this.knowledgeBaseView = null;
        this.knowledgeBaseDetailView = null;
        this.knowledgeGrid = null;
        this.documentList = null;
        this.taskList = null;
        this.kbChatMessages = null;
        
        // 按钮元素
        this.knowledgeBackBtn = null;
        this.detailBackBtn = null;
        this.createKnowledgeBtn = null;
        this.knowledgeCards = [];
        
        // 模拟数据
        this.knowledgeBases = [];
        this.currentKnowledgeBase = null;
        this.documents = [];
        this.tasks = [];
        
        // 绑定方法
        this.showKnowledgeBaseView = this.showKnowledgeBaseView.bind(this);
        this.showKnowledgeBaseDetail = this.showKnowledgeBaseDetail.bind(this);
        this.hideAllViews = this.hideAllViews.bind(this);
        this.handleKnowledgeCardClick = this.handleKnowledgeCardClick.bind(this);
        this.handleBackButtonClick = this.handleBackButtonClick.bind(this);
        this.handleCreateKnowledgeBase = this.handleCreateKnowledgeBase.bind(this);
        this.handleDeleteKnowledgeBase = this.handleDeleteKnowledgeBase.bind(this);
        this.loadKnowledgeBases = this.loadKnowledgeBases.bind(this);
        this.loadDocuments = this.loadDocuments.bind(this);
        this.loadTasks = this.loadTasks.bind(this);
        this.setupEventListeners = this.setupEventListeners.bind(this);
        this.updateHash = this.updateHash.bind(this);
        this.handleHashChange = this.handleHashChange.bind(this);
    }

    /**
     * 初始化知识库模块
     */
    async init() {
        console.log('📚 初始化知识库模块...');
        
        // 获取DOM元素
        this.knowledgeBaseView = document.getElementById('knowledgeBaseView');
        this.knowledgeBaseDetailView = document.getElementById('knowledgeBaseDetailView');
        this.knowledgeGrid = document.getElementById('knowledgeGrid');
        this.documentList = document.getElementById('documentList');
        this.taskList = document.getElementById('taskList');
        this.kbChatMessages = document.getElementById('kbChatMessages');
        
        // PDF阅读器相关元素
        this.kbChatPanel = document.getElementById('kbChatPanel');
        this.kbPdfViewer = document.getElementById('kbPdfViewer');
        this.kbPdfFrame = document.getElementById('kbPdfFrame');
        this.kbPdfFileName = document.getElementById('kbPdfFileName');
        this.kbPdfBackBtn = document.getElementById('kbPdfBackBtn');
        this.kbPdfCloseBtn = document.getElementById('kbPdfCloseBtn');
        this.kbDocChatMessages = document.getElementById('kbDocChatMessages');
        this.kbDocChatInput = document.getElementById('kbDocChatInput');
        this.kbDocSendButton = document.getElementById('kbDocSendButton');
        this.kbDocClearButton = document.getElementById('kbDocClearButton');
        this.kbChatToggleBtn = document.getElementById('kbChatToggleBtn');
        this.kbPdfResizer = document.getElementById('kbPdfResizer');
        this.kbPdfDisplayArea = document.getElementById('kbPdfDisplayArea');
        this.kbDocChatArea = document.getElementById('kbDocChatArea');
        this.taskPanel = document.querySelector('.task-panel');
        
        // 当前打开的文档
        this.currentDocument = null;
        
        // 获取按钮元素
        this.knowledgeBackBtn = document.getElementById('knowledgeBackButton');
        this.detailBackBtn = document.getElementById('detailBackButton');
        this.createKnowledgeBtn = document.getElementById('createKnowledgeBtn');
        
        // 设置事件监听器
        this.setupEventListeners();
        
        // 设置哈希路由监听
        window.addEventListener('hashchange', this.handleHashChange);
        
        // 先加载数据，再处理路由
        await this.loadKnowledgeBases();
        
        // 初始根据哈希显示对应视图
        this.handleHashChange();
        
        console.log('✅ 知识库模块初始化完成');
    }

    /**
     * 等待API模块加载完成后再加载数据
     */
    waitForApiAndLoadData(retryCount = 0) {
        const MAX_RETRIES = 50; // 最大重试次数 (50 * 100ms = 5秒)
        
        // 检查API是否已经加载 - 检查多个关键API方法
        if (typeof api !== 'undefined' && 
            api && 
            api.listKnowledgeBases && 
            api.createKnowledgeBase && 
            api.deleteKnowledgeBase) {
            console.log('✅ API已就绪，开始加载知识库数据');
            this.loadKnowledgeBases();
        } else if (retryCount >= MAX_RETRIES) {
            console.warn('⚠️ API加载超时，显示空状态');
            this.knowledgeBases = [];
            this.renderEmptyKnowledgeBases();
        } else {
            if (retryCount === 0) {
                console.log('⏳ 等待API模块加载...');
            }
            // 如果API还没加载，等待100ms后重试
            setTimeout(() => {
                this.waitForApiAndLoadData(retryCount + 1);
            }, 100);
        }
    }

    /**
     * 设置事件监听器
     */
    setupEventListeners() {
        // 监听侧边栏的知识库按钮事件
        document.addEventListener('open-knowledge-base', this.showKnowledgeBaseView);
        
        // 返回按钮
        if (this.knowledgeBackBtn) {
            this.knowledgeBackBtn.addEventListener('click', () => {
                this.handleBackButtonClick('main');
            });
        }
        
        if (this.detailBackBtn) {
            this.detailBackBtn.addEventListener('click', () => {
                this.handleBackButtonClick('knowledge-list');
            });
        }
        
        // 新建知识库按钮
        if (this.createKnowledgeBtn) {
            this.createKnowledgeBtn.addEventListener('click', this.handleCreateKnowledgeBase);
        }
        
        
        
        // 知识库卡片点击事件（事件委托）
        if (this.knowledgeGrid) {
            this.knowledgeGrid.addEventListener('click', (e) => {
                const card = e.target.closest('.knowledge-card');
                if (card) {
                    this.handleKnowledgeCardClick(card);
                }
            });
        }
        
        // 文档列表复选框事件（事件委托）
        if (this.documentList) {
            this.documentList.addEventListener('change', (e) => {
                if (e.target.classList.contains('doc-checkbox')) {
                    this.handleDocumentCheckboxChange(e.target);
                }
            });
            
            // 文档项点击事件（排除复选框和操作按钮）
            this.documentList.addEventListener('click', (e) => {
                // 如果点击的是复选框或操作按钮，不处理
                if (e.target.classList.contains('doc-checkbox') || 
                    e.target.classList.contains('doc-action-btn') ||
                    e.target.closest('.doc-action-btn')) {
                    return;
                }
                
                // 找到文档项
                const docItem = e.target.closest('.document-item');
                if (docItem) {
                    const checkbox = docItem.querySelector('.doc-checkbox');
                    const docId = checkbox?.dataset.docId;
                    if (docId) {
                        this.handleDocumentClick(docId, docItem);
                    }
                }
            });
        }
        
        // 全选复选框事件
        const selectAllCheckbox = document.getElementById('selectAllCheckbox');
        if (selectAllCheckbox) {
            selectAllCheckbox.addEventListener('change', (e) => {
                this.handleSelectAllChange(e.target);
            });
        }
        
        // 知识库对话发送按钮
        const kbSendButton = document.getElementById('kbSendButton');
        const kbChatInput = document.getElementById('kbChatInput');
        const kbClearButton = document.getElementById('kbClearButton');
        if (kbSendButton && kbChatInput) {
            kbSendButton.addEventListener('click', () => this.handleKbChatSend());
            kbChatInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.handleKbChatSend();
            });
        }
        if (kbClearButton) {
            kbClearButton.addEventListener('click', () => this.clearKbConversation());
        }
        
        // PDF阅读器相关按钮
        if (this.kbPdfBackBtn) {
            this.kbPdfBackBtn.addEventListener('click', () => this.closeKbPdfViewer());
        }
        if (this.kbPdfCloseBtn) {
            this.kbPdfCloseBtn.addEventListener('click', () => this.closeKbPdfViewer());
        }
        if (this.kbDocSendButton && this.kbDocChatInput) {
            this.kbDocSendButton.addEventListener('click', () => this.handleDocChatSend());
            this.kbDocChatInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.handleDocChatSend();
            });
        }
        if (this.kbDocClearButton) {
            this.kbDocClearButton.addEventListener('click', () => this.clearFileConversation());
        }
        if (this.kbChatToggleBtn) {
            this.kbChatToggleBtn.addEventListener('click', () => this.toggleKbDocChat());
        }
        
        // 初始化PDF阅读器拖拽调整功能
        if (this.kbPdfResizer) {
            this.initKbPdfResizer();
        }
        
        // 任务相关按钮
        const refreshTasksBtn = document.getElementById('refreshTasksBtn');
        if (refreshTasksBtn) refreshTasksBtn.addEventListener('click', () => this.loadTasks());
        
        // 大任务按钮 - 使用事件委托，确保按钮存在时能正常工作
        // 由于按钮在详情页面中，使用事件委托更可靠
        const detailView = document.getElementById('knowledgeBaseDetailView');
        if (detailView) {
            detailView.addEventListener('click', (e) => {
                if (e.target.closest('#aiPptBtn')) {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log('📊 AI-PPT按钮被点击');
                    this.handleAiPptTask();
                } else if (e.target.closest('#reportBtn')) {
                    e.preventDefault();
                    e.stopPropagation();
                    this.handleReportTask();
                }
            });
        }
        
        // 也保留直接绑定作为备用
        const aiPptBtn = document.getElementById('aiPptBtn');
        const reportBtn = document.getElementById('reportBtn');
        if (aiPptBtn) {
            // 移除可能存在的旧监听器
            const newAiPptBtn = aiPptBtn.cloneNode(true);
            aiPptBtn.parentNode.replaceChild(newAiPptBtn, aiPptBtn);
            newAiPptBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('📊 AI-PPT按钮被点击（直接绑定）');
                this.handleAiPptTask();
            });
        }
        if (reportBtn) {
            reportBtn.addEventListener('click', () => this.handleReportTask());
        }
        
        // 文档操作按钮
        const deleteSelectedBtn = document.getElementById('deleteSelectedBtn');
        const uploadFileBtn = document.getElementById('uploadFileBtn');
        if (deleteSelectedBtn) deleteSelectedBtn.addEventListener('click', () => this.deleteSelectedDocuments());
        if (uploadFileBtn) uploadFileBtn.addEventListener('click', () => this.handleFileUpload());
        
        // 知识库开关按钮
        const kbSwitchNet = document.getElementById('kbSwitchNet');
        const kbSwitchDeep = document.getElementById('kbSwitchDeep');
        if (kbSwitchNet) {
            kbSwitchNet.addEventListener('click', () => {
                kbSwitchNet.classList.toggle('active');
            });
        }
        if (kbSwitchDeep) {
            kbSwitchDeep.addEventListener('click', () => {
                kbSwitchDeep.classList.toggle('active');
            });
        }

        // 文档对话开关按钮
        const kbDocSwitchNet = document.getElementById('kbDocSwitchNet');
        const kbDocSwitchKb = document.getElementById('kbDocSwitchKb');
        if (kbDocSwitchNet) {
            kbDocSwitchNet.addEventListener('click', () => {
                kbDocSwitchNet.classList.toggle('active');
            });
        }
        if (kbDocSwitchKb) {
            kbDocSwitchKb.addEventListener('click', () => {
                kbDocSwitchKb.classList.toggle('active');
            });
        }
    }

    /**
     * 隐藏所有视图（除了侧边栏）
     */
    hideAllViews() {
        // 获取所有可能的视图
        const views = [
            'papersView',
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
     * 显示知识库集合页面
     */
    showKnowledgeBaseView() {
        this.hideAllViews();
        this.knowledgeBaseView.style.display = 'flex';
        this.knowledgeBaseView.classList.add('active');
        this.updateHash('#/knowledge-bases');
        
        // 隐藏侧边栏
        this.hideSidebar();
        
        // 确保数据是最新的
        this.loadKnowledgeBases();
        
        console.log('📚 显示知识库集合页面');
    }

    /**
     * 显示知识库详情页面
     * @param {string} kbId - 知识库ID
     */
    async showKnowledgeBaseDetail(kbId) {
        this.hideAllViews();
        this.knowledgeBaseDetailView.style.display = 'flex';
        this.knowledgeBaseDetailView.classList.add('active');
        this.updateHash(`#/knowledge-bases/${kbId}`);
        
        // 隐藏侧边栏
        this.hideSidebar();
        
        // 加载选中的知识库数据
        let kb = this.knowledgeBases.find(k => k.id === kbId);
        
        if (!kb) {
            // 如果列表中没有，尝试从 API 获取详情
            console.log(`📚 知识库列表中未找到 ${kbId}，尝试从 API 获取详情`);
            try {
                const response = await api.getKnowledgeBaseDetail(kbId);
                if (response && response.status === 'success' && response.data) {
                    kb = {
                        id: response.data.id,
                        name: response.data.name,
                        description: response.data.description || '暂无描述',
                        documentCount: response.data.file_count || 0,
                        updatedAt: response.data.updated_at || response.data.created_at,
                        createdAt: response.data.created_at
                    };
                    // 添加到列表中
                    this.knowledgeBases.push(kb);
                }
            } catch (error) {
                console.error('获取知识库详情失败:', error);
            }
        }
        
        if (kb) {
            this.currentKnowledgeBase = kb;
            this.updateDetailView(kb);
            this.loadDocuments(kbId);
            this.loadTasks(kbId);
            // TODO: 暂时注释掉轮询启动
            // // 启动任务轮询
            // this.startTaskPolling(kbId);
            // 加载知识库对话历史
            this.loadKbConversationHistory(kbId, kb.name);

            // 重新绑定详情页面的按钮事件（确保按钮可用）
            this.bindDetailPageEvents();
        } else {
            console.error(`❌ 无法找到知识库: ${kbId}`);
            this.showErrorToast('知识库不存在或已被删除');
            // 返回知识库列表
            this.showKnowledgeBaseView();
        }

        console.log(`📚 显示知识库详情: ${kbId}`);
    }

    /**
     * 更新详情页面内容
     */
    updateDetailView(knowledgeBase) {
        const titleElement = document.getElementById('detailTitle');
        if (titleElement) {
            titleElement.textContent = knowledgeBase.name;
        }
    }
    
    /**
     * 绑定详情页面的按钮事件
     */
    bindDetailPageEvents() {
        // 重新绑定AI-PPT按钮
        const aiPptBtn = document.getElementById('aiPptBtn');
        if (aiPptBtn) {
            // 移除旧的事件监听器（通过克隆节点）
            const newBtn = aiPptBtn.cloneNode(true);
            aiPptBtn.parentNode.replaceChild(newBtn, aiPptBtn);
            
            // 绑定新的事件
            newBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                console.log('📊 AI-PPT按钮被点击（详情页面绑定）');
                this.handleAiPptTask();
            });
            console.log('✅ AI-PPT按钮事件已重新绑定');
        } else {
            console.warn('⚠️ 未找到AI-PPT按钮');
        }
        
        // 重新绑定研究报告按钮
        const reportBtn = document.getElementById('reportBtn');
        if (reportBtn) {
            const newReportBtn = reportBtn.cloneNode(true);
            reportBtn.parentNode.replaceChild(newReportBtn, reportBtn);
            newReportBtn.addEventListener('click', () => this.handleReportTask());
        }
    }

    /**
     * 处理知识库卡片点击
     */
    handleKnowledgeCardClick(card) {
        const kbId = card.dataset.kbId;
        if (kbId) {
            this.showKnowledgeBaseDetail(kbId);
        }
    }

    /**
     * 处理返回按钮点击
     * @param {string} target - 返回目标：'main' 或 'knowledge-list'
     */
    handleBackButtonClick(target) {
        // TODO: 暂时注释掉轮询停止
        // // 停止任务轮询
        // this.stopTaskPolling();

        if (target === 'main') {
            // 返回主界面（论文列表）
            this.hideAllViews();
            const papersView = document.getElementById('papersView');
            if (papersView) {
                papersView.style.display = 'block';
                papersView.classList.add('active');
            }
            this.updateHash('#/');

            // 显示侧边栏
            this.showSidebar();
        } else if (target === 'knowledge-list') {
            // 返回知识库列表
            this.showKnowledgeBaseView();
        }
    }

    /**
     * 隐藏侧边栏
     */
    hideSidebar() {
        const sidebar = document.getElementById('sidebar');
        if (sidebar) {
            sidebar.style.display = 'none';
        }
        
        // 调整主内容区域的边距
        const chatArea = document.querySelector('.chat-area');
        if (chatArea) {
            chatArea.style.marginLeft = '0';
        }
    }

    /**
     * 显示侧边栏
     */
    showSidebar() {
        const sidebar = document.getElementById('sidebar');
        if (sidebar) {
            sidebar.style.display = 'flex';
        }
        
        // 恢复主内容区域的边距
        const chatArea = document.querySelector('.chat-area');
        if (chatArea) {
            chatArea.style.marginLeft = '';
        }
    }

/**
     * 处理创建知识库
     */
    async handleCreateKnowledgeBase() {
        const name = prompt('请输入新知识库的名称:');
        if (!name || !name.trim()) return;
        
        const description = prompt('请输入知识库描述（可选）:') || '';
        
        try {
            console.log('📝 创建知识库:', name);
            
            // 检查API是否可用
            if (typeof api === 'undefined' || !api || !api.createKnowledgeBase) {
                throw new Error('API服务不可用，请刷新页面重试');
            }
            
            const result = await api.createKnowledgeBase(name.trim(), description.trim());
            
            if (result && result.status === 'success') {
                this.showSuccessToast(`知识库 "${name}" 创建成功`);
                // 重新加载知识库列表
                this.loadKnowledgeBases();
            } else {
                throw new Error(result?.message || '创建失败');
            }
        } catch (error) {
            console.error('知识库创建失败:', error);
            this.showErrorToast(`知识库创建失败: ${error.message}`);
        }
    }

    /**
     * 处理删除知识库
     */
    async handleDeleteKnowledgeBase() {
        if (!this.currentKnowledgeBase) {
            this.showErrorToast('没有选择的知识库');
            return;
        }
        
        const kbName = this.currentKnowledgeBase.name;
        if (!confirm(`确定要删除知识库 "${kbName}" 吗？此操作将删除知识库及其所有文档，且不可撤销！`)) {
            return;
        }
        
        try {
            console.log('🗑️ 删除知识库:', this.currentKnowledgeBase.id);
            
            // 检查API是否可用
            if (typeof api === 'undefined' || !api || !api.deleteKnowledgeBase) {
                throw new Error('API服务不可用，请刷新页面重试');
            }
            
            const result = await api.deleteKnowledgeBase(this.currentKnowledgeBase.id);
            
            if (result && result.status === 'success') {
                this.showSuccessToast(`知识库 "${kbName}" 删除成功`);
                // 返回知识库列表
                this.showKnowledgeBaseView();
                // 重新加载知识库列表
                this.loadKnowledgeBases();
            } else {
                throw new Error(result?.message || '删除失败');
            }
        } catch (error) {
            console.error('知识库删除失败:', error);
            this.showErrorToast(`知识库删除失败: ${error.message}`);
        }
    }

    /**
     * 从卡片删除知识库
     */
    async handleDeleteKnowledgeBaseFromCard(kbId, kbName) {
        if (!confirm(`确定要删除知识库 "${kbName}" 吗？此操作将删除知识库及其所有文档，且不可撤销！`)) {
            return;
        }
        
        try {
            console.log('🗑️ 删除知识库:', kbId);
            
            // 检查API是否可用
            if (typeof api === 'undefined' || !api || !api.deleteKnowledgeBase) {
                throw new Error('API服务不可用，请刷新页面重试');
            }
            
            const result = await api.deleteKnowledgeBase(kbId);
            
            if (result && result.status === 'success') {
                this.showSuccessToast(`知识库 "${kbName}" 删除成功`);
                // 重新加载知识库列表
                this.loadKnowledgeBases();
            } else {
                throw new Error(result?.message || '删除失败');
            }
        } catch (error) {
            console.error('知识库删除失败:', error);
            this.showErrorToast(`知识库删除失败: ${error.message}`);
        }
    }

    /**
     * 加载知识库数据
     */
    async loadKnowledgeBases() {
        try {
            console.log('📚 加载知识库列表...');
            
            // 检查API是否可用
            if (typeof api === 'undefined' || !api || typeof api.listKnowledgeBases !== 'function') {
                console.log('📝 API不可用，显示空状态');
                this.knowledgeBases = [];
                this.renderEmptyKnowledgeBases();
                return;
            }
            
            const response = await api.listKnowledgeBases();
            
            if (response && response.status === 'success') {
                // 检查是否有知识库数据
                if (response.data && Array.isArray(response.data) && response.data.length > 0) {
                    this.knowledgeBases = response.data.map(kb => ({
                        id: kb.id,
                        name: kb.name,
                        description: kb.description || '暂无描述',
                        documentCount: kb.file_count || 0,
                        updatedAt: kb.updated_at || kb.created_at,
                        createdAt: kb.created_at,
                        folderId: kb.folder_id
                    }));
                    
                    console.log('✅ 知识库列表加载成功:', this.knowledgeBases);
                    this.renderKnowledgeBases();
                } else {
                    // 后端没有知识库数据，显示空状态
                    console.log('📝 后端没有知识库数据，显示空状态');
                    this.knowledgeBases = [];
                    this.renderEmptyKnowledgeBases();
                }
            } else {
                console.error('❌ 知识库列表加载失败:', response?.message || '未知错误');
                // 不显示错误提示，直接显示空状态
                console.log('📝 API调用失败，显示空状态');
                this.knowledgeBases = [];
                this.renderEmptyKnowledgeBases();
            }
        } catch (error) {
            console.error('❌ 知识库列表加载异常:', error);
            // 不显示错误提示，直接显示空状态
            console.log('📝 API调用异常，显示空状态');
            this.knowledgeBases = [];
            this.renderEmptyKnowledgeBases();
        }
    }

    /**
     * 渲染空知识库状态
     */
    renderEmptyKnowledgeBases() {
        if (!this.knowledgeGrid) return;
        
        this.knowledgeGrid.innerHTML = `
            <div class="empty-knowledge-bases">
                <div class="empty-icon">📚</div>
                <h3>请创建你的第一个知识库吧</h3>
                <p>点击"新建知识库"按钮开始创建</p>
            </div>
        `;
    }

    

    /**
     * 渲染知识库列表
     */
    renderKnowledgeBases() {
        if (!this.knowledgeGrid) return;
        
        this.knowledgeGrid.innerHTML = '';
        
        this.knowledgeBases.forEach(kb => {
            const card = this.createKnowledgeCard(kb);
            this.knowledgeGrid.appendChild(card);
        });
    }

    /**
     * 创建知识库卡片DOM
     */
    createKnowledgeCard(knowledgeBase) {
        const card = document.createElement('div');
        card.className = 'knowledge-card';
        card.dataset.kbId = knowledgeBase.id;
        
        const timeAgo = this.getTimeAgo(knowledgeBase.updatedAt);
        
        card.innerHTML = `
            <div class="card-icon">📁</div>
            <div class="card-content">
                <h3 class="card-title">${this.escapeHtml(knowledgeBase.name)}</h3>
                <p class="card-description">${this.escapeHtml(knowledgeBase.description)}</p>
                <div class="card-stats">
                    <span class="stat">📄 ${knowledgeBase.documentCount} 个文档</span>
                    <span class="stat">🕐 更新于 ${timeAgo}</span>
                </div>
            </div>
            <div class="card-actions">
                <button class="card-action-btn delete-btn" data-kb-id="${knowledgeBase.id}" title="删除知识库">🗑️</button>
            </div>
        `;
        
        // 绑定删除按钮事件
        const deleteBtn = card.querySelector('.delete-btn');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', (e) => {
                e.stopPropagation(); // 阻止事件冒泡到卡片点击
                this.handleDeleteKnowledgeBaseFromCard(knowledgeBase.id, knowledgeBase.name);
            });
        }
        
        return card;
    }

    /**
     * 加载文档数据
     */
    async loadDocuments(kbId = 'default') {
        try {
            console.log(`📄 加载知识库 ${kbId} 的文档列表...`);
            
            // 检查API是否可用
            if (typeof api === 'undefined' || !api || !api.getKnowledgeBaseFiles) {
                console.log('📝 API不可用，显示空文档状态');
                this.documents = [];
                this.renderEmptyDocuments();
                return;
            }
            
            const response = await api.getKnowledgeBaseFiles(kbId);
            
            if (response && response.status === 'success') {
                // 检查是否有文档数据
                if (response.data && Array.isArray(response.data) && response.data.length > 0) {
                    this.documents = response.data.map(doc => ({
                        id: doc.id,
                        name: doc.name,
                        size: this.formatFileSize(doc.size || 0),
                        uploadedAt: new Date(doc.uploaded_at || doc.created_at).toLocaleDateString(),
                        type: this.getFileType(doc.name)
                    }));
                    
                    console.log('✅ 文档列表加载成功:', this.documents);
                    
                    // 单独处理渲染错误
                    try {
                        this.renderDocuments();
                    } catch (renderError) {
                        console.error('❌ 文档列表渲染异常:', renderError);
                    }
                } else {
                    // 知识库没有文档
                    console.log('📝 知识库没有文档');
                    this.documents = [];
                    this.renderEmptyDocuments();
                }
            } else {
                console.error('❌ 文档列表加载失败:', response?.message || '未知错误');
                // 不显示错误提示，直接显示空状态
                console.log('📝 文档列表加载失败，显示空状态');
                this.documents = [];
                this.renderEmptyDocuments();
            }
        } catch (error) {
            console.error('❌ 文档列表加载异常:', error);
            // 不显示错误提示，直接显示空状态
            console.log('📝 文档列表加载异常，显示空状态');
            this.documents = [];
            this.renderEmptyDocuments();
        }
    }

    /**
     * 格式化文件大小
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    /**
     * 获取文件类型
     */
    getFileType(fileName) {
        const ext = fileName.split('.').pop().toLowerCase();
        const typeMap = {
            'pdf': 'pdf',
            'doc': 'word',
            'docx': 'word',
            'xls': 'excel',
            'xlsx': 'excel',
            'txt': 'text',
            'md': 'markdown'
        };
        return typeMap[ext] || 'unknown';
    }

    /**
     * 渲染文档列表
     */
    renderDocuments() {
        if (!this.documentList) return;
        
        this.documentList.innerHTML = '';
        
        this.documents.forEach(doc => {
            const docItem = this.createDocumentItem(doc);
            this.documentList.appendChild(docItem);
        });
        
        // 重置全选复选框的状态
        this.updateSelectAllCheckbox();
    }

    /**
     * 渲染空文档状态
     */
    renderEmptyDocuments() {
        if (!this.documentList) return;
        
        this.documentList.innerHTML = `
            <div class="empty-documents">
                <div class="empty-documents-icon">📄</div>
                <h4>还没有文档</h4>
                <p>点击"上传文件"按钮添加文档到知识库</p>
            </div>
        `;
        
        // 重置全选复选框的状态
        this.updateSelectAllCheckbox();
    }

    /**
     * 创建文档项DOM
     */
    createDocumentItem(doc) {
        const item = document.createElement('div');
        item.className = 'document-item';
        
        item.innerHTML = `
            <input type="checkbox" class="doc-checkbox" data-doc-id="${doc.id}">
            <div class="doc-icon">${this.getDocumentIcon(doc.type)}</div>
            <div class="doc-info">
                <div class="doc-title">${this.escapeHtml(doc.name)}</div>
                <div class="doc-meta">上传于 ${doc.uploadedAt} · 大小 ${doc.size}</div>
            </div>
            <button class="doc-action-btn" data-doc-id="${doc.id}">⋮</button>
        `;
        
        return item;
    }

    /**
     * 根据文档类型获取图标
     */
    getDocumentIcon(type) {
        const icons = {
            'pdf': '📄',
            'word': '📝',
            'excel': '📊',
            'markdown': '📘',
            'default': '📎'
        };
        return icons[type] || icons.default;
    }

    /**
     * 加载任务数据
     */
    async loadTasks(kbId = null) {
        if (!kbId || !this.currentKnowledgeBase) {
            return;
        }

        try {
            // TODO: 暂时注释掉真实 API 调用，使用 mock 数据
            // if (typeof api === 'undefined' || !api || !api.getTaskList) {
            //     console.error('API服务不可用');
            //     return;
            // }

            // const response = await api.getTaskList(kbId);

            // if (response && response.status === 'success') {
            //     // 只显示进行中和已完成的任务
            //     const tasks = response.data?.tasks || [];
            //     this.tasks = tasks.filter(task =>
            //         task.status === 'processing' || task.status === 'completed'
            //     );
            //     this.renderTasks();
            // }

            // Mock 数据用于展示
            this.tasks = [
                {
                    task_id: 'mock_task_1',
                    user_id: 'mock_user',
                    kb_id: kbId,
                    generation_type: 'ppt',
                    file_ids: ['file1', 'file2'],
                    query: '生成学术报告PPT',
                    status: 'processing',
                    progress: 60,
                    message: '正在生成PPT内容...',
                    created_at: new Date().toISOString(),
                    updated_at: new Date().toISOString()
                },
                {
                    task_id: 'mock_task_2',
                    user_id: 'mock_user',
                    kb_id: kbId,
                    generation_type: 'ppt',
                    file_ids: ['file3'],
                    query: '生成技术方案PPT',
                    status: 'completed',
                    progress: 100,
                    message: 'PPT生成成功',
                    result_path: '/mock/path/result.md',
                    created_at: new Date(Date.now() - 3600000).toISOString(),
                    updated_at: new Date(Date.now() - 1800000).toISOString()
                },
                {
                    task_id: 'mock_task_3',
                    user_id: 'mock_user',
                    kb_id: kbId,
                    generation_type: 'report',
                    file_ids: ['file1', 'file2', 'file3'],
                    query: '生成研究报告',
                    status: 'completed',
                    progress: 100,
                    message: '研究报告生成成功',
                    result_path: '/mock/path/report.md',
                    created_at: new Date(Date.now() - 7200000).toISOString(),
                    updated_at: new Date(Date.now() - 5400000).toISOString()
                }
            ];

            this.renderTasks();
        } catch (error) {
            console.error('加载任务列表失败:', error);
        }
    }

    /**
     * 启动任务轮询
     */
    startTaskPolling(kbId) {
        // TODO: 暂时注释掉轮询功能
        // // 清除之前的轮询
        // this.stopTaskPolling();

        // // 每5秒轮询一次任务状态
        // this.taskPollingInterval = setInterval(() => {
        //     this.loadTasks(kbId);
        // }, 5000);

        // console.log('🔄 任务轮询已启动');
        console.log('⏸️ 任务轮询已禁用（使用 mock 数据）');
    }

    /**
     * 停止任务轮询
     */
    stopTaskPolling() {
        // TODO: 暂时注释掉轮询功能
        // if (this.taskPollingInterval) {
        //     clearInterval(this.taskPollingInterval);
        //     this.taskPollingInterval = null;
        //     console.log('⏹️ 任务轮询已停止');
        // }
        console.log('⏸️ 任务轮询已禁用（使用 mock 数据）');
    }

    /**
     * 渲染任务列表
     */
    renderTasks() {
        if (!this.taskList) return;
        
        this.taskList.innerHTML = '';
        
        this.tasks.forEach(task => {
            const taskItem = this.createTaskItem(task);
            this.taskList.appendChild(taskItem);
        });
    }

    /**
     * 创建任务项DOM
     */
    createTaskItem(task) {
        const item = document.createElement('div');
        item.className = `task-item task-${task.status}`;
        item.dataset.taskId = task.task_id;

        // 根据任务类型和状态确定图标
        const generationType = task.generation_type || 'unknown';
        const taskTypeIcon = generationType === 'ppt' ? '📊' : '📝';

        // 根据状态确定图标
        let statusIcon = '⏳';
        if (task.status === 'processing') {
            statusIcon = '⏳';
        } else if (task.status === 'completed') {
            statusIcon = '✅';
        } else if (task.status === 'failed') {
            statusIcon = '❌';
        }

        // 任务标题
        const taskTitle = `${taskTypeIcon} ${generationType.toUpperCase()}生成`;

        // 操作按钮
        let actionButtons = '';
        if (task.status === 'completed') {
            actionButtons = `
                <button class="task-action-btn download-btn" title="下载结果" data-task-id="${task.task_id}">⬇️</button>
            `;
        }
        actionButtons += `
            <button class="task-action-btn delete-btn" title="删除任务" data-task-id="${task.task_id}">🗑️</button>
        `;

        item.innerHTML = `
            <div class="task-icon">${statusIcon}</div>
            <div class="task-info">
                <div class="task-title">${this.escapeHtml(taskTitle)}</div>
                <div class="task-meta">${task.message || ''}</div>
            </div>
            <div class="task-actions">
                ${actionButtons}
            </div>
        `;

        // 绑定操作按钮事件
        const downloadBtn = item.querySelector('.download-btn');
        if (downloadBtn) {
            downloadBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.handleTaskDownload(task.task_id);
            });
        }

        const deleteBtn = item.querySelector('.delete-btn');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.handleTaskDelete(task.task_id);
            });
        }

        return item;
    }

    /**
     * 处理任务下载
     */
    async handleTaskDownload(taskId) {
        try {
            // TODO: 暂时注释掉真实 API 调用，使用 mock 行为
            // if (typeof api === 'undefined' || !api || !api.downloadTaskResult) {
            //     this.showErrorToast('API服务不可用');
            //     return;
            // }

            // this.showInfoToast('正在下载任务结果...');

            // const blob = await api.downloadTaskResult(taskId);

            // // 创建下载链接
            // const url = window.URL.createObjectURL(blob);
            // const a = document.createElement('a');
            // a.href = url;
            // a.download = `task_${taskId}.md`;
            // document.body.appendChild(a);
            // a.click();
            // document.body.removeChild(a);
            // window.URL.revokeObjectURL(url);

            // this.showSuccessToast('任务结果下载成功！');

            // Mock 行为
            this.showInfoToast('正在下载任务结果...');
            setTimeout(() => {
                // 创建 mock 内容
                const mockContent = `# Mock 任务结果\n\n任务ID: ${taskId}\n\n这是模拟的生成内容。`;
                const blob = new Blob([mockContent], { type: 'text/markdown' });
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `task_${taskId}.md`;
                document.body.appendChild(a);
                a.click();
                document.body.removeChild(a);
                window.URL.revokeObjectURL(url);

                this.showSuccessToast('任务结果下载成功！(Mock 数据)');
            }, 500);
        } catch (error) {
            console.error('下载任务结果失败:', error);
            this.showErrorToast(`下载失败: ${error.message}`);
        }
    }

    /**
     * 处理任务删除
     */
    async handleTaskDelete(taskId) {
        if (!confirm('确定要删除这个任务吗？')) {
            return;
        }

        try {
            // TODO: 暂时注释掉真实 API 调用，使用 mock 行为
            // if (typeof api === 'undefined' || !api || !api.deleteTask) {
            //     this.showErrorToast('API服务不可用');
            //     return;
            // }

            // const response = await api.deleteTask(taskId);

            // if (response && response.status === 'success') {
            //     this.showSuccessToast('任务已删除');
            //     // 刷新任务列表
            //     if (this.currentKnowledgeBase) {
            //         await this.loadTasks(this.currentKnowledgeBase.id);
            //     }
            // } else {
            //     throw new Error(response?.message || '删除任务失败');
            // }

            // Mock 行为
            this.showInfoToast('正在删除任务...');
            setTimeout(() => {
                // 从 mock 数据中删除任务
                this.tasks = this.tasks.filter(task => task.task_id !== taskId);
                this.renderTasks();
                this.showSuccessToast('任务已删除！(Mock 数据)');
            }, 500);
        } catch (error) {
            console.error('删除任务失败:', error);
            this.showErrorToast(`删除失败: ${error.message}`);
        }
    }

    /**
     * 处理知识库聊天发送
     */
    async handleKbChatSend() {
        const input = document.getElementById('kbChatInput');
        if (!input) return;

        const message = input.value.trim();
        if (!message) return;

        // 添加用户消息
        this.addKbChatMessage('user', message);

        // 清空输入框
        input.value = '';

        // 获取选中的文件ID
        const selectedFiles = this.documentList.querySelectorAll('.doc-checkbox:checked');
        const fileIds = Array.from(selectedFiles).map(cb => cb.dataset.docId);

        // 获取联网搜索开关状态
        const kbSwitchNet = document.getElementById('kbSwitchNet');
        const useNet = kbSwitchNet?.classList.contains('active') || false;

        // 添加加载指示器
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'message ai';
        loadingDiv.innerHTML = `
            <div class="message-bubble typing-indicator">
                AI 正在思考<span class="dot"></span><span class="dot"></span><span class="dot"></span>
            </div>
        `;
        this.kbChatMessages.appendChild(loadingDiv);
        this.kbChatMessages.scrollTop = this.kbChatMessages.scrollHeight;

        try {
            // 检查API是否可用
            if (typeof api === 'undefined' || !api) {
                throw new Error('API服务不可用');
            }

            // 调用知识库对话API
            const response = await fetch('chat/knowledge-base/stream', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
                },
                body: JSON.stringify({
                    query: message,
                    kb_id: this.currentKnowledgeBase ? this.currentKnowledgeBase.id : null,
                    kb_name: this.currentKnowledgeBase ? this.currentKnowledgeBase.name : '',
                    file_ids: fileIds,
                    net: useNet
                })
            });
            
            // 移除加载指示器
            loadingDiv.remove();
            
            if (!response.ok) {
                throw new Error(`API调用失败: ${response.status}`);
            }
            
            // 处理流式响应
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let fullResponse = '';
            
            // 添加AI消息容器
            const aiMessageDiv = document.createElement('div');
            aiMessageDiv.className = 'message ai';
            aiMessageDiv.innerHTML = `
                <div class="message-bubble">
                    <div class="markdown-content"></div>
                </div>
            `;
            this.kbChatMessages.appendChild(aiMessageDiv);
            const contentDiv = aiMessageDiv.querySelector('.markdown-content');
            
            console.log('📡 开始读取流式响应...');
            
            while (true) {
                const { done, value } = await reader.read();
                if (done) {
                    console.log('✅ 流式响应读取完成');
                    break;
                }
                
                // 使用 { stream: true } 解码流式数据
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || ''; // 保留未完整的行
                
                for (const line of lines) {
                    const trimmed = line.trim();
                    if (trimmed.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(trimmed.slice(6));
                            if (data.chunk) {
                                fullResponse += data.chunk;
                                // 使用 marked 渲染 Markdown
                                contentDiv.innerHTML = typeof marked !== 'undefined' ? marked.parse(fullResponse) : fullResponse;
                                this.kbChatMessages.scrollTop = this.kbChatMessages.scrollHeight;
                                console.log('📝 收到 chunk:', data.chunk.length, '字符');
                            }
                        } catch (e) {
                            console.error('解析流式数据失败:', e, 'line:', trimmed);
                        }
                    }
                }
            }
            
            // 流式结束后，应用 Prism 代码高亮
            if (typeof Prism !== 'undefined') {
                contentDiv.querySelectorAll('pre code').forEach(block => Prism.highlightElement(block));
            }
            
            console.log('🎉 知识库对话完成，总长度:', fullResponse.length);
            
        } catch (error) {
            console.error('知识库对话失败:', error);
            
            // 移除加载指示器
            loadingDiv.remove();
            
            // 显示错误消息
            this.addKbChatMessage('ai', `抱歉，对话过程中出现错误：${error.message}`);
        }
    }

    /**
     * 添加知识库聊天消息
     */
    addKbChatMessage(role, content) {
        if (!this.kbChatMessages) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        
        // 使用 marked 渲染 Markdown
        const renderedContent = (role === 'ai' && typeof marked !== 'undefined') 
            ? marked.parse(content) 
            : this.escapeHtml(content);
        
        messageDiv.innerHTML = `
            <div class="message-bubble">
                <div class="markdown-content">${renderedContent}</div>
            </div>
        `;
        
        this.kbChatMessages.appendChild(messageDiv);
        
        // 应用 Prism 代码高亮
        if (role === 'ai' && typeof Prism !== 'undefined') {
            messageDiv.querySelectorAll('pre code').forEach(block => Prism.highlightElement(block));
        }
        
        this.kbChatMessages.scrollTop = this.kbChatMessages.scrollHeight;
    }

    /**
     * 加载知识库对话历史
     */
    async loadKbConversationHistory(kbId, kbName) {
        try {
            if (!api || !api.getKbConversationHistory) {
                console.error('API服务不可用');
                return;
            }

            const response = await api.getKbConversationHistory(kbId);
            
            if (response && response.status === 'success') {
                const messages = response.data?.messages || [];
                
                // 清空当前消息
                if (this.kbChatMessages) {
                    this.kbChatMessages.innerHTML = '';
                }
                
                // 渲染历史消息
                if (messages.length > 0) {
                    messages.forEach(msg => {
                        this.addKbChatMessage(msg.type === 'user' ? 'user' : 'ai', msg.content);
                    });
                } else {
                    // 如果没有历史消息，显示欢迎消息
                    this.addKbChatMessage('ai', `你好！我是${kbName}的AI助手，有什么可以帮助你的吗？`);
                }
                
                console.log(`✅ 成功加载知识库对话历史: ${messages.length} 条消息`);
            } else {
                console.error('加载对话历史失败:', response?.message);
            }
        } catch (error) {
            console.error('加载知识库对话历史失败:', error);
        }
    }

    /**
     * 清除知识库对话
     */
    async clearKbConversation() {
        if (!this.currentKnowledgeBase) {
            this.showErrorToast('当前知识库信息不存在');
            return;
        }

        if (!confirm('确定要清除当前对话吗？')) {
            return;
        }

        try {
            if (!api || !api.clearKbConversation) {
                throw new Error('API服务不可用，请刷新页面重试');
            }

            const result = await api.clearKbConversation(this.currentKnowledgeBase.id);

            if (result && result.status === 'success') {
                // 清空消息显示
                if (this.kbChatMessages) {
                    this.kbChatMessages.innerHTML = '';
                }

                // 显示欢迎消息
                this.addKbChatMessage('ai', `你好！我是${this.currentKnowledgeBase.name}的AI助手，有什么可以帮助你的吗？`);

                this.showSuccessToast('对话已清除');
            } else {
                throw new Error(result?.message || '清除对话失败');
            }
        } catch (error) {
            console.error('清除知识库对话失败:', error);
            this.showErrorToast('清除对话失败: ' + error.message);
        }
    }

    /**
     * 加载文件对话历史
     */
    async loadFileConversationHistory(kbId, fileId, docName) {
        try {
            if (!api || !api.getFileConversationHistory) {
                console.error('API服务不可用');
                return;
            }

            const response = await api.getFileConversationHistory(kbId, fileId);

            if (response && response.status === 'success') {
                const messages = response.data?.messages || [];

                // 清空当前消息
                if (this.kbDocChatMessages) {
                    this.kbDocChatMessages.innerHTML = '';
                }

                // 渲染历史消息
                if (messages.length > 0) {
                    messages.forEach(msg => {
                        this.addKbDocChatMessage(msg.type === 'user' ? 'user' : 'ai', msg.content);
                    });
                } else {
                    // 如果没有历史消息，显示欢迎消息
                    this.addKbDocChatMessage('ai', `已加载 **${this.escapeHtml(docName)}**，您可以开始询问关于这个文档的任何问题！

例如：
- 这个文档的主要内容是什么？
- 文档中提到了哪些关键概念？
- 有哪些重要的数据或结论？`);
                }

                console.log(`✅ 成功加载文件对话历史: ${messages.length} 条消息`);
            } else {
                console.error('加载文件对话历史失败:', response?.message);
            }
        } catch (error) {
            console.error('加载文件对话历史失败:', error);
        }
    }

    /**
     * 清除文件对话
     */
    async clearFileConversation() {
        if (!this.currentKnowledgeBase || !this.currentDocument) {
            this.showErrorToast('当前文档信息不存在');
            return;
        }

        if (!confirm('确定要清除当前对话吗？')) {
            return;
        }

        try {
            if (!api || !api.clearFileConversation) {
                throw new Error('API服务不可用，请刷新页面重试');
            }

            const result = await api.clearFileConversation(this.currentKnowledgeBase.id, this.currentDocument.id);

            if (result && result.status === 'success') {
                // 清空消息显示
                if (this.kbDocChatMessages) {
                    this.kbDocChatMessages.innerHTML = '';
                }

                // 显示欢迎消息
                this.addKbDocChatMessage('ai', `已加载 **${this.escapeHtml(this.currentDocument.name)}**，您可以开始询问关于这个文档的任何问题！

例如：
- 这个文档的主要内容是什么？
- 文档中提到了哪些关键概念？
- 有哪些重要的数据或结论？`);

                this.showSuccessToast('对话已清除');
            } else {
                throw new Error(result?.message || '清除对话失败');
            }
        } catch (error) {
            console.error('清除文件对话失败:', error);
            this.showErrorToast('清除对话失败: ' + error.message);
        }
    }

    /**
     * 处理文档复选框变化
     */
    handleDocumentCheckboxChange(checkbox) {
        console.log('文档复选框状态变化:', checkbox.checked, checkbox.dataset.docId);
        
        // 更新全选复选框的状态
        this.updateSelectAllCheckbox();
    }
    
    /**
     * 处理全选复选框变化
     */
    handleSelectAllChange(selectAllCheckbox) {
        const isChecked = selectAllCheckbox.checked;
        console.log('全选复选框状态变化:', isChecked);
        
        // 设置所有文档复选框的状态
        const docCheckboxes = this.documentList.querySelectorAll('.doc-checkbox');
        docCheckboxes.forEach(cb => {
            cb.checked = isChecked;
        });
    }
    
    /**
     * 更新全选复选框的状态
     */
    updateSelectAllCheckbox() {
        const selectAllCheckbox = document.getElementById('selectAllCheckbox');
        if (!selectAllCheckbox || !this.documentList) return;
        
        const docCheckboxes = this.documentList.querySelectorAll('.doc-checkbox');
        if (docCheckboxes.length === 0) {
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = false;
            return;
        }
        
        const checkedCount = Array.from(docCheckboxes).filter(cb => cb.checked).length;
        
        if (checkedCount === 0) {
            // 全部未选中
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = false;
        } else if (checkedCount === docCheckboxes.length) {
            // 全部选中
            selectAllCheckbox.checked = true;
            selectAllCheckbox.indeterminate = false;
        } else {
            // 部分选中
            selectAllCheckbox.checked = false;
            selectAllCheckbox.indeterminate = true;
        }
    }

    /**
     * 处理文件上传
     */
    handleFileUpload() {
        console.log('📁 处理文件上传');
        
        // 创建文件输入元素
        const fileInput = document.createElement('input');
        fileInput.type = 'file';
        fileInput.multiple = true;
        fileInput.accept = '.pdf,.doc,.docx,.txt,.md';
        
        fileInput.addEventListener('change', (e) => {
            const files = Array.from(e.target.files);
            if (files.length === 0) return;
            
            console.log('选择了文件:', files);
            
            // 处理每个文件
            files.forEach(file => {
                this.uploadFile(file);
            });
        });
        
        // 触发文件选择
        fileInput.click();
    }

    /**
     * 上传单个文件
     */
    async uploadFile(file) {
        console.log('📤 上传文件:', file.name);
        
        // 检查是否有当前知识库
        if (!this.currentKnowledgeBase) {
            this.showErrorToast('请先选择一个知识库');
            return;
        }
        
        // 检查API是否可用
        if (typeof api === 'undefined' || !api || !api.uploadFileToKnowledgeBase) {
            this.showErrorToast('API服务不可用，请刷新页面重试');
            return;
        }
        
        // 显示上传进度
        this.showUploadProgress(file.name);
        
        try {
            // 使用知识库API上传文件
            const result = await api.uploadFileToKnowledgeBase(this.currentKnowledgeBase.id, file);
            
            if (result && result.status === 'success') {
                this.showSuccessToast(`文件 "${file.name}" 上传成功`);
                // 重新加载文档列表
                this.loadDocuments(this.currentKnowledgeBase.id);
                // 重新加载知识库列表以更新文件数量
                this.loadKnowledgeBases();
            } else {
                throw new Error(result?.message || '上传失败');
            }
        } catch (error) {
            console.error('文件上传失败:', error);
            this.showErrorToast(`文件 "${file.name}" 上传失败: ${error.message}`);
        } finally {
            // 隐藏上传进度
            this.hideUploadProgress();
        }
    }

    /**
     * 显示上传进度
     */
    showUploadProgress(fileName) {
        // 移除现有的进度提示
        this.hideUploadProgress();
        
        const progressDiv = document.createElement('div');
        progressDiv.id = 'uploadProgress';
        progressDiv.className = 'upload-progress';
        progressDiv.innerHTML = `
            <div class="progress-content">
                <span>正在上传: ${fileName}</span>
                <div class="progress-spinner"></div>
            </div>
        `;
        
        // 添加到文档列表顶部
        const documentList = document.getElementById('documentList');
        if (documentList) {
            documentList.insertBefore(progressDiv, documentList.firstChild);
        }
    }

    /**
     * 隐藏上传进度
     */
    hideUploadProgress() {
        const progressDiv = document.getElementById('uploadProgress');
        if (progressDiv) {
            progressDiv.remove();
        }
    }

    /**
     * 删除选中文档
     */
    async deleteSelectedDocuments() {
        const selected = this.documentList.querySelectorAll('.doc-checkbox:checked');
        if (selected.length === 0) {
            this.showErrorToast('请先选择要删除的文档');
            return;
        }

        if (!this.currentKnowledgeBase) {
            this.showErrorToast('当前知识库信息不存在');
            return;
        }

        if (confirm(`确定要删除选中的 ${selected.length} 个文档吗？`)) {
            let successCount = 0;
            let failCount = 0;

            // 逐个删除文件
            for (const checkbox of selected) {
                const docItem = checkbox.closest('.document-item');
                const docId = checkbox.dataset.docId;

                try {
                    if (docId) {
                        // 检查API是否可用
                        if (!api || !api.deleteFileFromKnowledgeBase) {
                            throw new Error('API服务不可用，请刷新页面重试');
                        }

                        // 使用知识库专用删除接口
                        const result = await api.deleteFileFromKnowledgeBase(
                            this.currentKnowledgeBase.id,
                            docId
                        );

                        if (result && result.status === 'success') {
                            successCount++;
                            // 从DOM中移除
                            if (docItem) {
                                docItem.style.opacity = '0.5';
                                setTimeout(() => {
                                    docItem.remove();
                                }, 300);
                            }
                        } else {
                            throw new Error(result?.message || '删除失败');
                        }
                    }
                } catch (error) {
                    console.error(`文档 ${docId} 删除失败:`, error);
                    failCount++;
                }
            }

            // 显示结果
            if (failCount === 0) {
                this.showSuccessToast(`已删除 ${successCount} 个文档`);
            } else {
                this.showErrorToast(`删除完成：成功 ${successCount} 个，失败 ${failCount} 个`);
            }

            // 重新加载文档列表和知识库列表
            if (this.currentKnowledgeBase) {
                this.loadDocuments(this.currentKnowledgeBase.id);
                this.loadKnowledgeBases();
            }
        }
    }

    /**
     * 处理AI-PPT任务
     */
    handleAiPptTask() {
        console.log('📊 启动AI-PPT任务');
        
        // 检查documentList是否已初始化
        if (!this.documentList) {
            console.error('❌ documentList未初始化，尝试重新获取');
            this.documentList = document.getElementById('documentList');
        }
        
        // 如果还是找不到，尝试从DOM中查找
        if (!this.documentList) {
            const detailView = document.getElementById('knowledgeBaseDetailView');
            if (detailView) {
                this.documentList = detailView.querySelector('#documentList');
            }
        }
        
        if (!this.documentList) {
            console.error('❌ 无法找到documentList元素');
            this.showErrorToast('页面元素未正确加载，请刷新页面重试');
            return;
        }
        
        // 获取选中的文档
        const selectedFiles = this.documentList.querySelectorAll('.doc-checkbox:checked');
        console.log('📄 选中的文档数量:', selectedFiles.length);
        
        if (selectedFiles.length === 0) {
            this.showErrorToast('请先选择至少一个文档');
            return;
        }
        
        // 显示弹窗
        this.showAiPptModal(Array.from(selectedFiles));
    }
    
    /**
     * 显示AI-PPT弹窗
     * @param {Array} selectedCheckboxes - 选中的复选框元素数组
     */
    showAiPptModal(selectedCheckboxes) {
        // 获取选中文档的信息
        const selectedDocs = selectedCheckboxes.map(checkbox => {
            const docItem = checkbox.closest('.document-item');
            const docId = checkbox.dataset.docId;
            const docName = docItem.querySelector('.doc-title')?.textContent || '未知文档';
            const docMeta = docItem.querySelector('.doc-meta')?.textContent || '';
            const docIcon = docItem.querySelector('.doc-icon')?.textContent || '📄';
            
            // 从documents数组中获取完整信息
            const fullDoc = this.documents.find(d => d.id === docId);
            
            return {
                id: docId,
                name: docName,
                meta: docMeta,
                icon: docIcon,
                size: fullDoc?.size || '',
                uploadedAt: fullDoc?.uploadedAt || '',
                type: fullDoc?.type || 'unknown'
            };
        });
        
        // 创建弹窗HTML
        const modalHTML = `
            <div class="ai-ppt-modal-overlay" id="aiPptModalOverlay">
                <div class="ai-ppt-modal">
                    <div class="ai-ppt-modal-header">
                        <div class="ai-ppt-modal-title">
                            <span>📊</span>
                            <span>AI-PPT 生成</span>
                        </div>
                        <button class="ai-ppt-modal-close" id="aiPptModalClose">×</button>
                    </div>
                    <div class="ai-ppt-modal-body">
                        <div class="ai-ppt-selected-docs">
                            <div class="ai-ppt-selected-docs-title">已选中的文档 (${selectedDocs.length})</div>
                            <div class="ai-ppt-doc-list">
                                ${selectedDocs.length > 0 
                                    ? selectedDocs.map(doc => `
                                        <div class="ai-ppt-doc-item">
                                            <div class="ai-ppt-doc-icon">${doc.icon}</div>
                                            <div class="ai-ppt-doc-info">
                                                <div class="ai-ppt-doc-name">${this.escapeHtml(doc.name)}</div>
                                                <div class="ai-ppt-doc-meta">${this.escapeHtml(doc.meta)}</div>
                                            </div>
                                        </div>
                                    `).join('')
                                    : '<div class="ai-ppt-empty-docs">未选择文档</div>'
                                }
                            </div>
                        </div>
                        <div class="ai-ppt-input-section">
                            <label class="ai-ppt-input-label" for="aiPptStyleInput">PPT风格要求</label>
                            <textarea 
                                class="ai-ppt-input" 
                                id="aiPptStyleInput" 
                                placeholder="例如：创建一个简洁专业的学术风格PPT，包含封面、目录、内容页和总结页，使用蓝色主题色调，适合学术会议展示..."
                            ></textarea>
                            <div class="ai-ppt-input-placeholder">请描述您希望创建的PPT风格、主题、结构等要求</div>
                        </div>
                    </div>
                    <div class="ai-ppt-modal-footer">
                        <button class="ai-ppt-btn ai-ppt-btn-cancel" id="aiPptModalCancel">取消</button>
                        <button class="ai-ppt-btn ai-ppt-btn-confirm" id="aiPptModalConfirm">确定</button>
                    </div>
                </div>
            </div>
        `;
        
        // 移除现有弹窗（如果存在）
        const existingModal = document.getElementById('aiPptModalOverlay');
        if (existingModal) {
            existingModal.remove();
        }
        
        // 添加到页面
        document.body.insertAdjacentHTML('beforeend', modalHTML);
        
        // 获取弹窗元素
        const modalOverlay = document.getElementById('aiPptModalOverlay');
        const modalClose = document.getElementById('aiPptModalClose');
        const modalCancel = document.getElementById('aiPptModalCancel');
        const modalConfirm = document.getElementById('aiPptModalConfirm');
        const styleInput = document.getElementById('aiPptStyleInput');
        
        // 显示动画
        setTimeout(() => {
            modalOverlay.classList.add('show');
        }, 10);
        
        // 关闭弹窗函数
        const closeModal = () => {
            modalOverlay.classList.remove('show');
            setTimeout(() => {
                modalOverlay.remove();
            }, 300);
        };
        
        // 绑定事件
        modalClose.addEventListener('click', closeModal);
        modalCancel.addEventListener('click', closeModal);
        
        // 点击遮罩层关闭
        modalOverlay.addEventListener('click', (e) => {
            if (e.target === modalOverlay) {
                closeModal();
            }
        });
        
        // ESC键关闭
        const handleEsc = (e) => {
            if (e.key === 'Escape') {
                closeModal();
                document.removeEventListener('keydown', handleEsc);
            }
        };
        document.addEventListener('keydown', handleEsc);
        
        // 确定按钮事件
        modalConfirm.addEventListener('click', () => {
            const styleRequirement = styleInput.value.trim();
            
            if (!styleRequirement) {
                this.showErrorToast('请输入PPT风格要求');
                styleInput.focus();
                return;
            }
            
            // 获取选中的文档ID
            const selectedDocIds = selectedDocs.map(doc => doc.id);
            
            console.log('📊 提交AI-PPT任务:', {
                kbId: this.currentKnowledgeBase?.id,
                docIds: selectedDocIds,
                styleRequirement: styleRequirement
            });
            
            // 关闭弹窗
            closeModal();
            
            // 调用后端API生成PPT
            this.submitAiPptTask(selectedDocIds, styleRequirement);
        });
        
        // 自动聚焦输入框
        setTimeout(() => {
            styleInput.focus();
        }, 100);
    }

    /**
         * 提交AI-PPT任务到后端
         * @param {Array} fileIds - 选中的文档ID列表
         * @param {string} styleRequirement - PPT风格要求
         */
        async submitAiPptTask(fileIds, styleRequirement) {
            if (!this.currentKnowledgeBase) {
                this.showErrorToast('当前知识库信息不存在');
                return;
            }
    
            const kbId = this.currentKnowledgeBase.id;
    
            try {
                // TODO: 暂时注释掉真实 API 调用，使用 mock 行为
                // // 检查API是否可用
                // if (typeof api === 'undefined' || !api || !api.generateAiPpt) {
                //     throw new Error('API服务不可用，请刷新页面重试');
                // }
    
                // // 显示提交提示
                // this.showInfoToast('AI-PPT任务已提交，正在生成中...');
    
                // // 调用后端API
                // const response = await api.generateAiPpt(kbId, fileIds, styleRequirement);
    
                // if (response && response.status === 'success') {
                //     // 检查是否有任务ID（异步模式）
                //     if (response.task_id) {
                //         console.log('✅ AI-PPT任务已创建（异步模式），任务ID:', response.task_id);
                //         this.showSuccessToast(`AI-PPT生成任务已提交！任务ID: ${response.task_id}`);
                //         // 立即刷新任务列表
                //         await this.loadTasks(kbId);
                //         // TODO: 暂时注释掉轮询启动
                //         // // 如果没有轮询，启动轮询
                //         // if (!this.taskPollingInterval) {
                //         //     this.startTaskPolling(kbId);
                //         // }
                //     }
                //     // 检查是否有直接返回的内容（同步模式）
                //     else if (response.content) {
                //         console.log('✅ AI-PPT生成完成（同步模式）');
                //         this.showSuccessToast('AI-PPT生成完成！');
                //         // TODO: 可以显示生成的内容或提供下载
                //         console.log('📄 生成的内容:', response.content);
                //         if (response.metadata) {
                //             console.log('📊 元数据:', response.metadata);
                //         }
                //     } else {
                //         // 其他成功响应
                //         this.showSuccessToast('AI-PPT任务已成功提交！');
                //     }
                // } else {
                //     throw new Error(response?.message || '生成PPT失败');
                // }
    
                // Mock 行为
                this.showInfoToast('AI-PPT任务已提交，正在生成中...');
    
                setTimeout(() => {
                    const mockTask = {
                        task_id: `mock_task_${Date.now()}`,
                        user_id: 'mock_user',
                        kb_id: kbId,
                        generation_type: 'ppt',
                        file_ids: fileIds,
                        query: styleRequirement,
                        status: 'processing',
                        progress: 20,
                        message: '正在生成PPT内容...',
                        created_at: new Date().toISOString(),
                        updated_at: new Date().toISOString()
                    };
    
                    this.tasks.unshift(mockTask);
                    this.renderTasks();
                    this.showSuccessToast(`AI-PPT生成任务已提交！任务ID: ${mockTask.task_id} (Mock 数据)`);
                }, 500);
            } catch (error) {
                console.error('❌ AI-PPT任务提交失败:', error);
                this.showErrorToast(`AI-PPT任务提交失败: ${error.message}`);
            }
        }    
    /**
     * 处理研究报告任务
     */
    handleReportTask() {
        console.log('📝 启动研究报告任务');
        this.showInfoToast('研究报告功能即将上线，敬请期待！');
        
        // TODO: 实现研究报告功能
        // 1. 获取选中的文档
        // 2. 调用后端API生成研究报告
        // 3. 显示进度和结果
    }

    /**
     * 更新哈希路由
     */
    updateHash(hash) {
        if (window.location.hash !== hash) {
            window.location.hash = hash;
        }
    }

    /**
     * 处理哈希变化
     */
    handleHashChange() {
        const hash = window.location.hash;
        
        if (hash === '#/knowledge-bases') {
            this.showKnowledgeBaseView();
        } else if (hash.startsWith('#/knowledge-bases/')) {
            const parts = hash.split('/');
            const kbId = parts[2];
            if (kbId) {
                this.showKnowledgeBaseDetail(kbId);
            }
        }
        // 其他路由由其他模块处理
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
     * 显示信息提示
     */
    showInfoToast(message) {
        this.showToast(message, 'info');
    }

    /**
     * 处理文档点击事件
     * @param {string} docId - 文档ID
     * @param {HTMLElement} docItem - 文档项DOM元素
     */
    async handleDocumentClick(docId, docItem) {
        console.log('📄 点击文档:', docId);
        
        // 获取文档信息
        const docName = docItem.querySelector('.doc-title')?.textContent || '未知文档';
        const doc = this.documents.find(d => d.id === docId);
        
        if (!doc) {
            this.showErrorToast('文档信息不存在');
            return;
        }
        
        // 只支持PDF文件
        if (doc.type !== 'pdf') {
            this.showInfoToast('目前仅支持PDF文件的预览');
            return;
        }
        
        // 打开PDF阅读器
        await this.openKbPdfViewer(docId, docName, doc);
    }
    
    /**
     * 打开知识库PDF阅读器
     * @param {string} docId - 文档ID
     * @param {string} docName - 文档名称
     * @param {Object} doc - 文档对象
     */
    async openKbPdfViewer(docId, docName, doc) {
        if (!this.kbPdfViewer || !this.kbPdfFrame || !this.kbChatPanel) {
            console.error('❌ PDF阅读器元素未找到');
            return;
        }
        
        // 保存当前文档信息
        this.currentDocument = { id: docId, name: docName, ...doc };
        
        // 隐藏对话窗口，显示PDF阅读器
        this.kbChatPanel.style.display = 'none';
        this.kbPdfViewer.style.display = 'flex';
        
        // 折叠任务面板
        if (this.taskPanel) {
            this.taskPanel.classList.add('collapsed');
        }
        
        // 设置PDF文件名
        if (this.kbPdfFileName) {
            this.kbPdfFileName.textContent = docName;
        }
        
        // 设置PDF iframe源 - 直接使用知识库文件的content接口，添加preview参数
        const kbId = this.currentKnowledgeBase?.id;
        if (kbId) {
            // 使用content接口，添加preview=true参数以支持在iframe中显示
            this.kbPdfFrame.src = `/api/knowledge/base/${kbId}/files/${docId}/content?preview=true`;
        } else {
            // 如果没有知识库ID，使用文件系统接口
            this.kbPdfFrame.src = `/api/file/view?id=${encodeURIComponent(docId)}`;
        }

        // 加载文件对话历史
        await this.loadFileConversationHistory(kbId, docId, docName);
        
        // 平滑过渡动画
        requestAnimationFrame(() => {
            this.kbPdfViewer.style.opacity = '0';
            setTimeout(() => {
                this.kbPdfViewer.style.transition = 'opacity 0.3s ease';
                this.kbPdfViewer.style.opacity = '1';
            }, 10);
        });
        
        console.log('✅ PDF阅读器已打开:', docName);
    }
    
    /**
     * 关闭知识库PDF阅读器
     */
    closeKbPdfViewer() {
        if (!this.kbPdfViewer || !this.kbChatPanel) {
            return;
        }
        
        // 隐藏PDF阅读器，显示对话窗口
        this.kbPdfViewer.style.display = 'none';
        this.kbChatPanel.style.display = 'flex';
        
        // 展开任务面板
        if (this.taskPanel) {
            this.taskPanel.classList.remove('collapsed');
        }
        
        // 清空PDF iframe
        if (this.kbPdfFrame) {
            this.kbPdfFrame.src = '';
        }
        
        // 清空当前文档
        this.currentDocument = null;
        
        console.log('✅ PDF阅读器已关闭');
    }
    
    /**
     * 切换文档对话区折叠/展开
     */
    toggleKbDocChat() {
        if (!this.kbDocChatArea || !this.kbPdfDisplayArea) {
            return;
        }
        
        const isHidden = this.kbDocChatArea.style.display === 'none';
        
        if (isHidden) {
            // 显示对话区
            this.kbDocChatArea.style.display = 'flex';
            this.kbPdfDisplayArea.style.flex = '0 0 70%';
            if (this.kbChatToggleBtn) {
                this.kbChatToggleBtn.textContent = '◀';
            }
        } else {
            // 隐藏对话区
            this.kbDocChatArea.style.display = 'none';
            this.kbPdfDisplayArea.style.flex = '1 1 auto';
            if (this.kbChatToggleBtn) {
                this.kbChatToggleBtn.textContent = '▶';
            }
        }
    }
    
    /**
     * 处理文档对话发送
     */
    async handleDocChatSend() {
        if (!this.kbDocChatInput || !this.currentDocument) {
            return;
        }
        
        const message = this.kbDocChatInput.value.trim();
        if (!message) {
            return;
        }
        
        // 添加用户消息
        this.addKbDocChatMessage('user', message);
        
        // 清空输入框
        this.kbDocChatInput.value = '';
        
        // 获取功能开关状态
        const kbDocSwitchNet = document.getElementById('kbDocSwitchNet');
        const kbDocSwitchKb = document.getElementById('kbDocSwitchKb');
        const useNet = kbDocSwitchNet?.classList.contains('active') || false;
        const useKb = kbDocSwitchKb?.classList.contains('active') || false;
        
        // 添加加载指示器
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'message ai';
        loadingDiv.innerHTML = `
            <div class="message-bubble typing-indicator">
                AI 正在思考<span class="dot"></span><span class="dot"></span><span class="dot"></span>
            </div>
        `;
        if (this.kbDocChatMessages) {
            this.kbDocChatMessages.appendChild(loadingDiv);
            this.kbDocChatMessages.scrollTop = this.kbDocChatMessages.scrollHeight;
        }
        
        try {
            const kbId = this.currentKnowledgeBase?.id;
            const fileId = this.currentDocument.id;
            
            // 调用文档对话API
            const response = await fetch(`/api/knowledge/base/${kbId}/files/${fileId}/chat/stream`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
                },
                body: JSON.stringify({
                    query: message,
                    use_kb: useKb,
                    net: useNet
                })
            });
            
            // 移除加载指示器
            loadingDiv.remove();
            
            if (!response.ok) {
                throw new Error(`API调用失败: ${response.status}`);
            }
            
            // 处理流式响应
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let fullResponse = '';
            
            // 添加AI消息容器
            const aiMessageDiv = document.createElement('div');
            aiMessageDiv.className = 'message ai';
            aiMessageDiv.innerHTML = `
                <div class="message-bubble">
                    <div class="markdown-content"></div>
                </div>
            `;
            if (this.kbDocChatMessages) {
                this.kbDocChatMessages.appendChild(aiMessageDiv);
            }
            const contentDiv = aiMessageDiv.querySelector('.markdown-content');
            
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';
                
                for (const line of lines) {
                    const trimmed = line.trim();
                    if (trimmed.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(trimmed.slice(6));
                            if (data.chunk) {
                                fullResponse += data.chunk;
                                if (contentDiv) {
                                    contentDiv.innerHTML = typeof marked !== 'undefined' 
                                        ? marked.parse(fullResponse) 
                                        : this.escapeHtml(fullResponse);
                                    if (this.kbDocChatMessages) {
                                        this.kbDocChatMessages.scrollTop = this.kbDocChatMessages.scrollHeight;
                                    }
                                }
                            }
                        } catch (e) {
                            console.error('解析流式数据失败:', e);
                        }
                    }
                }
            }
            
            // 应用代码高亮
            if (typeof Prism !== 'undefined' && contentDiv) {
                contentDiv.querySelectorAll('pre code').forEach(block => Prism.highlightElement(block));
            }
            
        } catch (error) {
            console.error('文档对话失败:', error);
            loadingDiv.remove();
            this.addKbDocChatMessage('ai', `抱歉，对话过程中出现错误：${error.message}`);
        }
    }
    
    /**
     * 添加文档对话消息
     */
    addKbDocChatMessage(role, content) {
        if (!this.kbDocChatMessages) return;
        
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        
        const renderedContent = (role === 'ai' && typeof marked !== 'undefined') 
            ? marked.parse(content) 
            : this.escapeHtml(content);
        
        messageDiv.innerHTML = `
            <div class="message-bubble">
                <div class="markdown-content">${renderedContent}</div>
            </div>
        `;
        
        this.kbDocChatMessages.appendChild(messageDiv);
        
        // 应用代码高亮
        if (role === 'ai' && typeof Prism !== 'undefined') {
            messageDiv.querySelectorAll('pre code').forEach(block => Prism.highlightElement(block));
        }
        
        this.kbDocChatMessages.scrollTop = this.kbDocChatMessages.scrollHeight;
    }
    
    /**
     * 初始化PDF阅读器拖拽调整功能
     */
    initKbPdfResizer() {
        if (!this.kbPdfResizer || !this.kbPdfDisplayArea || !this.kbDocChatArea) {
            return;
        }
        
        let isResizing = false;
        let startX = 0;
        let startDisplayWidth = 0;
        
        this.kbPdfResizer.addEventListener('mousedown', (e) => {
            isResizing = true;
            startX = e.clientX;
            startDisplayWidth = this.kbPdfDisplayArea.offsetWidth;
            document.body.style.cursor = 'col-resize';
            e.preventDefault();
        });
        
        document.addEventListener('mousemove', (e) => {
            if (!isResizing) return;
            
            const deltaX = e.clientX - startX;
            const viewerWidth = this.kbPdfViewer.clientWidth;
            let newDisplayWidth = startDisplayWidth + deltaX;
            let newChatWidth = viewerWidth - newDisplayWidth;
            
            // 限制最小宽度
            const minDisplayWidth = viewerWidth * 0.3;
            const minChatWidth = 200;
            
            if (newDisplayWidth < minDisplayWidth) {
                newDisplayWidth = minDisplayWidth;
                newChatWidth = viewerWidth - newDisplayWidth;
            } else if (newChatWidth < minChatWidth) {
                newChatWidth = minChatWidth;
                newDisplayWidth = viewerWidth - newChatWidth;
            }
            
            this.kbPdfDisplayArea.style.width = `${newDisplayWidth}px`;
            this.kbDocChatArea.style.width = `${newChatWidth}px`;
            this.kbPdfDisplayArea.style.flex = 'none';
            this.kbDocChatArea.style.flex = 'none';
        });
        
        document.addEventListener('mouseup', () => {
            if (isResizing) {
                isResizing = false;
                document.body.style.cursor = '';
            }
        });
    }
    
    /**
     * 显示提示消息
     */
    showToast(message, type = 'success') {
        // 移除现有提示
        const existingToast = document.querySelector('.success-toast, .error-toast, .info-toast');
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
}

// 创建全局实例
window.knowledgeBaseManager = new KnowledgeBaseManager();

// 导出初始化函数
export function initKnowledgeBase() {
    window.knowledgeBaseManager.init();
}
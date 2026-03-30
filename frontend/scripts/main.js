// 先导入API模块，确保它在其他模块使用前加载完成
import './services/api.js';

// 引入各个模块的初始化函数
import { initSidebar } from './modules/sidebar.js';
// import { initFileManager } from './modules/fileManager.js';  // 暂时注释掉
import { initPdfViewer } from './modules/pdfViewer.js';
import { initChat } from './modules/chat.js';
import { initRecommendation } from './modules/recommendation.js';
import { initKnowledgeBase } from './modules/knowledgeBase.js';
import ConversationManager from './modules/conversation-manager.js';
import GeminiScrollManager from './modules/gemini-scroll.js';

// 等待 DOM 加载完成
document.addEventListener('DOMContentLoaded', async () => {
    console.log('✨ System initializing...');

    // 1. 启动侧边栏模块
    initSidebar();

    // 2. 启动对话管理器
    await window.conversationManager.init();

    // 3. 启动 Gemini 滚动管理器
    window.geminiScrollManager.init();

    // 4. 启动 PDF 阅读器模块 (注册全局事件)
    initPdfViewer();

    // 5. 启动文件管理器 (加载文件树) - 暂时注释掉
    // initFileManager();

    // 6. 启动知识库模块
    initKnowledgeBase();

    // 7. 启动主聊天窗口
    initChat();

    // 8. 启动论文推荐系统
    initRecommendation();
    
    console.log('✅ System ready.');
});
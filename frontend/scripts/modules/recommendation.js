import { api } from '../services/api.js';
import { throttle } from '../utils/helpers.js';
import { showChatView } from './chat.js';

// DOM 元素缓存
const elements = {
    input: document.getElementById('keywordsInput'),
    tagsContainer: document.getElementById('keywordTags'),
    listContainer: document.getElementById('papersList'),
    tooltip: document.getElementById('paperTooltip')
};

// 状态
let keywords = ['推荐系统', '大语言模型']; // 默认标签
let papers = [];
let allPapers = []; // 所有论文数据
let displayedPapersCount = 0; // 已显示的论文数量
const pageSize = 12; // 每页显示的论文数量
const tooltipCache = new Map(); // 缓存 Markdown 解析结果，提升性能
let isLoading = false; // 是否正在加载数据，防止重复请求
let hasMoreData = true; // 是否还有更多数据可加载

// 虚拟论文数据
const mockPapers = [
    {
        id: 'mock_1',
        title: 'Attention Is All You Need: Transformer架构的革命性突破',
        authors: 'Vaswani et al.',
        year: '2017',
        abstract: '本文提出了Transformer模型，完全基于注意力机制，摒弃了传统的循环和卷积结构。在机器翻译任务上取得了最好的成绩，同时训练效率大幅提升。这一架构已成为现代大语言模型的基础。',
        isParsed: false,
        source: 'arxiv'
    },
    {
        id: 'mock_2',
        title: 'BERT: Pre-training of Deep Bidirectional Transformers for Language Understanding',
        authors: 'Devlin et al.',
        year: '2018',
        abstract: 'BERT是一种新的语言表示模型，通过在所有层中联合调节左右上下文来预训练深度双向表示。BERT是第一个深度双向的、无监督的语言表示模型，仅需一个额外的输出层就可以针对广泛任务创建最先进的模型。',
        isParsed: false,
        source: 'arxiv'
    },
    {
        id: 'mock_3',
        title: 'GPT-3: Language Models are Few-Shot Learners',
        authors: 'Brown et al.',
        year: '2020',
        abstract: 'GPT-3是一个1750亿参数的自回归语言模型，在few-shot学习方面表现惊人。无需微调就能完成多种任务，展示了大规模语言模型的强大潜力。',
        isParsed: false,
        source: 'arxiv'
    },
    {
        id: 'mock_4',
        title: 'Deep Residual Learning for Image Recognition',
        authors: 'He et al.',
        year: '2016',
        abstract: '深度残差网络解决了深度神经网络训练中的退化问题。通过引入快捷连接，使得训练极深的神经网络成为可能。ResNet在ImageNet竞赛中取得了突破性成果。',
        isParsed: false,
        source: 'cvpr'
    },
    {
        id: 'mock_5',
        title: 'Generative Adversarial Networks',
        authors: 'Goodfellow et al.',
        year: '2014',
        abstract: '生成对抗网络(GAN)通过让生成器和判别器相互对抗来学习数据的分布。这一框架在图像生成、图像编辑等领域取得了巨大成功。',
        isParsed: false,
        source: 'neurips'
    },
    {
        id: 'mock_6',
        title: 'Variational Autoencoders for Deep Learning',
        authors: 'Kingma & Welling',
        year: '2014',
        abstract: '变分自编码器(VAE)是一种生成模型，通过变分推断学习数据的潜在表示。在图像生成、数据压缩等领域有广泛应用。',
        isParsed: false,
        source: 'iclr'
    },
    {
        id: 'mock_7',
        title: 'Reinforcement Learning: An Introduction',
        authors: 'Sutton & Barto',
        year: '2018',
        abstract: '强化学习是机器学习的重要分支，通过智能体与环境的交互来学习最优策略。本书全面介绍了强化学习的理论基础和实践方法。',
        isParsed: false,
        source: 'book'
    },
    {
        id: 'mock_8',
        title: 'The Landscape of Transformer-based Language Models',
        authors: 'Liu et al.',
        year: '2023',
        abstract: '本文全面回顾了基于Transformer的语言模型发展历程，从BERT到GPT系列，分析了各种模型的优缺点和应用场景。',
        isParsed: false,
        source: 'survey'
    },
    {
        id: 'mock_9',
        title: 'Efficient Transformers: A Survey',
        authors: 'Taylor et al.',
        year: '2022',
        abstract: 'Transformer模型虽然效果强大，但计算复杂度高。本文综述了各种高效Transformer变体，包括稀疏注意力、线性注意力等方法。',
        isParsed: false,
        source: 'survey'
    },
    {
        id: 'mock_10',
        title: 'Self-Supervised Learning for Computer Vision',
        authors: 'Chen et al.',
        year: '2021',
        abstract: '自监督学习在计算机视觉领域取得了重大进展。本文介绍了各种自监督学习方法，包括对比学习、掩码图像建模等。',
        isParsed: false,
        source: 'survey'
    },
    {
        id: 'mock_11',
        title: 'Neural Architecture Search: A Survey',
        authors: 'Elsken et al.',
        year: '2019',
        abstract: '神经架构搜索(NAS)自动设计神经网络结构。本文综述了NAS的各种方法，包括强化学习、进化算法、梯度-based方法等。',
        isParsed: false,
        source: 'survey'
    },
    {
        id: 'mock_12',
        title: 'Federated Learning: Challenges and Opportunities',
        authors: 'Kairouz et al.',
        year: '2021',
        abstract: '联邦学习允许在保护隐私的前提下进行分布式机器学习。本文全面分析了联邦学习的挑战、机遇和未来发展方向。',
        isParsed: false,
        source: 'survey'
    },
    {
        id: 'mock_13',
        title: 'Explainable AI: Interpreting, Explaining and Visualizing Deep Learning',
        authors: 'Samek et al.',
        year: '2021',
        abstract: '可解释AI是深度学习的重要研究方向。本书介绍了各种解释方法，包括显著性图、特征归因、概念向量等。',
        isParsed: false,
        source: 'book'
    },
    {
        id: 'mock_14',
        title: 'Graph Neural Networks: A Review of Methods and Applications',
        authors: 'Wu et al.',
        year: '2021',
        abstract: '图神经网络(GNN)在图数据学习方面表现出色。本文综述了GNN的各种方法，包括GCN、GAT、GraphSAGE等，以及它们的应用。',
        isParsed: false,
        source: 'survey'
    },
    {
        id: 'mock_15',
        title: 'Meta-Learning: A Survey',
        authors: 'Hospedales et al.',
        year: '2022',
        abstract: '元学习让模型学会学习，是少样本学习的重要方法。本文综述了元学习的各种方法，包括基于度量、基于模型、基于优化等。',
        isParsed: false,
        source: 'survey'
    }
];

/**
 * 生成更多mock数据（用于无限滚动测试）
 */
function generateMockPapers(count = 200) {
    const topics = [
        '深度学习', '机器学习', '神经网络', '计算机视觉', '自然语言处理',
        '强化学习', '生成模型', 'Transformer', '注意力机制', '图神经网络',
        '元学习', '迁移学习', '联邦学习', '自监督学习', '对比学习',
        '多模态学习', '知识蒸馏', '模型压缩', '神经架构搜索', '可解释AI'
    ];
    const sources = ['arxiv', 'cvpr', 'neurips', 'iclr', 'survey', 'book'];
    const years = ['2024', '2023', '2022', '2021', '2020', '2019', '2018', '2017'];
    
    const generated = [];
    for (let i = 1; i <= count; i++) {
        const topic = topics[i % topics.length];
        const source = sources[i % sources.length];
        const year = years[i % years.length];
        
        generated.push({
            id: `mock_gen_${i}`,
            title: `${topic}的最新研究进展与应用 (${i})`,
            authors: `Author${i} et al.`,
            year: year,
            abstract: `这是关于${topic}的第${i}篇论文摘要。本文深入探讨了${topic}在人工智能领域的最新应用和发展趋势，包括理论基础、实验方法和实际应用场景。通过大量的实验验证，我们证明了所提出方法的有效性和优越性。该方法在多个基准数据集上取得了state-of-the-art的性能。`,
            isParsed: i % 3 === 0, // 每3篇中有一篇已解析
            source: source
        });
    }
    return generated;
}

/**
 * 模块初始化
 */
export function initRecommendation() {
    console.log('Initializing Recommendation Module...');

    // 1. 初始渲染
    renderKeywords();
    loadInitialPapers(); // 加载初始论文

    // 2. 绑定输入事件
    elements.input.addEventListener('keypress', (e) => {
        if (e.key === 'Enter') {
            const val = elements.input.value.trim();
            if (val && !keywords.includes(val)) {
                keywords.push(val);
                renderKeywords();
                triggerSearch();
                elements.input.value = '';
            }
        }
    });
    
    // 3. 绑定滚动加载更多（使用节流优化性能）
    const throttledHandleScroll = throttle(handleScroll, 200); // 200ms 节流
    
    // 绑定到实际的滚动容器（papersView 是主滚动容器）
    const papersView = document.getElementById('papersView');
    if (papersView) {
        papersView.addEventListener('scroll', throttledHandleScroll);
    }
    // 同时绑定到 listContainer（以防万一）
    elements.listContainer.addEventListener('scroll', throttledHandleScroll);
    
    // 4. 绑定头部隐藏/显示的滚动监听
    initHeaderScroll();
}

/**
 * 初始化头部滚动隐藏功能
 */
function initHeaderScroll() {
    const papersHeader = document.querySelector('.papers-header');
    const papersView = document.getElementById('papersView');
    let lastScrollTop = 0;
    let scrollThreshold = 100; // 滚动阈值
    
    papersView.addEventListener('scroll', () => {
        const scrollTop = papersView.scrollTop;
        
        // 向下滚动超过阈值时隐藏头部
        if (scrollTop > scrollThreshold && scrollTop > lastScrollTop) {
            papersHeader.classList.add('hidden');
        } 
        // 向上滚动时显示头部
        else if (scrollTop < lastScrollTop) {
            papersHeader.classList.remove('hidden');
        }
        
        lastScrollTop = scrollTop;
    });
}

/**
 * 渲染顶部 Tag 区域
 */
function renderKeywords() {
    elements.tagsContainer.innerHTML = keywords.map(k => `
        <span class="keyword-tag">
            ${k}
            <span class="remove" data-key="${k}">×</span>
        </span>
    `).join('');

    // 绑定删除事件
    elements.tagsContainer.querySelectorAll('.remove').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const keyToRemove = e.target.dataset.key;
            keywords = keywords.filter(k => k !== keyToRemove);
            renderKeywords();
            triggerSearch();
        });
    });
}

/**
 * 显示加载动画
 */
function showLoading() {
    // 移除已存在的loading
    const existingLoader = elements.listContainer.querySelector('.loading-spinner-container');
    if (existingLoader) {
        existingLoader.remove();
    }
    
    const loader = document.createElement('div');
    loader.className = 'loading-spinner-container';
    loader.innerHTML = `
        <div class="loading-spinner">
            <div class="spinner-ring"></div>
            <div class="spinner-ring"></div>
            <div class="spinner-ring"></div>
            <div class="spinner-ring"></div>
        </div>
        <div class="loading-text">加载中...</div>
    `;
    elements.listContainer.appendChild(loader);
}

/**
 * 隐藏加载动画
 */
function hideLoading() {
    const loader = elements.listContainer.querySelector('.loading-spinner-container');
    if (loader) {
        loader.remove();
    }
}

/**
 * 加载初始论文
 */
async function loadInitialPapers() {
    // 显示初始loading
    showLoading();
    
    // 重置状态
    isLoading = false;
    hasMoreData = true;
    displayedPapersCount = 0;
    papers = [];
    allPapers = [];
    
    // 模拟API延迟
    await new Promise(resolve => setTimeout(resolve, 500));
    
    try {
        // 1. 先获取已解析的论文（暂时注释，使用mock数据）
        // const res = await api.searchPapers(keywords);
        // let parsedPapers = [];
        // if (res && res.papers) {
        //     parsedPapers = res.papers.map(p => ({ ...p, isParsed: true, source: 'local' }));
        // }
        
        // 2. 生成足够多的mock数据用于无限滚动测试
        const mockData = generateMockPapers(200); // 生成200条mock数据
        
        // 3. 合并原有的15条mock数据和生成的mock数据
        allPapers = [...mockPapers, ...mockData];
        
        // 4. 按年份排序（最新的在前）
        allPapers.sort((a, b) => parseInt(b.year) - parseInt(a.year));
        
        // 5. 检查是否有数据
        if (allPapers.length === 0) {
            hideLoading();
            elements.listContainer.innerHTML = '<div style="color:#999;text-align:center;padding:20px">暂无论文数据</div>';
            hasMoreData = false;
            return;
        }
        
        // 6. 初始显示第一页
        loadMorePapers();
        
    } catch (err) {
        console.error('Load papers error:', err);
        hideLoading();
        // 如果加载失败，只显示虚拟数据
        allPapers = [...mockPapers];
        if (allPapers.length === 0) {
            elements.listContainer.innerHTML = '<div style="color:red;text-align:center;padding:20px">加载失败，请稍后重试</div>';
            hasMoreData = false;
            return;
        }
        displayedPapersCount = 0;
        loadMorePapers();
    }
}

/**
 * 加载更多论文
 */
function loadMorePapers() {
    // 防止重复加载
    if (isLoading) {
        return;
    }
    
    // 如果没有更多数据，直接返回
    if (!hasMoreData || displayedPapersCount >= allPapers.length) {
        return;
    }
    
    isLoading = true;
    
    // 移除之前的"已加载全部论文"提示
    const existingNoMoreMsg = elements.listContainer.querySelector('.no-more-papers');
    if (existingNoMoreMsg) {
        existingNoMoreMsg.remove();
    }
    
    const isFirstLoad = displayedPapersCount === 0;
    
    // 如果不是首次加载，显示加载动画
    if (!isFirstLoad) {
        showLoading();
    }
    
    // 模拟网络延迟（实际使用时可以移除或调整）
    setTimeout(() => {
        try {
            const endIndex = Math.min(displayedPapersCount + pageSize, allPapers.length);
            const newPapers = allPapers.slice(displayedPapersCount, endIndex);
            
            if (newPapers.length === 0) {
                hasMoreData = false;
                isLoading = false;
                hideLoading();
                return;
            }
            
            // 更新已显示的论文列表
            if (isFirstLoad) {
                // 首次加载，清空容器并重置列表
                papers = newPapers;
                elements.listContainer.innerHTML = '';
            } else {
                // 追加加载
                papers = [...papers, ...newPapers];
            }
            
            displayedPapersCount = endIndex;
            
            // 隐藏加载动画
            hideLoading();
            
            // 渲染新论文
            if (isFirstLoad) {
                // 首次加载，替换全部内容
                renderPaperList(papers, false);
            } else {
                // 追加加载
                renderPaperList(newPapers, false);
            }
            
            // 检查是否还有更多数据
            if (displayedPapersCount >= allPapers.length) {
                hasMoreData = false;
                const noMoreMsg = document.createElement('div');
                noMoreMsg.className = 'no-more-papers';
                noMoreMsg.textContent = '已加载全部论文';
                noMoreMsg.style.cssText = 'text-align: center; color: #999; padding: 20px;';
                elements.listContainer.appendChild(noMoreMsg);
            }
            
            isLoading = false;
        } catch (err) {
            console.error('Load more papers error:', err);
            isLoading = false;
            hideLoading();
            const errorMsg = document.createElement('div');
            errorMsg.className = 'load-error';
            errorMsg.textContent = '加载失败，请重试';
            errorMsg.style.cssText = 'text-align: center; color: #f44336; padding: 20px;';
            elements.listContainer.appendChild(errorMsg);
        }
    }, 300); // 300ms 延迟，模拟网络请求
}

/**
 * 处理滚动事件
 */
function handleScroll() {
    // 如果正在加载或没有更多数据，直接返回
    if (isLoading || !hasMoreData) {
        return;
    }
    
    // 获取滚动容器（优先使用 papersView，否则使用 listContainer）
    const papersView = document.getElementById('papersView');
    const scrollContainer = papersView || elements.listContainer;
    
    const { scrollTop, scrollHeight, clientHeight } = scrollContainer;
    
    // 当滚动到底部附近时（距离底部100px）加载更多
    const threshold = 100;
    if (scrollTop + clientHeight >= scrollHeight - threshold) {
        if (displayedPapersCount < allPapers.length) {
            loadMorePapers();
        }
    }
}

/**
 * 触发搜索并渲染列表
 */
async function triggerSearch() {
    if (keywords.length === 0) {
        elements.listContainer.innerHTML = '<div style="color:#999;text-align:center;padding:20px">请添加关键词以获取推荐</div>';
        // 重置状态
        isLoading = false;
        hasMoreData = false;
        displayedPapersCount = 0;
        papers = [];
        allPapers = [];
        return;
    }

    // 显示加载动画
    showLoading();
    
    // 重置状态
    isLoading = false;
    hasMoreData = true;
    displayedPapersCount = 0;
    papers = [];
    allPapers = [];

    try {
        // 暂时使用mock数据（后端接口未完成）
        // const res = await api.searchPapers(keywords);
        
        // 生成足够多的mock数据用于无限滚动测试
        const mockData = generateMockPapers(200);
        
        // 合并原有的15条mock数据和生成的mock数据
        allPapers = [...mockPapers, ...mockData];
        
        // 按年份排序（最新的在前）
        allPapers.sort((a, b) => parseInt(b.year) - parseInt(a.year));
        
        // 检查是否有数据
        if (allPapers.length === 0) {
            hideLoading();
            elements.listContainer.innerHTML = '<div style="color:#999;text-align:center;padding:20px">未找到相关论文</div>';
            hasMoreData = false;
            return;
        }
        
        // 加载第一页
        loadMorePapers();

    } catch (err) {
        console.error('Search error:', err);
        hideLoading();
        elements.listContainer.innerHTML = '<div style="color:red;text-align:center;padding:20px">加载失败，请稍后重试</div>';
        hasMoreData = false;
    }
}

/**
 * 渲染论文卡片列表
 */
function renderPaperList(papersToRender = papers, isLastPage = false) {
    const fragment = document.createDocumentFragment();
    
    papersToRender.forEach(p => {
        const card = document.createElement('div');
        card.className = 'paper-card';
        card.dataset.id = p.id;
        
        // 根据是否已解析添加不同的样式标识
        const parsedClass = p.isParsed ? 'parsed' : 'unparsed';
        const sourceTag = p.source ? `<span class="source-tag source-${p.source}">${getSourceName(p.source)}</span>` : '';
        
        card.innerHTML = `
            <div class="paper-title">${p.title}</div>
            <div class="paper-meta">
                <span class="authors">${p.authors}</span>
                <span class="year">${p.year}</span>
                ${sourceTag}
            </div>
            <div class="paper-abstract markdown-content">
                ${p.abstract} 
            </div>
            <div class="paper-actions">
                ${p.isParsed ? 
                    `<button class="paper-action-btn primary" onclick="window.startChatAboutPaper('${p.id}')">问一问</button>` :
                    `<button class="paper-action-btn disabled" disabled>未解析</button>`
                }
            </div>
        `;
        
        card.classList.add(parsedClass);
        fragment.appendChild(card);
    });
    
    if (papersToRender === papers) {
        // 首次渲染或搜索结果，替换全部内容
        elements.listContainer.innerHTML = '';
        elements.listContainer.appendChild(fragment);
    } else {
        // 追加加载
        elements.listContainer.appendChild(fragment);
    }

    // 绑定卡片交互事件
    const cards = elements.listContainer.querySelectorAll('.paper-card:not(.events-bound)');
    cards.forEach(card => {
        // 鼠标悬浮 Tooltip 逻辑
        bindTooltipEvents(card);
        card.classList.add('events-bound'); // 标记已绑定事件，避免重复绑定
    });
}

/**
 * 获取来源名称
 */
function getSourceName(source) {
    const sourceNames = {
        'arxiv': 'arXiv',
        'cvpr': 'CVPR',
        'neurips': 'NeurIPS',
        'iclr': 'ICLR',
        'survey': '综述',
        'book': '书籍',
        'local': '本地'
    };
    return sourceNames[source] || source;
}

/**
 * 绑定 Tooltip 逻辑 (包含节流优化)
 */
function bindTooltipEvents(cardElement) {
    const paperId = cardElement.dataset.id;
    const paper = papers.find(p => p.id === paperId);

    if (!paper) return;

    // 鼠标进入：显示 Tooltip
    cardElement.addEventListener('mouseenter', (e) => {
        // 使用缓存避免重复 Markdown 解析
        if (!tooltipCache.has(paperId)) {
            // 假设 marked 已全局加载
            const html = (typeof marked !== 'undefined') 
                ? marked.parse(paper.abstract.slice(0, 300) + '...') 
                : paper.abstract;
            tooltipCache.set(paperId, html);
        }

        elements.tooltip.innerHTML = tooltipCache.get(paperId);
        elements.tooltip.style.display = 'block';
        updateTooltipPosition(e);
    });

    // 鼠标移动：跟随 (使用节流)
    const throttledMove = throttle((e) => {
        updateTooltipPosition(e);
    }, 20); // 50fps

    cardElement.addEventListener('mousemove', throttledMove);

    // 鼠标离开：隐藏
    cardElement.addEventListener('mouseleave', () => {
        elements.tooltip.style.display = 'none';
    });
}

/**
 * 计算 Tooltip 位置，防止溢出屏幕
 */
function updateTooltipPosition(e) {
    const tooltipRect = elements.tooltip.getBoundingClientRect();
    const padding = 15;
    
    let left = e.clientX + padding;
    let top = e.clientY + padding;

    // 边界检测
    if (left + tooltipRect.width > window.innerWidth) {
        left = e.clientX - tooltipRect.width - padding;
    }
    if (top + tooltipRect.height > window.innerHeight) {
        top = e.clientY - tooltipRect.height - padding;
    }

    elements.tooltip.style.left = Math.max(0, left) + 'px';
    elements.tooltip.style.top = Math.max(0, top) + 'px';
}

// 全局函数：切换摘要显示
window.toggleAbstract = function(paperId) {
    const card = document.querySelector(`.paper-card[data-id="${paperId}"]`);
    if (!card) return;
    
    const abs = card.querySelector('.paper-abstract');
    if(abs.style.display === 'none') {
        abs.style.display = 'block';
        card.classList.add('expanded');
    } else {
        abs.style.display = 'none';
        card.classList.remove('expanded');
    }
};

// 全局函数：开始关于论文的对话
window.startChatAboutPaper = function(paperId) {
    const paper = papers.find(p => p.id === paperId);
    if (!paper) return;
    
    // 同步开关状态到对话页面
    const switchesMain = {
        net: document.getElementById('switchNetMain'),
        kb: document.getElementById('switchKbMain'),
        deep: document.getElementById('switchDeepMain')
    };
    
    const switches = {
        net: document.getElementById('switchNet'),
        kb: document.getElementById('switchKb'),
        deep: document.getElementById('switchDeep')
    };
    
    switches.net.checked = switchesMain.net.checked;
    switches.kb.checked = switchesMain.kb.checked;
    switches.deep.checked = switchesMain.deep.checked;
    
    // 切换到对话视图
    showChatView();
    
    // 在输入框中预设问题
    const chatInput = document.getElementById('chatInput');
    chatInput.value = `请介绍一下这篇论文：《${paper.title}》`;
    
    // 聚焦输入框
    chatInput.focus();
};
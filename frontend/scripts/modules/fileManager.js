import { api } from '../services/api.js';
import { openPDF } from './pdfViewer.js'; // 跨模块调用
import { findNodeById, removeNodeById } from '../utils/helpers.js';

// 模块内部状态
let nodes = [];
let selectedNode = null;

// DOM 元素缓存
const elements = {
    tree: document.getElementById('fileTree'),
    addFolderBtn: document.getElementById('addFolderBtn'),
    deleteBtn: document.getElementById('deleteBtn'),
    uploadBtn: document.getElementById('uploadBtn'),
    fileInput: document.getElementById('fileInput'),
    uploadArea: document.getElementById('uploadArea')
};

/**
 * 模块初始化函数
 */
export function initFileManager() {
    console.log('Initializing File Manager...');
    
    // 1. 初始加载文件树
    renderTree();

    // 2. 绑定按钮事件
    elements.addFolderBtn.addEventListener('click', handleCreateFolder);
    elements.deleteBtn.addEventListener('click', handleDeleteNode);
    
    // 3. 绑定上传事件
    elements.uploadBtn.addEventListener('click', () => elements.fileInput.click());
    elements.fileInput.addEventListener('change', () => handleFiles(elements.fileInput.files));
    
    // 4. 绑定拖拽上传事件
    elements.uploadArea.addEventListener('dragover', e => { 
        e.preventDefault(); 
        elements.uploadArea.classList.add('dragover'); 
    });
    elements.uploadArea.addEventListener('dragleave', () => {
        elements.uploadArea.classList.remove('dragover');
    });
    elements.uploadArea.addEventListener('drop', e => {
        e.preventDefault();
        elements.uploadArea.classList.remove('dragover');
        handleFiles(e.dataTransfer.files);
    });
}

/**
 * 从后端获取数据并渲染树
 */
async function renderTree() {
    try {
        const res = await api.getFileList();
        if (res && res.data) {
            nodes = res.data; // 更新本地状态
            elements.tree.innerHTML = ''; // 清空容器
            // 开始递归渲染
            walkAndRender(nodes, 0, elements.tree);
        }
    } catch (err) {
        console.error('加载文件树失败:', err);
        alert('文件列表加载失败，请检查网络');
    }
}

/**
 * 递归渲染 DOM
 */
function walkAndRender(nodeList, depth, container) {
    nodeList.forEach(node => {
        const div = document.createElement('div');
        div.className = 'file-item ' + (node.type === 'folder' ? 'folder' : 'file');
        div.dataset.id = node.id;
        div.style.paddingLeft = (14 + depth * 18) + 'px';
        
        div.innerHTML = `
            ${node.type === 'folder' ? '<span class="arrow"></span>' : '<span style="width:10px"></span>'}
            <span class="icon">${node.type === 'folder' ? '📁' : '📄'}</span>
            <span class="name">${node.name}</span>
        `;

        // 点击选中事件
        div.addEventListener('click', (e) => {
            e.stopPropagation();
            selectNode(node, div);
        });

        // 双击打开文件（仅限 PDF）
        if (node.type === 'file' && node.name.toLowerCase().endsWith('.pdf')) {
            div.addEventListener('dblclick', (e) => {
                e.stopPropagation();
                openPDF(node.id, node.name);
            });
            div.title = '双击打开 PDF 文件';
        }

        container.appendChild(div);

        // 如果有子节点，递归渲染
        if (node.children && node.children.length > 0) {
            walkAndRender(node.children, depth + 1, container);
        }
    });
}

/**
 * 处理节点选中逻辑
 */
function selectNode(node, domElement) {
    selectedNode = node;
    
    // 更新 UI 样式
    const allItems = elements.tree.querySelectorAll('.file-item');
    allItems.forEach(el => el.classList.remove('selected'));
    
    // 这里的 domElement 可能是重新渲染前的，所以最好用 selector 再找一次确保万无一失
    // 但如果在 render 周期内直接传引用也是可以的
    if(domElement) {
        domElement.classList.add('selected');
    } else {
        const target = elements.tree.querySelector(`[data-id="${node.id}"]`);
        if(target) target.classList.add('selected');
    }

    console.log(`选中: ${node.name} (${node.id})`);
}

/**
 * 创建文件夹
 */
async function handleCreateFolder() {
    if (!selectedNode) {
        return alert('❌ 请先点击选择一个文件夹或文件（将在其父级或自身下创建）');
    }

    // 如果选中的是文件，这就涉及到业务逻辑：是平级创建还是报错？
    // 这里沿用原逻辑：只允许在文件夹下创建
    if (selectedNode.type !== 'folder') {
        return alert('❌ 只能在文件夹下创建子文件夹，请重新选择一个文件夹');
    }

    const folderName = prompt('请输入新文件夹名称：');
    if (!folderName || !folderName.trim()) return;

    try {
        const res = await api.createFolder(selectedNode.id, folderName.trim());
        if (res.status === 'success') {
            console.log('文件夹创建成功');
            await renderTree(); // 重新拉取最新数据渲染
        } else {
            alert(`创建失败: ${res.message}`);
        }
    } catch (err) {
        console.error(err);
        alert('网络错误');
    }
}

/**
 * 删除节点
 */
async function handleDeleteNode() {
    if (!selectedNode) return alert('请先选择要删除的文件或文件夹');
    
    if (!confirm(`确定删除 "${selectedNode.name}" 吗？此操作不可撤销！`)) return;

    try {
        const res = await api.deleteNode(selectedNode.id);
        if (res.status === 'success') {
            // 乐观更新：也可以直接从本地 nodes 移除然后重绘，减少一次请求
            // 这里为了数据一致性，重新拉取
            await renderTree();
            selectedNode = null;
        } else {
            alert(`删除失败: ${res.message}`);
        }
    } catch (err) {
        console.error(err);
        alert('删除请求失败');
    }
}

/**
 * 处理文件上传
 */
async function handleFiles(files) {
    if (!files || files.length === 0) return;

    // 默认上传到根目录，或者当前选中的文件夹
    let targetNode = selectedNode;
    
    // 如果没选中，或者选中了文件，找根目录或者报错
    // 这里简单处理：如果没有选中文件夹，则默认传到列表第一个节点所在的目录(通常是根)
    if (!targetNode || targetNode.type !== 'folder') {
        if (nodes.length > 0 && nodes[0].type === 'folder') {
            targetNode = nodes[0]; // Fallback 到根目录
        } else {
            return alert('❌ 请先选择一个目标文件夹');
        }
    }

    console.log(`开始上传 ${files.length} 个文件到 ${targetNode.name}...`);

    // 并行上传
    const promises = [...files].map(file => 
        api.uploadFile(targetNode.path, file)
            .then(res => {
                if (res.status === 'success') return res.data;
                throw new Error(res.message);
            })
            .catch(err => {
                console.error(`文件 ${file.name} 上传失败:`, err);
                alert(`文件 ${file.name} 上传失败`);
                return null;
            })
    );

    await Promise.all(promises);
    
    // 刷新视图
    await renderTree();
    // 可以在这里做一些 input cleanup
    elements.fileInput.value = '';
}
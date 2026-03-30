const BASE_URL = 'api'; // 可以改为配置项

const headers = (skipContentType = false) => {
    const baseHeaders = {
        'Authorization': `Bearer ${localStorage.getItem('token') || ''}`
    };
    
    if (!skipContentType) {
        baseHeaders['Content-Type'] = 'application/json';
    }
    
    return baseHeaders;
};

export const api = {
    // 文件相关
    getFileList: async () => {
        const res = await fetch(`${BASE_URL}/file/list`, { headers: headers() });
        return res.json();
    },
    createFolder: async (parentID, folderName) => {
        return fetch(`${BASE_URL}/folder`, {
            method: 'POST',
            headers: headers(),
            body: JSON.stringify({ parentID, folderName })
        }).then(r => r.json());
    },
    deleteNode: async (id) => {
        return fetch(`${BASE_URL}/file`, {
            method: 'DELETE',
            headers: { ...headers(), 'Content-Type': 'application/json' },
            body: JSON.stringify({ id })
        }).then(r => r.json());
    },
    uploadFile: async (targetPath, file) => {
        const formData = new FormData();
        formData.append('targetPath', targetPath);
        formData.append('file', file);
        return fetch(`${BASE_URL}/file/upload`, {
            method: 'POST',
            headers: headers(), // 让浏览器自动设置 Content-Type boundary
            body: formData
        }).then(r => r.json());
    },

    // 知识库相关
    listKnowledgeBases: async () => {
        const res = await fetch(`${BASE_URL}/knowledge/bases`, { headers: headers() });
        return res.json();
    },
    createKnowledgeBase: async (name, description = '') => {
        return fetch(`${BASE_URL}/knowledge/base`, {
            method: 'POST',
            headers: { ...headers(), 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, description })
        }).then(r => r.json());
    },
    getKnowledgeBaseDetail: async (kbId) => {
        const res = await fetch(`${BASE_URL}/knowledge/base/${kbId}`, { headers: headers() });
        return res.json();
    },
    getKnowledgeBaseFiles: async (kbId) => {
        const res = await fetch(`${BASE_URL}/knowledge/base/${kbId}/files`, { headers: headers() });
        return res.json();
    },
    uploadFileToKnowledgeBase: async (kbId, file) => {
        const formData = new FormData();
        formData.append('file', file);
        return fetch(`${BASE_URL}/knowledge/base/${kbId}/upload`, {
            method: 'POST',
            headers: headers(true), // 不设置Content-Type，让FormData自动处理
            body: formData
        }).then(r => r.json());
    },
    deleteKnowledgeBase: async (kbId) => {
        return fetch(`${BASE_URL}/knowledge/base/${kbId}`, {
            method: 'DELETE',
            headers: headers()
        }).then(r => r.json());
    },
    deleteFileFromKnowledgeBase: async (kbId, fileId) => {
        return fetch(`${BASE_URL}/knowledge/base/${kbId}/files/${fileId}`, {
            method: 'DELETE',
            headers: headers()
        }).then(r => r.json());
    },
    getKbConversationHistory: async (kbId) => {
        const res = await fetch(`${BASE_URL}/knowledge/base/${kbId}/conversation/history`, { headers: headers() });
        return res.json();
    },
    clearKbConversation: async (kbId) => {
        return fetch(`${BASE_URL}/knowledge/base/${kbId}/conversation`, {
            method: 'DELETE',
            headers: headers()
        }).then(r => r.json());
    },
    getFileConversationHistory: async (kbId, fileId) => {
        const res = await fetch(`${BASE_URL}/knowledge/base/${kbId}/files/${fileId}/conversation/history`, { headers: headers() });
        return res.json();
    },
    clearFileConversation: async (kbId, fileId) => {
        return fetch(`${BASE_URL}/knowledge/base/${kbId}/files/${fileId}/conversation`, {
            method: 'DELETE',
            headers: headers()
        }).then(r => r.json());
    },
    // 生成AI-PPT
    generateAiPpt: async (kbId, fileIds, styleRequirement) => {
        return fetch(`${BASE_URL}/knowledge/base/${kbId}/generate`, {
            method: 'POST',
            headers: headers(),
            body: JSON.stringify({
                query: styleRequirement,
                kb_id: kbId,
                file_ids: fileIds,
                generation_type: 'ppt'
            })
        }).then(r => r.json());
    },

    // 获取任务列表
    getTaskList: async (kbId, status = null) => {
        const url = status
            ? `${BASE_URL}/knowledge/base/${kbId}/tasks?status=${status}`
            : `${BASE_URL}/knowledge/base/${kbId}/tasks`;
        const res = await fetch(url, { headers: headers() });
        return res.json();
    },

    // 获取任务详情
    getTaskDetail: async (taskId) => {
        const res = await fetch(`${BASE_URL}/knowledge/generation/${taskId}/detail`, { headers: headers() });
        return res.json();
    },

    // 删除任务
    deleteTask: async (taskId) => {
        return fetch(`${BASE_URL}/knowledge/generation/${taskId}`, {
            method: 'DELETE',
            headers: headers()
        }).then(r => r.json());
    },

    // 下载任务结果
    downloadTaskResult: async (taskId) => {
        const res = await fetch(`${BASE_URL}/knowledge/generation/${taskId}/download`, { headers: headers() });
        return res.blob();
    },

    // 论文会话相关
    startPaperChat: async (paperId, paperName) => {
        return fetch(`/paper/conversation/start`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ paper_id: paperId, paper_name: paperName })
        }).then(r => r.json());
    },
    endPaperChat: async (paperId) => {
        return fetch(`/paper/conversation/end`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ paper_id: paperId })
        });
    },

    // 搜索
    searchPapers: async (keywords) => {
        return fetch(`${BASE_URL}/search`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ keywords })
        }).then(r => r.json());
    }
};
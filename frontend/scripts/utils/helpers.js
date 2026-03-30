// 生成唯一ID
export const uid = () => 'id_' + Date.now() + Math.random().toString(36).slice(2, 8);

// HTML 转义
export function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 节流函数
export function throttle(func, delay) {
    let timeoutId;
    let lastExecTime = 0;
    return function (...args) {
        const currentTime = Date.now();
        if (currentTime - lastExecTime > delay) {
            func.apply(this, args);
            lastExecTime = currentTime;
        } else {
            clearTimeout(timeoutId);
            timeoutId = setTimeout(() => {
                func.apply(this, args);
                lastExecTime = Date.now();
            }, delay - (currentTime - lastExecTime));
        }
    };
}

// 树结构查找工具
export const findNodeById = (id, arr) => {
    for (const n of arr) {
        if (n.id === id) return n;
        if (n.children) {
            const t = findNodeById(id, n.children);
            if (t) return t;
        }
    }
    return null;
};

// 树结构删除工具
export const removeNodeById = (id, arr) => {
    for (let i = 0; i < arr.length; i++) {
        if (arr[i].id === id) { arr.splice(i, 1); return true; }
        if (arr[i].children && removeNodeById(id, arr[i].children)) return true;
    }
    return false;
};
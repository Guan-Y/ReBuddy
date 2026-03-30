export class StreamingMarkdownRenderer {
    constructor() {
        this.buffer = ''; 
        // 假设 marked 和 Prism 已通过 CDN 在全局引入
        this.hasMarked = typeof marked !== 'undefined';

        if (this.hasMarked) {
            marked.setOptions({
                breaks: true,
                gfm: true,
                highlight: (code, lang) => {
                    if (typeof Prism !== 'undefined') {
                        const langMap = { 'js': 'javascript', 'py': 'python', 'c++': 'cpp', 'ts': 'typescript' };
                        const finalLang = langMap[lang] || lang;
                        if (Prism.languages[finalLang]) {
                            try {
                                return Prism.highlight(code, Prism.languages[finalLang], finalLang);
                            } catch (e) { return code; }
                        }
                    }
                    return code;
                }
            });
        }
    }

    processChunk(chunk) {
        this.buffer += (chunk || '');
        return this._renderSafely();
    }

    _renderSafely() {
        if (!this.hasMarked) return `<pre>${this.buffer}</pre>`;
        let textToRender = this.buffer;
        // 补全代码块
        const codeBlockMarkers = (textToRender.match(/```/g) || []).length;
        if (codeBlockMarkers % 2 !== 0) {
            textToRender += '\n```';
        }
        try {
            return marked.parse(textToRender);
        } catch (e) {
            console.error("Markdown 解析错误:", e);
            return textToRender;
        }
    }
}
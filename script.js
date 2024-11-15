// 配置
const CONFIG = Object.freeze({
    SERVER_URL: 'https://47.113.226.71',
    TOKEN_KEY: 'WEIBO_TOKEN',
    REDIRECT_PATH: '/WeiboLuckyDrawTool/'
});

// State 管理
const state = {
    loading: false,
    error: null,
    users: [],
    setLoading(value) {
        this.loading = value;
        this.render();
    },
    setError(error) {
        this.error = error;
        this.render();
    },
    setUsers(users) {
        this.users = users;
        this.render();
    },
    render() {
        const resultDiv = document.getElementById('result');
        if (!resultDiv) return;

        if (this.loading) {
            resultDiv.innerHTML = '<div>正在加载...</div>';
            return;
        }

        if (this.error) {
            resultDiv.innerHTML = `<div class="error">错误: ${this.error}</div>`;
            return;
        }

        if (this.users.length > 0) {
            resultDiv.innerHTML = `
                <h3>抽奖结果:</h3>
                <ul>
                    ${this.users.map(user => `<li>${user}</li>`).join('')}
                </ul>
            `;
        }
    }
};

// Token 管理
const tokenManager = {
    save(tokenData) {
        try {
            localStorage.setItem(CONFIG.TOKEN_KEY, JSON.stringify(tokenData));
        } catch (error) {
            console.error('Token save error:', error);
        }
    },

    load() {
        try {
            const data = localStorage.getItem(CONFIG.TOKEN_KEY);
            return data ? JSON.parse(data) : null;
        } catch {
            return null;
        }
    },

    isExpired(tokenData) {
        if (!tokenData?.expires) return true;
        return Math.floor(Date.now() / 1000) > tokenData.expires;
    },

    clear() {
        localStorage.removeItem(CONFIG.TOKEN_KEY);
    }
};

// API 请求
const api = {
    async getAuthUrl() {
        const response = await fetch(`${CONFIG.SERVER_URL}/get_auth_url`);
        const data = await response.json();
        if (!data.auth_url) throw new Error('获取授权地址失败');
        return data.auth_url;
    },

    async processAuthCode(code) {
        const response = await fetch(`${CONFIG.SERVER_URL}/process_auth_code`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ code })
        });
        return response.json();
    },

    async fetchReposts(weiboUrl, userCount) {
        const response = await fetch(
            `${CONFIG.SERVER_URL}/fetch_reposts?weibo_url=${encodeURIComponent(weiboUrl)}&count=${userCount}`
        );
        return response.json();
    }
};

// 主程序
class App {
    constructor() {
        this.initialized = false;
    }

    async init() {
        if (this.initialized) return;
        this.initialized = true;

        // 绑定事件处理器
        const fetchButton = document.getElementById('fetchButton');
        if (fetchButton) {
            fetchButton.addEventListener('click', () => this.handleFetchClick());
        }

        // 检查URL中是否有授权码
        const params = new URLSearchParams(window.location.search);
        const code = params.get('code');

        if (code) {
            try {
                state.setLoading(true);
                const tokenData = await api.processAuthCode(code);

                if (tokenData.access_token) {
                    tokenManager.save(tokenData);
                    window.history.replaceState({}, document.title, CONFIG.REDIRECT_PATH);
                } else {
                    throw new Error('授权失败');
                }
            } catch (error) {
                state.setError(error.message);
            } finally {
                state.setLoading(false);
            }
            return;
        }

        // 检查现有token
        const token = tokenManager.load();
        if (!token || tokenManager.isExpired(token)) {
            try {
                const authUrl = await api.getAuthUrl();
                window.location.href = authUrl;
            } catch (error) {
                state.setError('获取授权失败');
            }
        }
    }

    async handleFetchClick() {
        const weiboUrl = document.getElementById('weiboUrl')?.value;
        const userCount = document.getElementById('userCount')?.value;

        if (!weiboUrl || !userCount) {
            state.setError('请填写完整信息');
            return;
        }

        try {
            state.setLoading(true);
            state.setError(null);

            const tokenData = tokenManager.load();
            if (!tokenData || tokenManager.isExpired(tokenData)) {
                await this.init(); // 重新初始化以获取新token
                return;
            }

            const data = await api.fetchReposts(weiboUrl, userCount);
            if (data.error) {
                throw new Error(data.error);
            }

            state.setUsers(data.users || []);
        } catch (error) {
            state.setError(error.message);
        } finally {
            state.setLoading(false);
        }
    }
}

// 初始化应用
const app = new App();
document.addEventListener('DOMContentLoaded', () => app.init());
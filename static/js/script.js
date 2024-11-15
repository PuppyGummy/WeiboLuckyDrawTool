// 配置
const config = {
    serverUrl: "https://47.113.226.71",
    tokenKey: 'WEIBO_TOKEN',
    redirectPath: "/WeiboLuckyDrawTool/"  // GitHub Pages 项目路径
};

// 工具函数
const utils = {
    // 显示错误信息
    showError(message) {
        const resultDiv = document.getElementById('result');
        resultDiv.innerHTML = `<div class="error">错误: ${message}</div>`;
    },

    // 显示加载状态
    showLoading() {
        const resultDiv = document.getElementById('result');
        resultDiv.innerHTML = '<div>正在加载...</div>';
    },

    // 显示结果
    showResults(users) {
        const resultDiv = document.getElementById('result');
        resultDiv.innerHTML = `
            <h3>抽奖结果:</h3>
            <ul>
                ${users.map(user => `<li>${user}</li>`).join('')}
            </ul>
        `;
    }
};

// Token 管理
const tokenManager = {
    save(tokenData) {
        try {
            localStorage.setItem(config.tokenKey, JSON.stringify(tokenData));
            console.log('Token saved successfully');
        } catch (error) {
            console.error('Error saving token:', error);
        }
    },

    load() {
        try {
            const tokenString = localStorage.getItem(config.tokenKey);
            return tokenString ? JSON.parse(tokenString) : null;
        } catch (error) {
            console.error('Error loading token:', error);
            return null;
        }
    },

    isExpired(tokenData) {
        if (!tokenData?.expires) return true;
        return Math.floor(Date.now() / 1000) > tokenData.expires;
    }
};

// API 请求处理
const api = {
    async getAuthUrl() {
        try {
            const response = await fetch(`${config.serverUrl}/get_auth_url`);
            const data = await response.json();
            return data.auth_url;
        } catch (error) {
            console.error('Error getting auth URL:', error);
            throw new Error('获取授权地址失败');
        }
    },

    async processAuthCode(code) {
        try {
            const response = await fetch(`${config.serverUrl}/process_auth_code`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ code })
            });
            return await response.json();
        } catch (error) {
            console.error('Error processing auth code:', error);
            throw new Error('处理授权码失败');
        }
    },

    async fetchReposts(weiboUrl, userCount) {
        try {
            const response = await fetch(
                `${config.serverUrl}/fetch_reposts?weibo_url=${encodeURIComponent(weiboUrl)}&count=${userCount}`,
                { method: 'GET' }
            );
            return await response.json();
        } catch (error) {
            console.error('Error fetching reposts:', error);
            throw new Error('获取转发列表失败');
        }
    }
};

// 主要业务逻辑
const app = {
    async init() {
        await this.checkAndHandleToken();
        this.setupEventListeners();
        this.handleAuthCallback();
    },

    async checkAndHandleToken() {
        const tokenData = tokenManager.load();
        if (!tokenData || tokenManager.isExpired(tokenData)) {
            const authUrl = await api.getAuthUrl();
            if (authUrl) {
                window.location.href = authUrl;
            }
        }
    },

    setupEventListeners() {
        const fetchButton = document.getElementById('fetchButton');
        if (fetchButton) {
            fetchButton.addEventListener('click', () => this.handleFetchReposts());
        }
    },

    async handleAuthCallback() {
        const urlParams = new URLSearchParams(window.location.search);
        const code = urlParams.get('code');
        if (code) {
            try {
                const tokenData = await api.processAuthCode(code);
                if (tokenData.access_token) {
                    tokenManager.save(tokenData);
                    // 清除 URL 中的授权码
                    window.history.replaceState({}, document.title, config.redirectPath);
                }
            } catch (error) {
                utils.showError('授权处理失败');
            }
        }
    },

    async handleFetchReposts() {
        const weiboUrl = document.getElementById('weiboUrl').value;
        const userCount = document.getElementById('userCount').value;

        if (!weiboUrl || !userCount) {
            utils.showError('请输入微博链接和抽取人数');
            return;
        }

        const tokenData = tokenManager.load();
        if (!tokenData || tokenManager.isExpired(tokenData)) {
            utils.showError('授权已过期，请重新授权');
            await this.checkAndHandleToken();
            return;
        }

        try {
            utils.showLoading();
            const data = await api.fetchReposts(weiboUrl, userCount);

            if (data.error) {
                utils.showError(data.error);
                return;
            }

            utils.showResults(data.users);
        } catch (error) {
            utils.showError(error.message);
        }
    }
};

// 初始化应用
document.addEventListener('DOMContentLoaded', () => app.init());
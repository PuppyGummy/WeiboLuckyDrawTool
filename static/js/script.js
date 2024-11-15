const serverUrl = "https://47.113.226.71";

// 保存令牌到localStorage
function saveTokenToLocalStorage(tokenData) {
    try {
        const tokenString = JSON.stringify(tokenData);
        localStorage.setItem('WEIBO_TOKEN', tokenString);
        console.log('Token saved successfully');
    } catch (error) {
        console.error('Error saving token to localStorage:', error);
    }
}

// 从localStorage加载令牌
function loadTokenFromLocalStorage() {
    try {
        const tokenString = localStorage.getItem('WEIBO_TOKEN');
        if (tokenString) {
            const tokenData = JSON.parse(tokenString);
            console.log('Token loaded successfully');
            return tokenData;
        }
        console.warn('No token found in localStorage');
        return null;
    } catch (error) {
        console.error('Error loading token from localStorage:', error);
        return null;
    }
}

// 检查令牌是否过期
function isTokenExpired(tokenData) {
    if (!tokenData || !tokenData.expires) {
        return true;
    }
    const currentTime = Math.floor(Date.now() / 1000);
    const expirationTime = tokenData.expires;
    const isExpired = currentTime > expirationTime;
    console.log(`Token expiration check: Current time = ${currentTime}, Expiration time = ${expirationTime}, Is expired = ${isExpired}`);
    return isExpired;
}

// 检查并处理令牌
async function checkAndHandleToken() {
    const tokenData = loadTokenFromLocalStorage();
    if (!tokenData || isTokenExpired(tokenData)) {
        try {
            const response = await fetch(`${serverUrl}/get_auth_url`, {
                method: 'GET'
            });
            const data = await response.json();
            if (data.auth_url) {
                window.location.href = data.auth_url;
            } else {
                console.error('Error fetching auth URL:', data.error || 'Unknown error');
            }
        } catch (error) {
            console.error('Error fetching auth URL:', error);
        }
    } else {
        console.log('Token is valid');
    }
}

// 处理授权回调
async function handleAuthCallback() {
    const urlParams = new URLSearchParams(window.location.search);
    const code = urlParams.get('code');
    if (code) {
        try {
            const response = await fetch(`${serverUrl}/process_auth_code`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ code: code })
            });
            const tokenData = await response.json();
            if (tokenData.access_token) {
                saveTokenToLocalStorage(tokenData);
                console.log('Token received and saved');
                window.history.replaceState({}, document.title, "/WeiboLuckyDrawTool/");
            } else {
                console.error('Failed to receive token:', tokenData.error);
            }
        } catch (error) {
            console.error('Error processing auth code:', error);
        }
    }
}

// 获取转发列表
async function fetchReposts() {
    const weiboUrl = document.getElementById('weiboUrl').value;
    const userCount = document.getElementById('userCount').value;

    if (!weiboUrl || !userCount) {
        alert("Please provide both Weibo URL and number of users to select.");
        return;
    }

    const tokenData = loadTokenFromLocalStorage();
    if (!tokenData || isTokenExpired(tokenData)) {
        alert("Token is missing or expired. Please reauthorize.");
        return;
    }

    try {
        const response = await fetch(`${serverUrl}/fetch_reposts?weibo_url=${encodeURIComponent(weiboUrl)}&count=${userCount}`, {
            method: 'GET'
        });

        const data = await response.json();

        if (data.error) {
            alert("Error: " + data.error);
            return;
        }

        const userList = data.users;
        const resultDiv = document.getElementById('result');
        resultDiv.innerHTML = `<h3>Selected Users:</h3><ul>${userList.map(user => `<li>${user}</li>`).join('')}</ul>`;
    } catch (error) {
        console.error("Error fetching reposts:", error);
        alert("Error fetching reposts. Check the console for details.");
    }
}

// 页面加载完成后进行初始化
document.addEventListener('DOMContentLoaded', () => {
    // 检查并处理令牌
    checkAndHandleToken();

    // 处理授权回调
    handleAuthCallback();

    // 添加按钮点击事件监听器
    const fetchButton = document.getElementById('fetchButton');
    if (fetchButton) {
        fetchButton.addEventListener('click', fetchReposts);
    }
});
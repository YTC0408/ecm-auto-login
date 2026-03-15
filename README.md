# ECM Auto Login - 加密凭证管理与自动登录

安全凭证管理与自动登录 Skill。基于零信任架构，LLM 绝不接触明文密码。

## 功能特性

- 🔐 **安全加密存储**：AES-256-GCM + PBKDF2 密钥派生
- 🔑 **主密码管理**：存于 Windows Credential Manager / macOS Keychain
- 🤖 **自动登录**：浏览器自动填表、提交
- 🚫 **零信任架构**：加解密闭环完成，LLM 无法访问明文密码
- ⚠️ **2FA/Captcha 检测**：自动暂停等待人工处理

## 快速开始

### 1. 安装依赖

```bash
pip install keyring cryptography playwright playwright-stealth
playwright install chromium
```

### 2. 设置主密码

```python
from ecm_skill import ecm_set_master_password
ecm_set_master_password("你的主密码")
```

### 3. 添加凭证

```python
from ecm_skill import ecm_add_credential

ecm_add_credential(
    name="GitHub",
    url="https://github.com/login",
    username="your-email@example.com",
    password="your-password",
    notes="Main account"
)
```

### 4. 自动登录

```python
from ecm_skill import ecm_login

# headless=False 可见浏览器，headless=True 无头模式
result = ecm_login("GitHub", headless=False)
print(result)
```

## Tools 列表

| Tool | 说明 |
|------|------|
| `ecm_set_master_password` | 设置主密码 |
| `ecm_has_master_password` | 检查主密码是否已设置 |
| `ecm_add_credential` | 添加新凭证 |
| `ecm_list_credentials` | 列出所有凭证（脱敏） |
| `ecm_get_credential` | 根据名称查询凭证（脱敏） |
| `ecm_update_credential` | 更新凭证 |
| `ecm_delete_credential` | 删除凭证 |
| `ecm_login` | 自动登录 |

## 项目结构

```
ecm-auto-login/
├── SKILL.md                      # Skill 文档
├── ecm_skill.py                  # Skill 入口 / Tool 定义
├── phase0_security_base.py       # 加密核心（AES-256-GCM + PBKDF2）
├── phase1_credential_manager.py  # 凭证管理（增删改查）
└── phase2_auto_login.py         # 自动登录（Playwright）
```

## 调试方法

### 本地测试

```bash
# 测试主密码设置
python -c "from ecm_skill import ecm_set_master_password; print(ecm_set_master_password('test'))"

# 测试添加凭证
python -c "from ecm_skill import ecm_add_credential; print(ecm_add_credential('Test', 'https://test.com', 'user', 'pass'))"

# 测试登录（非无头模式）
python -c "from ecm_skill import ecm_login; import json; print(json.dumps(ecm_login('Test', headless=False), indent=2))"
```

### 查看日志

登录时会输出详细日志：
```
=== Auto-Login: GitHub ===

[*] Found credential for: GitHub
    URL: https://github.com/login
    Username: ytch2004@qq.com
    [OK] Password decrypted internally
[OK] Stealth browser started
    [OK] Filled username: input[name="email"]
    [OK] Filled password: input[name="password"]
    [OK] Clicked submit: button[type="submit"]
[OK] Browser closed
```

### 常见问题

**Q: 登录失败提示 "verification"**
A: 网站检测到新设备/新浏览器，需要邮箱验证。这是正常的安全机制。

**Q: 提示 "module object is not callable"**
A: 确保 playwright-stealth 版本正确，或检查导入方式。最新版本需要用 `Stealth().apply_stealth_async(page)`。

**Q: 浏览器没有启动**
A: 确保已运行 `playwright install chromium`

## 安全说明

- 主密码不存储在磁盘，只存于系统凭据库
- 每次加密使用随机 salt
- 密码解密在 Skill 内部完成，LLM 只能调用高级接口，无法获取明文
- 建议定期更换主密码

## License

MIT

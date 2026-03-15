# SKILL.md - Encrypted Credential Manager & Auto Login

## 概述

安全凭证管理与自动登录 Skill。基于零信任架构，LLM 绝不接触明文密码。

## 核心原则

**零信任交互**：所有加解密操作在 Python 代码内部闭环完成，LLM 只能调用高级接口。

## Tools

### ecm_add_credential

添加新凭证。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 网站名称（如 "GitHub"） |
| url | string | 是 | 登录URL |
| username | string | 是 | 用户名/邮箱 |
| password | string | 是 | 明文密码（仅Skill内部使用，不暴露给LLM） |
| notes | string | 否 | 备注信息 |

返回：`{id, name, url, username, status}`

---

### ecm_list_credentials

列出所有凭证（脱敏，不含密码）。

返回：凭证列表 `[{id, name, url, username, notes}, ...]`

---

### ecm_get_credential

根据名称查询凭证（脱敏）。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 网站名称 |

返回：`{id, name, url, username, notes}`

---

### ecm_update_credential

更新凭证。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| entry_id | string | 是 | 凭证ID |
| name | string | 否 | 新名称 |
| url | string | 否 | 新URL |
| username | string | 否 | 新用户名 |
| password | string | 否 | 新密码（如提供会自动加密） |
| notes | string | 否 | 新备注 |

返回：`{id, name, url, username, status}`

---

### ecm_delete_credential

删除凭证。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| entry_id | string | 是 | 凭证ID |

返回：`{success: true/false}`

---

### ecm_login

自动登录到网站（闭环：解密 → 填充 → 提交）。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| site_name | string | 是 | 网站名称（需已添加凭证） |
| headless | boolean | 否 | 是否无头模式（默认 true） |

返回：
```json
{
  "success": true/false,
  "site": "GitHub",
  "message": "Login appears successful",
  "paused": true/false,
  "reason": "twofa"  // 如果 paused=true
}
```

**注意**：如果检测到 Captcha 或 2FA，会暂停并返回 `paused: true`，需人工接管。

---

### ecm_set_master_password

设置主密码（存储到 OS 凭据管理器）。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| password | string | 是 | 主密码 |

---

### ecm_has_master_password

检查主密码是否已设置。

返回：`{exists: true/false}`

## 安全机制

1. **主密码**：存于 Windows Credential Manager / macOS Keychain
2. **加密**：AES-256-GCM + PBKDF2 密钥派生
3. **脱敏查询**：列表/查询接口不返回明文密码
4. **闭环登录**：解密在 Skill 内部完成，LLM 无法访问明文

## 依赖

- Python 3.10+
- keyring
- cryptography
- playwright
- playwright-stealth

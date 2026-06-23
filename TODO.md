# TODO

## 待办

- [ ] **首页文案优化**：当前首页文案（副标题、说明文字、placeholder 等）风格不够理想。参考 sitor.cc 的首页文案结构和风格重新设计。涉及文件：`web/frontend/src/pages/LandingPage.tsx`

- [ ] **账号体系**：Google OAuth 2.0 登录 + JWT session + 4 档角色（user / pro / max / admin）。需先在 Google Cloud Console 创建 OAuth 应用，获取 Client ID 和 Client Secret。实现内容：`users` 表、`/api/auth/google/callback` 接口、JWT 中间件、对话数据绑定 user_id、各接口 auth 守卫。权益规则（各档对话次数、功能开关）待产品方案确定后补充。

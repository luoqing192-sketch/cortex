# Frontend Project

React 18 + TypeScript + Vite 项目

## 技术栈

- **框架**: React 18
- **构建工具**: Vite
- **语言**: TypeScript
- **UI 组件库**: Ant Design 5
- **状态管理**: Zustand
- **服务端状态**: @tanstack/react-query
- **路由**: react-router-dom v6
- **HTTP 客户端**: Axios
- **日期处理**: dayjs

## 项目结构

```
src/
├── components/     # 通用组件
├── pages/         # 页面组件
├── stores/        # Zustand stores
├── services/      # API 调用
├── types/         # TypeScript 类型定义
├── hooks/         # 自定义 hooks
├── utils/         # 工具函数
├── styles/        # 全局样式
├── App.tsx        # 应用根组件
└── main.tsx       # 入口文件
```

## 开发

```bash
# 安装依赖
npm install

# 启动开发服务器
npm run dev

# 构建生产版本
npm run build

# 预览生产版本
npm run preview

# 代码检查
npm run lint
```

## 配置说明

- **路径别名**: `@` 指向 `src` 目录
- **API 代理**: `/api` 自动代理到 `http://localhost:3000`
- **开发服务器**: 默认运行在 `http://localhost:5173`

## 已配置的工具

- ESLint + TypeScript ESLint
- Prettier
- TypeScript (strict mode)

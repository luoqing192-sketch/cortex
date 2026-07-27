import axios from 'axios';
import type {
  LoginResponse,
  User,
  Conversation,
  Message,
  LLMSettings,
  Prompt,
  WikiFile,
  QueueStatus,
} from '@/types';

const api = axios.create({
  baseURL: '/api',
  timeout: 30000,
});

// JWT interceptor
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// 401/403 认证失败处理：仅在 token 存在但被服务端拒绝时才登出
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status;
    const token = localStorage.getItem('token');

    // 只有当 token 存在且被服务端明确拒绝时才清除登录态
    // 401 = token 缺失, 403 = token 无效/过期
    if (token && (status === 401 || status === 403)) {
      // 排除登录接口本身的 401（密码错误）
      const isLoginRequest = error.config?.url?.includes('/auth/login');
      if (!isLoginRequest) {
        localStorage.removeItem('token');
        localStorage.removeItem('user');
        if (window.location.pathname !== '/login') {
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

// ==================== Auth ====================

export const authApi = {
  login: (username: string, password: string) =>
    api.post<LoginResponse>('/auth/login', { username, password }),

  me: () => api.get<User>('/auth/me'),
};

// ==================== Conversations ====================

export const conversationsApi = {
  list: () => api.get<Conversation[]>('/conversations'),

  create: (title?: string) =>
    api.post<Conversation>('/conversations', { title }),

  messages: (id: number) =>
    api.get<Message[]>(`/conversations/${id}/messages`),

  delete: (id: number) =>
    api.delete(`/conversations/${id}`),
};

// ==================== Chat ====================

export const chatApi = {
  uploadFile: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/chat/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },
};

// ==================== Queue ====================

export const queueApi = {
  status: () => api.get<QueueStatus>('/queue/status'),
};

// ==================== Admin: Users ====================

export const usersApi = {
  list: () => api.get<User[]>('/admin/users'),

  create: (username: string, password: string, role: string = 'user') =>
    api.post('/admin/users', { username, password, role }),

  resetPassword: (id: number, password: string) =>
    api.put(`/admin/users/${id}/password`, { password }),

  delete: (id: number) => api.delete(`/admin/users/${id}`),
};

// ==================== Admin: Settings ====================

export const settingsApi = {
  get: () => api.get<LLMSettings>('/admin/settings'),

  update: (settings: Partial<LLMSettings>) =>
    api.put('/admin/settings', settings),
};

// ==================== Admin: Prompts ====================

export const promptsApi = {
  list: () => api.get<Prompt[]>('/admin/prompts'),

  create: (data: Partial<Prompt>) =>
    api.post<Prompt>('/admin/prompts', data),

  update: (id: number, data: Partial<Prompt>) =>
    api.put<Prompt>(`/admin/prompts/${id}`, data),

  delete: (id: number) => api.delete(`/admin/prompts/${id}`),

  activate: (id: number) => api.post(`/admin/prompts/${id}/activate`),

  deactivate: (id: number) => api.post(`/admin/prompts/${id}/deactivate`),

  getActive: () => api.get<Prompt | null>('/admin/prompts/active'),
};

// ==================== Admin: Wiki Files ====================

export const wikiApi = {
  list: () => api.get<WikiFile[]>('/admin/wiki'),

  upload: (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post('/admin/wiki/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
  },

  delete: (filename: string) =>
    api.delete(`/admin/wiki/${encodeURIComponent(filename)}`),

  organize: (task?: string) =>
    api.post('/admin/wiki/organize', { task }, { timeout: 300000 }),
};

export default api;

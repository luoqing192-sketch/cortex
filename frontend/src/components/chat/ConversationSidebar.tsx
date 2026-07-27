import {
  PlusOutlined,
  DeleteOutlined,
  MessageOutlined,
  SettingOutlined,
  LogoutOutlined,
} from '@ant-design/icons';
import { Button, List, Typography, Space, Popconfirm, Tooltip } from 'antd';
import { useQueryClient } from '@tanstack/react-query';
import { useConversations, useCreateConversation, useDeleteConversation } from '@/hooks/useConversations';
import { useChatStore } from '@/stores/chatStore';
import { useAuthStore } from '@/stores/authStore';
import { useNavigate } from 'react-router-dom';
import dayjs from 'dayjs';

export default function ConversationSidebar() {
  const { data: conversations, isLoading } = useConversations();
  const createMutation = useCreateConversation();
  const deleteMutation = useDeleteConversation();
  const { currentConversationId, setCurrentConversation, reset: resetChat } = useChatStore();
  const { user, logout } = useAuthStore();
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const handleNewConversation = () => {
    createMutation.mutate(undefined);
  };

  const handleSelect = (id: number) => {
    setCurrentConversation(id);
  };

  const handleDelete = (id: number) => {
    deleteMutation.mutate(id);
  };

  const handleLogout = () => {
    resetChat();
    queryClient.clear();
    logout();
    navigate('/login');
  };

  return (
    <div style={{
      height: '100%',
      display: 'flex',
      flexDirection: 'column',
      background: 'linear-gradient(180deg, var(--sidebar-start) 0%, var(--sidebar-end) 100%)',
    }}>
      {/* Header */}
      <div style={{
        padding: '20px 16px 16px',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
      }}>
        <div style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 14,
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <div style={{
              width: 32,
              height: 32,
              borderRadius: 10,
              background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 16,
              color: '#fff',
              fontWeight: 700,
              flexShrink: 0,
            }}>
              A
            </div>
            <Typography.Title level={5} style={{ color: '#fff', margin: 0, fontSize: 15, fontWeight: 600, letterSpacing: '-0.01em' }}>
              AI 助手
            </Typography.Title>
          </div>
          <Space size={2}>
            {user?.role === 'admin' && (
              <Tooltip title="管理后台">
                <Button
                  type="text"
                  icon={<SettingOutlined />}
                  size="small"
                  style={{ color: 'rgba(255,255,255,0.5)' }}
                  onClick={() => navigate('/admin')}
                />
              </Tooltip>
            )}
            <Tooltip title="退出登录">
              <Button
                type="text"
                icon={<LogoutOutlined />}
                size="small"
                style={{ color: 'rgba(255,255,255,0.5)' }}
                onClick={handleLogout}
              />
            </Tooltip>
          </Space>
        </div>
        <Button
          icon={<PlusOutlined />}
          block
          onClick={handleNewConversation}
          loading={createMutation.isPending}
          style={{
            background: 'rgba(255,255,255,0.07)',
            border: '1px solid rgba(255,255,255,0.1)',
            color: 'rgba(255,255,255,0.8)',
            borderRadius: 10,
            height: 38,
            fontWeight: 500,
          }}
        >
          新对话
        </Button>
      </div>

      {/* Conversation List */}
      <div style={{ flex: 1, overflow: 'auto', padding: '8px 8px' }}>
        {isLoading ? (
          <Typography.Text style={{ color: 'rgba(255,255,255,0.35)', padding: 16, display: 'block' }}>
            加载中...
          </Typography.Text>
        ) : (
          <List
            dataSource={conversations || []}
            renderItem={(conv) => (
              <div
                key={conv.id}
                onClick={() => handleSelect(conv.id)}
                style={{
                  padding: '10px 12px',
                  marginBottom: 2,
                  borderRadius: 10,
                  cursor: 'pointer',
                  background: currentConversationId === conv.id
                    ? 'rgba(99, 102, 241, 0.15)'
                    : 'transparent',
                  transition: 'background 0.15s ease',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                }}
                onMouseEnter={(e) => {
                  if (currentConversationId !== conv.id) {
                    (e.currentTarget as HTMLElement).style.background = 'rgba(255,255,255,0.05)';
                  }
                }}
                onMouseLeave={(e) => {
                  if (currentConversationId !== conv.id) {
                    (e.currentTarget as HTMLElement).style.background = 'transparent';
                  }
                }}
              >
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{
                    color: currentConversationId === conv.id ? '#fff' : 'rgba(255,255,255,0.75)',
                    fontSize: 13,
                    fontWeight: currentConversationId === conv.id ? 500 : 400,
                    whiteSpace: 'nowrap',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    transition: 'color 0.15s ease',
                  }}>
                    <MessageOutlined style={{ marginRight: 8, opacity: 0.4, fontSize: 12 }} />
                    {conv.title}
                  </div>
                  <div style={{
                    color: 'rgba(255,255,255,0.25)',
                    fontSize: 11,
                    marginTop: 3,
                    paddingLeft: 20,
                  }}>
                    {dayjs(conv.updated_at).format('MM/DD HH:mm')}
                  </div>
                </div>
                <Popconfirm
                  title="确定删除此对话？"
                  onConfirm={(e) => {
                    e?.stopPropagation();
                    handleDelete(conv.id);
                  }}
                  onCancel={(e) => e?.stopPropagation()}
                  okText="删除"
                  cancelText="取消"
                >
                  <Button
                    type="text"
                    size="small"
                    icon={<DeleteOutlined />}
                    style={{ color: 'rgba(255,255,255,0.2)', flexShrink: 0 }}
                    onClick={(e) => e.stopPropagation()}
                  />
                </Popconfirm>
              </div>
            )}
          />
        )}
      </div>

      {/* User Info */}
      <div style={{
        padding: '12px 16px',
        borderTop: '1px solid rgba(255,255,255,0.06)',
        color: 'rgba(255,255,255,0.5)',
        fontSize: 12,
        letterSpacing: '0.01em',
      }}>
        {user?.username} · {user?.role === 'admin' ? '管理员' : '用户'}
      </div>
    </div>
  );
}

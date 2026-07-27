import { useEffect, useRef } from 'react';
import { Typography, Avatar, Spin, Alert } from 'antd';
import { RobotOutlined, UserOutlined, LoadingOutlined } from '@ant-design/icons';
import { useChatStore, defaultStreamState } from '@/stores/chatStore';
import { useConversationMessages } from '@/hooks/useConversations';
import CodePreview from './CodePreview';
import ToolProgress from './ToolProgress';
import Sources from './Sources';
import dayjs from 'dayjs';

export default function MessageList() {
  const currentConversationId = useChatStore((s) => s.currentConversationId);
  const ragNotice = useChatStore((s) => s.ragNotice);
  const streamState = useChatStore((s) =>
    s.currentConversationId
      ? (s.streamStates[s.currentConversationId] || defaultStreamState)
      : defaultStreamState
  );
  const { isStreaming, streamingContent, toolProgress, previewUrl, sources } = streamState;
  const { data: messages, isLoading } = useConversationMessages(currentConversationId);
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (listRef.current) {
      listRef.current.scrollTop = listRef.current.scrollHeight;
    }
  }, [messages, streamingContent]);

  if (!currentConversationId) {
    return (
      <div style={{
        flex: 1,
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        color: 'var(--text-muted)',
      }}>
        <div style={{ textAlign: 'center' }}>
          <div style={{
            width: 64,
            height: 64,
            borderRadius: 20,
            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 20px',
            opacity: 0.15,
          }}>
            <RobotOutlined style={{ fontSize: 28, color: '#fff' }} />
          </div>
          <div style={{ fontSize: 14, fontWeight: 500, color: 'var(--text-secondary)' }}>
            选择或创建一个对话开始聊天
          </div>
        </div>
      </div>
    );
  }

  if (isLoading) {
    return (
      <div style={{
        flex: 1,
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
      }}>
        <Spin size="large" />
      </div>
    );
  }

  return (
    <div
      ref={listRef}
      style={{
        flex: 1,
        overflow: 'auto',
        padding: '24px 32px',
      }}
    >
      {(messages || []).map((msg) => (
        <MessageBubble key={msg.id} role={msg.role} content={msg.content} time={msg.created_at} />
      ))}

      {isStreaming && ragNotice && (
        <Alert
          type="warning"
          showIcon
          message={ragNotice}
          style={{ margin: '0 0 12px 52px', maxWidth: '70%', borderRadius: 10 }}
        />
      )}

      {isStreaming && toolProgress && (
        <div style={{ marginLeft: 52 }}>
          <ToolProgress tool={toolProgress.tool} status={toolProgress.status} />
        </div>
      )}

      {isStreaming && (
        <MessageBubble
          role="assistant"
          content={streamingContent || ''}
          isStreaming={!streamingContent}
        />
      )}

      {sources && sources.length > 0 && (
        <div style={{ marginLeft: 52, maxWidth: '70%' }}>
          <Sources sources={sources} />
        </div>
      )}

      {previewUrl && (
        <div style={{ marginLeft: 52, maxWidth: '70%' }}>
          <CodePreview url={previewUrl} />
        </div>
      )}
    </div>
  );
}

function MessageBubble({
  role,
  content,
  time,
  isStreaming,
}: {
  role: string;
  content: string;
  time?: string;
  isStreaming?: boolean;
}) {
  const isUser = role === 'user';

  return (
    <div style={{
      display: 'flex',
      justifyContent: isUser ? 'flex-end' : 'flex-start',
      marginBottom: 20,
    }}>
      {!isUser && (
        <Avatar
          icon={<RobotOutlined />}
          size={36}
          style={{
            background: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
            marginRight: 12,
            flexShrink: 0,
          }}
        />
      )}

      <div style={{ maxWidth: '70%' }}>
        <div style={{
          padding: '12px 16px',
          borderRadius: isUser ? '18px 18px 4px 18px' : '18px 18px 18px 4px',
          background: isUser ? 'var(--user-bubble)' : 'var(--assistant-bubble)',
          color: isUser ? '#fff' : 'var(--text-primary)',
          lineHeight: 1.7,
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
          fontSize: 14,
          boxShadow: isUser ? 'none' : '0 1px 3px rgba(0, 0, 0, 0.06)',
          border: isUser ? 'none' : '1px solid var(--border)',
          transition: 'all 0.15s ease',
        }}>
          {isStreaming && !content ? (
            <LoadingOutlined style={{ color: 'var(--text-muted)', fontSize: 16 }} />
          ) : (
            content
          )}
        </div>
        {time && (
          <Typography.Text
            style={{
              fontSize: 11,
              color: 'var(--text-muted)',
              marginTop: 6,
              display: 'block',
              textAlign: isUser ? 'right' : 'left',
            }}
          >
            {dayjs(time).format('HH:mm')}
          </Typography.Text>
        )}
      </div>

      {isUser && (
        <Avatar
          icon={<UserOutlined />}
          size={36}
          style={{
            background: 'var(--primary)',
            marginLeft: 12,
            flexShrink: 0,
          }}
        />
      )}
    </div>
  );
}

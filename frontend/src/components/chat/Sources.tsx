import { Typography } from 'antd';
import { LinkOutlined, GlobalOutlined } from '@ant-design/icons';
import type { Source } from '@/types';

export default function Sources({ sources }: { sources: Source[] }) {
  if (!sources || sources.length === 0) return null;

  return (
    <div
      style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--border)',
        borderRadius: 12,
        padding: '12px 16px',
        marginBottom: 20,
      }}
    >
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 6,
          fontSize: 13,
          fontWeight: 600,
          color: 'var(--text-secondary)',
          marginBottom: 8,
        }}
      >
        <GlobalOutlined />
        参考来源（{sources.length}）
      </div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {sources.map((s, i) => (
          <a
            key={`${s.url}-${i}`}
            href={s.url}
            target="_blank"
            rel="noopener noreferrer"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 6,
              fontSize: 13,
              color: 'var(--primary)',
              textDecoration: 'none',
              overflow: 'hidden',
            }}
          >
            <LinkOutlined style={{ flexShrink: 0 }} />
            <Typography.Text
              ellipsis
              style={{ color: 'var(--primary)', maxWidth: '100%' }}
              title={s.title || s.url}
            >
              {i + 1}. {s.title || s.url}
            </Typography.Text>
          </a>
        ))}
      </div>
    </div>
  );
}

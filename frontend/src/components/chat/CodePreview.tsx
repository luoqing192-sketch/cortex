import React, { useMemo } from 'react';
import { Button } from 'antd';
import { ExpandOutlined, LinkOutlined } from '@ant-design/icons';

interface CodePreviewProps {
  url: string;
}

const CodePreview: React.FC<CodePreviewProps> = ({ url }) => {
  const fullUrl = useMemo(() => {
    if (/^https?:\/\//.test(url)) return url;
    return `${window.location.origin}${url.startsWith('/') ? '' : '/'}${url}`;
  }, [url]);

  return (
    <div style={{ marginTop: 12, border: '1px solid #e8e8e8', borderRadius: 8, overflow: 'hidden' }}>
      {/* Clickable preview link card */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        padding: '10px 14px', background: '#f0f7ff', borderBottom: '1px solid #d6e8fa',
      }}>
        <LinkOutlined style={{ fontSize: 16, color: '#1677ff' }} />
        <span style={{ fontSize: 13, color: '#555' }}>预览链接：</span>
        <a
          href={fullUrl}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            fontSize: 13, color: '#1677ff', textDecoration: 'underline',
            wordBreak: 'break-all', flex: 1,
          }}
        >
          {fullUrl}
        </a>
        <a
          href={fullUrl}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            fontSize: 13, color: '#1677ff', fontWeight: 500,
            whiteSpace: 'nowrap', textDecoration: 'none',
          }}
        >
          点击打开 ↗
        </a>
      </div>

      {/* Toolbar */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        padding: '8px 12px', background: '#fafafa', borderBottom: '1px solid #e8e8e8'
      }}>
        <span style={{ fontWeight: 500, fontSize: 13 }}>页面预览</span>
        <Button
          size="small"
          icon={<ExpandOutlined />}
          onClick={() => window.open(fullUrl, '_blank')}
        >
          新窗口打开
        </Button>
      </div>

      {/* Iframe preview */}
      <iframe
        src={url}
        sandbox="allow-scripts allow-same-origin"
        style={{ width: '100%', height: '400px', border: 'none' }}
        title="代码预览"
      />
    </div>
  );
};

export default CodePreview;

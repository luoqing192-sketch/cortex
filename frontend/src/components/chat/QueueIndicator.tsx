import { useEffect, useState } from 'react';
import { Tag } from 'antd';
import { LoadingOutlined, ClockCircleOutlined } from '@ant-design/icons';
import { queueApi } from '@/services/api';
import type { QueueStatus } from '@/types';

export default function QueueIndicator() {
  const [status, setStatus] = useState<QueueStatus | null>(null);

  useEffect(() => {
    const poll = async () => {
      try {
        const res = await queueApi.status();
        setStatus(res.data);
      } catch {
        // Ignore
      }
    };

    poll();
    const interval = setInterval(poll, 5000);
    return () => clearInterval(interval);
  }, []);

  if (!status || (status.pending === 0 && status.active === 0)) {
    return null;
  }

  return (
    <div style={{ padding: '4px 16px', textAlign: 'center' }}>
      {status.pending > 0 ? (
        <Tag icon={<ClockCircleOutlined />} color="warning">
          排队中: {status.pending} 个请求等待
        </Tag>
      ) : (
        <Tag icon={<LoadingOutlined spin />} color="processing">
          处理中: {status.active} 个请求
        </Tag>
      )}
    </div>
  );
}

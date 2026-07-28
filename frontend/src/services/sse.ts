import type { ChatStreamEvent, Source, Attachment } from '@/types';

export interface StreamCallbacks {
  onChunk: (content: string) => void;
  onDone: () => void;
  onError: (error: string) => void;
  onQueueStatus?: (pending: number, active: number) => void;
  onNotice?: (message: string) => void;
  onToolProgress?: (tool: string, status: string) => void;
  onPreview?: (url: string) => void;
  onSources?: (sources: Source[]) => void;
}

export async function streamChat(
  conversationId: number,
  message: string,
  callbacks: StreamCallbacks,
  attachments?: Attachment[]
): Promise<void> {
  const token = localStorage.getItem('token');

  const body: Record<string, unknown> = { conversationId, message };
  if (attachments && attachments.length > 0) {
    body.attachments = attachments;
  }

  const response = await fetch('/api/chat', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    callbacks.onError(`请求失败: ${response.status}`);
    return;
  }

  const reader = response.body?.getReader();
  if (!reader) {
    callbacks.onError('无法读取响应流');
    return;
  }

  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue;
        const data = line.slice(6).trim();

        if (data === '[DONE]') {
          callbacks.onDone();
          return;
        }

        try {
          const event: ChatStreamEvent = JSON.parse(data);

          if (event.type === 'queue' && callbacks.onQueueStatus) {
            callbacks.onQueueStatus(event.pending || 0, event.active || 0);
            continue;
          }

          if (event.type === 'notice' && callbacks.onNotice) {
            callbacks.onNotice(event.message || '');
            continue;
          }

          if (event.type === 'tool_progress') {
            callbacks.onToolProgress?.(event.tool || '', event.status || '');
            continue;
          }

          if (event.type === 'preview') {
            callbacks.onPreview?.(event.url || '');
            continue;
          }

          if (event.type === 'sources') {
            callbacks.onSources?.(event.sources || []);
            continue;
          }

          if (event.type === 'intent') {
            // 信息性事件，前端暂不展示
            continue;
          }

          if (event.error) {
            callbacks.onError(event.error);
            return;
          }

          if (event.content) {
            callbacks.onChunk(event.content);
          }
        } catch {
          // Skip invalid JSON
        }
      }
    }

    callbacks.onDone();
  } catch (error) {
    callbacks.onError(`流式传输中断: ${error instanceof Error ? error.message : '未知错误'}`);
  }
}

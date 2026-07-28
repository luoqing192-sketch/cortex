import { useState, useRef } from 'react';
import { Input, Button, Upload, message } from 'antd';
import { SendOutlined, PaperClipOutlined, PictureOutlined, CloseCircleFilled } from '@ant-design/icons';
import { useQueryClient } from '@tanstack/react-query';
import { useChatStore } from '@/stores/chatStore';
import { streamChat } from '@/services/sse';
import { chatApi } from '@/services/api';
import type { Attachment } from '@/types';

const { TextArea } = Input;

export default function MessageInput() {
  const [inputValue, setInputValue] = useState('');
  const [uploading, setUploading] = useState(false);
  const [pendingImages, setPendingImages] = useState<Attachment[]>([]);
  const queryClient = useQueryClient();
  const {
    currentConversationId,
    setIsStreaming,
    setStreamingContent,
    appendStreamingContent,
    finalizeStreaming,
    setQueueStatus,
    setRagNotice,
    setToolProgress,
    setPreviewUrl,
    setSources,
    clearCodeGenState,
  } = useChatStore();
  const textAreaRef = useRef<HTMLTextAreaElement>(null);

  const currentIsStreaming = useChatStore(
    (s) => s.currentConversationId ? (s.streamStates[s.currentConversationId]?.isStreaming ?? false) : false
  );

  // 上传单张图片 → 拿到引用（{type,url,name,mime,path}）
  const uploadImage = async (file: File): Promise<Attachment | null> => {
    try {
      const resp = await chatApi.uploadFile(file);
      const f = resp.data.file;
      if (!f?.is_image) {
        message.warning(`"${file.name}" 不是图片`);
        return null;
      }
      return { type: 'image', name: f.original_name, url: f.url, path: f.path, mime: f.mime };
    } catch {
      message.error(`图片 "${file.name}" 上传失败`);
      return null;
    }
  };

  const addImages = async (files: File[]) => {
    if (!currentConversationId) return;
    setUploading(true);
    try {
      for (const file of files) {
        if (file.size > 10 * 1024 * 1024) {
          message.warning(`"${file.name}" 超过 10MB`);
          continue;
        }
        const ref = await uploadImage(file);
        if (ref) setPendingImages((prev) => [...prev, ref]);
      }
    } finally {
      setUploading(false);
    }
  };

  const handleSend = async () => {
    const text = inputValue.trim();
    const convId = currentConversationId;
    if ((!text && pendingImages.length === 0) || !convId) return;
    if (useChatStore.getState().streamStates[convId]?.isStreaming) return;

    const attachments = pendingImages;
    setInputValue('');
    setPendingImages([]);

    const userMessage = {
      id: Date.now(),
      conversation_id: convId,
      role: 'user' as const,
      content: text,
      created_at: new Date().toISOString(),
      attachments,
    };
    queryClient.setQueryData(
      ['messages', convId],
      (old: any[] | undefined) => [...(old || []), userMessage]
    );

    setIsStreaming(convId, true);
    setStreamingContent(convId, '');
    setRagNotice(null);
    clearCodeGenState(convId);

    await streamChat(convId, text, {
      onChunk: (content) => appendStreamingContent(convId, content),
      onDone: () => {
        finalizeStreaming(convId);
        queryClient.invalidateQueries({ queryKey: ['messages', convId] });
        queryClient.invalidateQueries({ queryKey: ['conversations'] });
      },
      onError: (error) => {
        message.error(error);
        finalizeStreaming(convId);
        queryClient.invalidateQueries({ queryKey: ['messages', convId] });
      },
      onQueueStatus: (pending, active) => setQueueStatus(pending, active),
      onNotice: (notice) => {
        if (useChatStore.getState().currentConversationId === convId) {
          setRagNotice(notice);
        }
      },
      onToolProgress: (tool, status) => setToolProgress(convId, { tool, status }),
      onPreview: (url) => setPreviewUrl(convId, url),
      onSources: (sources) => setSources(convId, sources),
    }, attachments.length > 0 ? attachments : undefined);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // 粘贴板图片
  const handlePaste = (e: React.ClipboardEvent) => {
    const items = Array.from(e.clipboardData?.items || []);
    const files = items
      .filter((it) => it.type.startsWith('image/'))
      .map((it) => it.getAsFile())
      .filter((f): f is File => !!f);
    if (files.length > 0) {
      e.preventDefault();
      addImages(files);
    }
  };

  const handleImageUpload = (file: File) => {
    addImages([file]);
    return false;
  };

  const handleFileUpload = async (file: File) => {
    setUploading(true);
    try {
      await chatApi.uploadFile(file);
      message.success(`文件 "${file.name}" 上传成功`);
    } catch {
      message.error('文件上传失败');
    } finally {
      setUploading(false);
    }
    return false;
  };

  const removeImage = (idx: number) => {
    setPendingImages((prev) => prev.filter((_, i) => i !== idx));
  };

  const disabled = !currentConversationId || currentIsStreaming;

  return (
    <div style={{
      padding: '14px 32px 20px',
      background: 'var(--bg-card)',
      boxShadow: '0 -1px 4px rgba(0, 0, 0, 0.04)',
    }}>
      {/* 待发图片缩略图区 */}
      {pendingImages.length > 0 && (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 10 }}>
          {pendingImages.map((img, idx) => (
            <div key={idx} style={{ position: 'relative' }}>
              <img
                src={img.url}
                alt={img.name}
                style={{ width: 56, height: 56, objectFit: 'cover', borderRadius: 8, border: '1px solid var(--border)' }}
              />
              <CloseCircleFilled
                onClick={() => removeImage(idx)}
                style={{ position: 'absolute', top: -6, right: -6, color: '#ff4d4f', cursor: 'pointer', background: '#fff', borderRadius: '50%' }}
              />
            </div>
          ))}
        </div>
      )}

      <div style={{
        display: 'flex',
        gap: 10,
        alignItems: 'flex-end',
        background: 'var(--bg-main)',
        borderRadius: 14,
        padding: '8px 8px 8px 14px',
        border: '1px solid var(--border)',
        transition: 'border-color 0.2s ease',
      }}>
        <Upload beforeUpload={handleImageUpload} showUploadList={false} accept="image/*" multiple>
          <Button
            type="text"
            icon={<PictureOutlined />}
            loading={uploading}
            disabled={disabled}
            title="添加图片（也可直接粘贴）"
            style={{ color: 'var(--text-muted)', border: 'none' }}
          />
        </Upload>

        <Upload beforeUpload={handleFileUpload} showUploadList={false} accept=".txt,.pdf,.doc,.docx,.md,.csv">
          <Button
            type="text"
            icon={<PaperClipOutlined />}
            disabled={disabled}
            title="上传文件"
            style={{ color: 'var(--text-muted)', border: 'none' }}
          />
        </Upload>

        <TextArea
          ref={textAreaRef as any}
          value={inputValue}
          onChange={(e) => setInputValue(e.target.value)}
          onKeyDown={handleKeyDown}
          onPaste={handlePaste}
          placeholder={currentConversationId ? '输入消息，可粘贴图片... (Enter 发送)' : '请先选择一个对话'}
          disabled={disabled}
          autoSize={{ minRows: 1, maxRows: 6 }}
          style={{
            flex: 1,
            border: 'none',
            background: 'transparent',
            boxShadow: 'none',
            resize: 'none',
            padding: '4px 0',
            fontSize: 14,
          }}
          variant="borderless"
        />

        <Button
          type="primary"
          shape="circle"
          icon={<SendOutlined style={{ fontSize: 14 }} />}
          onClick={handleSend}
          loading={currentIsStreaming}
          disabled={disabled || (!inputValue.trim() && pendingImages.length === 0)}
          style={{ flexShrink: 0, width: 36, height: 36 }}
        />
      </div>
    </div>
  );
}

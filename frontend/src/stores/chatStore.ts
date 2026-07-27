import { create } from 'zustand';
import type { Message, Source } from '@/types';

export interface ConversationStreamState {
  isStreaming: boolean;
  streamingContent: string;
  toolProgress: { tool: string; status: string } | null;
  previewUrl: string | null;
  sources: Source[];
}

export const defaultStreamState: ConversationStreamState = {
  isStreaming: false,
  streamingContent: '',
  toolProgress: null,
  previewUrl: null,
  sources: [],
};

interface ChatState {
  currentConversationId: number | null;
  messages: Message[];
  ragNotice: string | null;
  queuePending: number;
  queueActive: number;

  // 按 conversationId 隔离的流式状态
  streamStates: Record<number, ConversationStreamState>;

  // 获取当前对话的流式状态（便捷方法）
  getCurrentStreamState: () => ConversationStreamState;

  setCurrentConversation: (id: number | null) => void;
  setMessages: (messages: Message[]) => void;
  addMessage: (message: Message) => void;

  // 所有流式操作都带 conversationId 参数
  setIsStreaming: (conversationId: number, streaming: boolean) => void;
  setStreamingContent: (conversationId: number, content: string) => void;
  appendStreamingContent: (conversationId: number, chunk: string) => void;
  setRagNotice: (notice: string | null) => void;
  finalizeStreaming: (conversationId: number) => void;
  setQueueStatus: (pending: number, active: number) => void;
  setToolProgress: (conversationId: number, progress: { tool: string; status: string } | null) => void;
  setPreviewUrl: (conversationId: number, url: string | null) => void;
  setSources: (conversationId: number, sources: Source[]) => void;
  clearCodeGenState: (conversationId: number) => void;
  reset: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  currentConversationId: null,
  messages: [],
  ragNotice: null,
  queuePending: 0,
  queueActive: 0,
  streamStates: {},

  getCurrentStreamState: () => {
    const { currentConversationId, streamStates } = get();
    if (!currentConversationId) return defaultStreamState;
    return streamStates[currentConversationId] || defaultStreamState;
  },

  setCurrentConversation: (id) =>
    set({ currentConversationId: id, messages: [] }),

  setMessages: (messages) => set({ messages }),

  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),

  setIsStreaming: (conversationId, streaming) => {
    set((state) => ({
      streamStates: {
        ...state.streamStates,
        [conversationId]: {
          ...(state.streamStates[conversationId] || defaultStreamState),
          isStreaming: streaming,
          ...(streaming ? { toolProgress: null } : {}),
        },
      },
    }));
  },

  setStreamingContent: (conversationId, content) => {
    set((state) => ({
      streamStates: {
        ...state.streamStates,
        [conversationId]: {
          ...(state.streamStates[conversationId] || defaultStreamState),
          streamingContent: content,
        },
      },
    }));
  },

  appendStreamingContent: (conversationId, chunk) => {
    set((state) => {
      const current = state.streamStates[conversationId] || defaultStreamState;
      return {
        streamStates: {
          ...state.streamStates,
          [conversationId]: {
            ...current,
            streamingContent: current.streamingContent + chunk,
          },
        },
      };
    });
  },

  setRagNotice: (notice) => set({ ragNotice: notice }),

  finalizeStreaming: (conversationId) => {
    const streamState = get().streamStates[conversationId] || defaultStreamState;

    if (streamState.streamingContent && conversationId) {
      const assistantMessage: Message = {
        id: Date.now(),
        conversation_id: conversationId,
        role: 'assistant',
        content: streamState.streamingContent,
        created_at: new Date().toISOString(),
      };

      set((state) => {
        const newStreamStates = { ...state.streamStates };
        newStreamStates[conversationId] = {
          ...(newStreamStates[conversationId] || defaultStreamState),
          streamingContent: '',
          isStreaming: false,
        };

        return {
          messages: conversationId === state.currentConversationId
            ? [...state.messages, assistantMessage]
            : state.messages,
          ragNotice: conversationId === state.currentConversationId ? null : state.ragNotice,
          streamStates: newStreamStates,
        };
      });
    } else {
      set((state) => {
        const newStreamStates = { ...state.streamStates };
        newStreamStates[conversationId] = {
          ...(newStreamStates[conversationId] || defaultStreamState),
          streamingContent: '',
          isStreaming: false,
        };
        return {
          ragNotice: conversationId === state.currentConversationId ? null : state.ragNotice,
          streamStates: newStreamStates,
        };
      });
    }
  },

  setQueueStatus: (pending, active) =>
    set({ queuePending: pending, queueActive: active }),

  setToolProgress: (conversationId, progress) => {
    set((state) => ({
      streamStates: {
        ...state.streamStates,
        [conversationId]: {
          ...(state.streamStates[conversationId] || defaultStreamState),
          toolProgress: progress,
        },
      },
    }));
  },

  setPreviewUrl: (conversationId, url) => {
    set((state) => ({
      streamStates: {
        ...state.streamStates,
        [conversationId]: {
          ...(state.streamStates[conversationId] || defaultStreamState),
          previewUrl: url,
        },
      },
    }));
  },

  setSources: (conversationId, sources) => {
    set((state) => ({
      streamStates: {
        ...state.streamStates,
        [conversationId]: {
          ...(state.streamStates[conversationId] || defaultStreamState),
          sources,
        },
      },
    }));
  },

  clearCodeGenState: (conversationId) => {
    set((state) => ({
      streamStates: {
        ...state.streamStates,
        [conversationId]: {
          ...(state.streamStates[conversationId] || defaultStreamState),
          toolProgress: null,
          previewUrl: null,
          sources: [],
        },
      },
    }));
  },

  reset: () =>
    set({
      currentConversationId: null,
      messages: [],
      ragNotice: null,
      queuePending: 0,
      queueActive: 0,
      streamStates: {},
    }),
}));

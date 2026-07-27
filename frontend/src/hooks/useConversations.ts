import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { conversationsApi } from '@/services/api';
import { useChatStore } from '@/stores/chatStore';

export function useConversations() {
  return useQuery({
    queryKey: ['conversations'],
    queryFn: () => conversationsApi.list().then((r) => r.data),
  });
}

export function useConversationMessages(conversationId: number | null) {
  return useQuery({
    queryKey: ['messages', conversationId],
    queryFn: () =>
      conversationId
        ? conversationsApi.messages(conversationId).then((r) => r.data)
        : [],
    enabled: conversationId !== null,
  });
}

export function useCreateConversation() {
  const queryClient = useQueryClient();
  const { setCurrentConversation } = useChatStore();

  return useMutation({
    mutationFn: (title?: string) => conversationsApi.create(title).then((r) => r.data),
    onSuccess: (conversation) => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
      setCurrentConversation(conversation.id);
    },
  });
}

export function useDeleteConversation() {
  const queryClient = useQueryClient();
  const { currentConversationId, setCurrentConversation } = useChatStore();

  return useMutation({
    mutationFn: (id: number) => conversationsApi.delete(id),
    onSuccess: (_, deletedId) => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
      if (currentConversationId === deletedId) {
        setCurrentConversation(null);
      }
    },
  });
}

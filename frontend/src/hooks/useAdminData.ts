import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  usersApi,
  settingsApi,
  promptsApi,
  wikiApi,
} from '@/services/api';
import type { LLMSettings, Prompt } from '@/types';

// ==================== Users ====================

export function useUsers() {
  return useQuery({
    queryKey: ['admin', 'users'],
    queryFn: () => usersApi.list().then((r) => r.data),
  });
}

export function useCreateUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: { username: string; password: string; role?: string }) =>
      usersApi.create(data.username, data.password, data.role || 'user'),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'users'] }),
  });
}

export function useDeleteUser() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => usersApi.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'users'] }),
  });
}

export function useResetPassword() {
  return useMutation({
    mutationFn: ({ id, password }: { id: number; password: string }) =>
      usersApi.resetPassword(id, password),
  });
}

// ==================== Settings ====================

export function useSettings() {
  return useQuery({
    queryKey: ['admin', 'settings'],
    queryFn: () => settingsApi.get().then((r) => r.data),
    staleTime: 0,
    refetchOnWindowFocus: true,
    refetchOnMount: 'always',
  });
}

export function useUpdateSettings() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (settings: Partial<LLMSettings>) => settingsApi.update(settings),
    onSuccess: (_, variables) => {
      // 立即同步更新缓存，不等 refetch
      queryClient.setQueryData(['admin', 'settings'], (old: LLMSettings | undefined) => {
        if (!old) return old;
        return { ...old, ...variables };
      });
      // 同时触发后台 refetch 确认一致
      queryClient.invalidateQueries({ queryKey: ['admin', 'settings'] });
    },
  });
}

// ==================== Prompts ====================

export function usePrompts() {
  return useQuery({
    queryKey: ['admin', 'prompts'],
    queryFn: () => promptsApi.list().then((r) => r.data),
  });
}

export function useCreatePrompt() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (data: Partial<Prompt>) => promptsApi.create(data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'prompts'] }),
  });
}

export function useUpdatePrompt() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<Prompt> }) =>
      promptsApi.update(id, data),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'prompts'] }),
  });
}

export function useDeletePrompt() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => promptsApi.delete(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'prompts'] }),
  });
}

export function useActivatePrompt() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => promptsApi.activate(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'prompts'] }),
  });
}

export function useDeactivatePrompt() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => promptsApi.deactivate(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['admin', 'prompts'] }),
  });
}

// ==================== Wiki Files ====================

export function useWikiFiles() {
  return useQuery({
    queryKey: ['admin', 'wiki'],
    queryFn: () => wikiApi.list().then((r) => r.data),
  });
}

export function useUploadWikiFile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (file: File) => wikiApi.upload(file),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'wiki'] });
    },
  });
}

export function useDeleteWikiFile() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (filename: string) => wikiApi.delete(filename),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'wiki'] });
    },
  });
}

export function useOrganizeWiki() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (task?: string) => wikiApi.organize(task),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin', 'wiki'] });
    },
  });
}

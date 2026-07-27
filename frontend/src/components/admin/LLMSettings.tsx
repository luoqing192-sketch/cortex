import { useEffect } from 'react';
import { Form, Input, InputNumber, Button, Card, Typography, message, Spin } from 'antd';
import { useSettings, useUpdateSettings } from '@/hooks/useAdminData';

export default function LLMSettings() {
  const { data: settings, isLoading, refetch } = useSettings();
  const updateSettings = useUpdateSettings();
  const [form] = Form.useForm();

  useEffect(() => {
    if (settings) {
      form.setFieldsValue({
        llm_base_url: settings.llm_base_url,
        llm_api_key: settings.llm_api_key,
        llm_model: settings.llm_model,
        llm_temperature: settings.llm_temperature ? parseFloat(settings.llm_temperature) : 0.7,
        llm_max_tokens: settings.llm_max_tokens ? parseInt(settings.llm_max_tokens) : 4096,
        llm_top_p: settings.llm_top_p ? parseFloat(settings.llm_top_p) : 0.9,
        knowledge_retrieval_limit: settings.knowledge_retrieval_limit ? parseInt(settings.knowledge_retrieval_limit) : 3,
        knowledge_min_score: settings.knowledge_min_score ? parseFloat(settings.knowledge_min_score) : 0.7,
      });
    }
  }, [settings, form]);

  const handleSave = async (values: Record<string, unknown>) => {
    try {
      const stringified: Record<string, string> = {};
      for (const [key, value] of Object.entries(values)) {
        stringified[key] = String(value);
      }
      await updateSettings.mutateAsync(stringified as any);
      // 保存后立即 refetch 确认 DB 数据一致
      refetch();
      message.success('设置已保存，新配置立即生效');
    } catch {
      message.error('保存设置失败');
    }
  };

  if (isLoading) return <Spin />;

  return (
    <div>
      <Typography.Title level={5}>LLM 配置</Typography.Title>

      <Card style={{ marginTop: 16 }}>
        <Form form={form} onFinish={handleSave} layout="vertical">
          <Typography.Title level={5} type="secondary">模型设置</Typography.Title>

          <Form.Item name="llm_base_url" label="API Base URL">
            <Input placeholder="https://api.openai.com" />
          </Form.Item>

          <Form.Item name="llm_api_key" label="API Key">
            <Input.Password placeholder="sk-..." />
          </Form.Item>

          <Form.Item name="llm_model" label="模型名称">
            <Input placeholder="gpt-4 / qwen-plus" />
          </Form.Item>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 16 }}>
            <Form.Item name="llm_temperature" label="Temperature">
              <InputNumber min={0} max={2} step={0.1} style={{ width: '100%' }} />
            </Form.Item>

            <Form.Item name="llm_max_tokens" label="Max Tokens">
              <InputNumber min={256} max={32768} step={256} style={{ width: '100%' }} />
            </Form.Item>

            <Form.Item name="llm_top_p" label="Top P">
              <InputNumber min={0} max={1} step={0.05} style={{ width: '100%' }} />
            </Form.Item>
          </div>

          <Typography.Title level={5} type="secondary" style={{ marginTop: 24 }}>知识库检索设置</Typography.Title>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <Form.Item name="knowledge_retrieval_limit" label="检索结果数量">
              <InputNumber min={1} max={10} style={{ width: '100%' }} />
            </Form.Item>

            <Form.Item name="knowledge_min_score" label="最低相似度">
              <InputNumber min={0} max={1} step={0.05} style={{ width: '100%' }} />
            </Form.Item>
          </div>

          <Form.Item>
            <Button type="primary" htmlType="submit" loading={updateSettings.isPending}>
              保存设置
            </Button>
          </Form.Item>
        </Form>
      </Card>
    </div>
  );
}

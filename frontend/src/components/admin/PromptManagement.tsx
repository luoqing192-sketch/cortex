import { useState } from 'react';
import {
  Table, Button, Space, Modal, Form, Input, Switch, Popconfirm, Tag, Typography, message,
} from 'antd';
import { PlusOutlined, EditOutlined, DeleteOutlined, CheckCircleOutlined, StopOutlined, PlayCircleOutlined } from '@ant-design/icons';
import {
  usePrompts, useCreatePrompt, useUpdatePrompt, useDeletePrompt,
  useActivatePrompt, useDeactivatePrompt,
} from '@/hooks/useAdminData';
import type { Prompt } from '@/types';

const { TextArea } = Input;

export default function PromptManagement() {
  const { data: prompts, isLoading } = usePrompts();
  const createPrompt = useCreatePrompt();
  const updatePrompt = useUpdatePrompt();
  const deletePrompt = useDeletePrompt();
  const activatePrompt = useActivatePrompt();
  const deactivatePrompt = useDeactivatePrompt();

  const [editVisible, setEditVisible] = useState(false);
  const [editingPrompt, setEditingPrompt] = useState<Prompt | null>(null);
  const [form] = Form.useForm();

  const handleOpenCreate = () => {
    setEditingPrompt(null);
    form.resetFields();
    form.setFieldsValue({ is_active: false });
    setEditVisible(true);
  };

  const handleOpenEdit = (prompt: Prompt) => {
    setEditingPrompt(prompt);
    form.setFieldsValue(prompt);
    setEditVisible(true);
  };

  const handleSave = async (values: { name: string; content: string; description: string; is_active: boolean }) => {
    try {
      if (editingPrompt) {
        await updatePrompt.mutateAsync({ id: editingPrompt.id, data: values });
        message.success('System Prompt 已更新');
      } else {
        await createPrompt.mutateAsync(values);
        message.success('System Prompt 已创建');
      }
      setEditVisible(false);
    } catch {
      message.error('保存失败');
    }
  };

  const handleActivate = async (id: number) => {
    try {
      await activatePrompt.mutateAsync(id);
      message.success('System Prompt 已激活');
    } catch {
      message.error('激活失败');
    }
  };

  const handleDeactivate = async (id: number) => {
    try {
      await deactivatePrompt.mutateAsync(id);
      message.success('System Prompt 已停用');
    } catch {
      message.error('停用失败');
    }
  };

  const columns = [
    {
      title: '名称',
      dataIndex: 'name',
      key: 'name',
    },
    {
      title: '描述',
      dataIndex: 'description',
      key: 'description',
      ellipsis: true,
    },
    {
      title: '状态',
      key: 'status',
      width: 100,
      render: (_: unknown, record: Prompt) => (
        record.is_active
          ? <Tag color="success" icon={<CheckCircleOutlined />}>激活</Tag>
          : <Tag>停用</Tag>
      ),
    },
    {
      title: '操作',
      key: 'action',
      width: 280,
      render: (_: unknown, record: Prompt) => (
        <Space>
          <Button size="small" icon={<EditOutlined />} onClick={() => handleOpenEdit(record)}>
            编辑
          </Button>
          {record.is_active ? (
            <Button
              size="small"
              icon={<StopOutlined />}
              onClick={() => handleDeactivate(record.id)}
            >
              停用
            </Button>
          ) : (
            <Button
              size="small"
              type="primary"
              icon={<PlayCircleOutlined />}
              onClick={() => handleActivate(record.id)}
            >
              激活
            </Button>
          )}
          <Popconfirm
            title="确定删除此 System Prompt？"
            onConfirm={() => deletePrompt.mutate(record.id)}
            okText="删除"
            cancelText="取消"
          >
            <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <Typography.Title level={5} style={{ margin: 0 }}>System Prompt 管理</Typography.Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={handleOpenCreate}>
          新建 System Prompt
        </Button>
      </div>

      <Table
        dataSource={prompts || []}
        columns={columns}
        rowKey="id"
        loading={isLoading}
        size="small"
      />

      <Modal
        title={editingPrompt ? '编辑 System Prompt' : '新建 System Prompt'}
        open={editVisible}
        onCancel={() => setEditVisible(false)}
        footer={null}
        width={640}
      >
        <Form form={form} onFinish={handleSave} layout="vertical">
          <Form.Item name="name" label="名称" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="description" label="描述">
            <Input />
          </Form.Item>
          <Form.Item name="content" label="System Prompt 内容" rules={[{ required: true }]}>
            <TextArea rows={8} placeholder="你是 AI 助手..." />
          </Form.Item>
          <Form.Item name="is_active" label="立即激活" valuePropName="checked">
            <Switch />
          </Form.Item>
          <Form.Item>
            <Space>
              <Button
                type="primary"
                htmlType="submit"
                loading={createPrompt.isPending || updatePrompt.isPending}
              >
                {editingPrompt ? '保存' : '创建'}
              </Button>
              <Button onClick={() => setEditVisible(false)}>取消</Button>
            </Space>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

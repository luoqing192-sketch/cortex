import { useState } from 'react';
import {
  Table, Button, Space, Modal, Form, Input, Select, Popconfirm, Tag, message, Typography,
} from 'antd';
import { PlusOutlined, DeleteOutlined, KeyOutlined } from '@ant-design/icons';
import {
  useUsers, useCreateUser, useDeleteUser, useResetPassword,
} from '@/hooks/useAdminData';
import type { User } from '@/types';
import dayjs from 'dayjs';

export default function UserManagement() {
  const { data: users, isLoading } = useUsers();
  const createUser = useCreateUser();
  const deleteUser = useDeleteUser();
  const resetPassword = useResetPassword();

  const [createVisible, setCreateVisible] = useState(false);
  const [resetVisible, setResetVisible] = useState(false);
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [createForm] = Form.useForm();
  const [resetForm] = Form.useForm();

  const handleCreate = async (values: { username: string; password: string; role: string }) => {
    try {
      await createUser.mutateAsync(values);
      message.success('用户创建成功');
      setCreateVisible(false);
      createForm.resetFields();
    } catch {
      message.error('创建用户失败');
    }
  };

  const handleResetPassword = async (values: { password: string }) => {
    if (!selectedUserId) return;
    try {
      await resetPassword.mutateAsync({ id: selectedUserId, password: values.password });
      message.success('密码已重置');
      setResetVisible(false);
      resetForm.resetFields();
    } catch {
      message.error('重置密码失败');
    }
  };

  const columns = [
    {
      title: 'ID',
      dataIndex: 'id',
      key: 'id',
      width: 60,
    },
    {
      title: '用户名',
      dataIndex: 'username',
      key: 'username',
    },
    {
      title: '角色',
      dataIndex: 'role',
      key: 'role',
      render: (role: string) => (
        <Tag color={role === 'admin' ? 'purple' : 'blue'}>
          {role === 'admin' ? '管理员' : '用户'}
        </Tag>
      ),
    },
    {
      title: '创建时间',
      dataIndex: 'created_at',
      key: 'created_at',
      render: (t: string) => dayjs(t).format('YYYY-MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'action',
      render: (_: unknown, record: User) => (
        <Space>
          <Button
            size="small"
            icon={<KeyOutlined />}
            onClick={() => { setSelectedUserId(record.id); setResetVisible(true); }}
          >
            重置密码
          </Button>
          <Popconfirm
            title="确定删除此用户？"
            onConfirm={() => deleteUser.mutate(record.id)}
            okText="删除"
            cancelText="取消"
          >
            <Button size="small" danger icon={<DeleteOutlined />}>
              删除
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 16, display: 'flex', justifyContent: 'space-between' }}>
        <Typography.Title level={5} style={{ margin: 0 }}>用户管理</Typography.Title>
        <Button type="primary" icon={<PlusOutlined />} onClick={() => setCreateVisible(true)}>
          新建用户
        </Button>
      </div>

      <Table
        dataSource={users || []}
        columns={columns}
        rowKey="id"
        loading={isLoading}
        size="small"
        pagination={{ pageSize: 10 }}
      />

      <Modal
        title="新建用户"
        open={createVisible}
        onCancel={() => setCreateVisible(false)}
        footer={null}
      >
        <Form form={createForm} onFinish={handleCreate} layout="vertical">
          <Form.Item name="username" label="用户名" rules={[{ required: true }]}>
            <Input />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true, min: 6 }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item name="role" label="角色" initialValue="user">
            <Select>
              <Select.Option value="user">用户</Select.Option>
              <Select.Option value="admin">管理员</Select.Option>
            </Select>
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={createUser.isPending}>创建</Button>
          </Form.Item>
        </Form>
      </Modal>

      <Modal
        title="重置密码"
        open={resetVisible}
        onCancel={() => setResetVisible(false)}
        footer={null}
      >
        <Form form={resetForm} onFinish={handleResetPassword} layout="vertical">
          <Form.Item name="password" label="新密码" rules={[{ required: true, min: 6 }]}>
            <Input.Password />
          </Form.Item>
          <Form.Item>
            <Button type="primary" htmlType="submit" loading={resetPassword.isPending}>确认重置</Button>
          </Form.Item>
        </Form>
      </Modal>
    </div>
  );
}

import {
  Card, Button, Space, Popconfirm, Typography,
  message, Upload, Table,
} from 'antd';
import {
  DeleteOutlined, InboxOutlined,
  FileMarkdownOutlined, ThunderboltOutlined,
} from '@ant-design/icons';
import {
  useWikiFiles, useUploadWikiFile, useDeleteWikiFile, useOrganizeWiki,
} from '@/hooks/useAdminData';
import type { WikiFile } from '@/types';
import dayjs from 'dayjs';

const { Dragger } = Upload;

export default function KnowledgeManagement() {
  const { data: wikiFiles, isLoading: wikiLoading } = useWikiFiles();
  const uploadWiki = useUploadWikiFile();
  const deleteWiki = useDeleteWikiFile();
  const organizeWiki = useOrganizeWiki();

  const handleUploadWiki = async (file: File) => {
    if (!file.name.endsWith('.md')) {
      message.warning('仅支持 .md (Markdown) 文件');
      return false;
    }
    try {
      await uploadWiki.mutateAsync(file);
      message.success(`Wiki 文件 "${file.name}" 上传成功`);
    } catch {
      message.error('上传失败');
    }
    return false;
  };

  const handleOrganizeWiki = async () => {
    message.loading({ content: 'Wiki 整理中（LLM 正在分析文档...）', key: 'organize', duration: 0 });
    try {
      await organizeWiki.mutateAsync(undefined);
      message.success({ content: 'Wiki 整理完成！已生成/更新文档', key: 'organize' });
    } catch {
      message.error({ content: 'Wiki 整理失败', key: 'organize' });
    }
  };

  const wikiColumns = [
    {
      title: '标题',
      dataIndex: 'name',
      key: 'name',
      render: (name: string) => (
        <Space>
          <FileMarkdownOutlined style={{ color: 'var(--primary)' }} />
          {name}
        </Space>
      ),
    },
    {
      title: '大小',
      dataIndex: 'size',
      key: 'size',
      width: 100,
      render: (s: number) => s < 1024 ? `${s} B` : `${(s / 1024).toFixed(1)} KB`,
    },
    {
      title: '更新时间',
      dataIndex: 'updated_at',
      key: 'time',
      width: 140,
      render: (t: string) => dayjs(t).format('MM-DD HH:mm'),
    },
    {
      title: '操作',
      key: 'action',
      width: 80,
      render: (_: unknown, record: WikiFile) => (
        <Popconfirm
          title="确定删除此 Wiki 文件？"
          onConfirm={() => deleteWiki.mutate(record.filename)}
        >
          <Button size="small" danger icon={<DeleteOutlined />}>删除</Button>
        </Popconfirm>
      ),
    },
  ];

  return (
    <div>
      {/* Wiki Files — LLM 检索的知识来源 */}
      <Card
        title={
          <Space>
            <FileMarkdownOutlined />
            <span>Wiki 知识文件</span>
          </Space>
        }
        size="small"
        extra={
          <Space>
            <Button
              icon={<ThunderboltOutlined />}
              onClick={handleOrganizeWiki}
              loading={organizeWiki.isPending}
              style={{ color: 'var(--primary)' }}
            >
              Wiki 整理
            </Button>
            <Typography.Text type="secondary" style={{ fontSize: 12 }}>
              上传 .md 文件，聊天时 LLM 会自动检索相关内容
            </Typography.Text>
          </Space>
        }
      >
        <Dragger
          beforeUpload={handleUploadWiki}
          showUploadList={false}
          accept=".md"
          style={{ marginBottom: 16 }}
        >
          <p><InboxOutlined style={{ fontSize: 32, color: 'var(--primary)' }} /></p>
          <p>点击或拖拽 .md 文件到此区域上传</p>
          <p style={{ color: 'var(--text-muted)', fontSize: 12 }}>
            文件名即标题，上传后立即生效（无需重启）
          </p>
        </Dragger>

        <Table
          dataSource={wikiFiles || []}
          columns={wikiColumns}
          rowKey="filename"
          loading={wikiLoading}
          size="small"
          pagination={{ pageSize: 10 }}
        />
      </Card>
    </div>
  );
}
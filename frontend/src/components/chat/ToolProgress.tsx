import React from 'react';
import { Spin } from 'antd';
import { CodeOutlined, SearchOutlined, FileTextOutlined, PlayCircleOutlined } from '@ant-design/icons';

interface ToolProgressProps {
  tool: string;
  status: string;
}

// 工具名称到中文描述的映射
const toolLabels: Record<string, { label: string; icon: React.ReactNode }> = {
  search_codebase: { label: '搜索代码库', icon: <SearchOutlined /> },
  read_file: { label: '读取文件', icon: <FileTextOutlined /> },
  get_project_structure: { label: '获取项目结构', icon: <FileTextOutlined /> },
  get_symbol_definition: { label: '解析符号定义', icon: <CodeOutlined /> },
  generate_code: { label: '生成代码', icon: <CodeOutlined /> },
  run_command: { label: '执行命令', icon: <PlayCircleOutlined /> },
};

const ToolProgress: React.FC<ToolProgressProps> = ({ tool, status }) => {
  const toolInfo = toolLabels[tool] || { label: tool, icon: <CodeOutlined /> };
  const isRunning = status === 'running';

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 8,
      padding: '6px 12px', margin: '4px 0',
      background: '#f6f8fa', borderRadius: 6, fontSize: 13
    }}>
      {isRunning ? <Spin size="small" /> : toolInfo.icon}
      <span style={{ color: '#586069' }}>
        {isRunning ? `正在${toolInfo.label}...` : `${toolInfo.label} ✓`}
      </span>
    </div>
  );
};

export default ToolProgress;

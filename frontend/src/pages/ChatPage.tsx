import { Layout } from 'antd';
import ConversationSidebar from '@/components/chat/ConversationSidebar';
import MessageList from '@/components/chat/MessageList';
import MessageInput from '@/components/chat/MessageInput';
import QueueIndicator from '@/components/chat/QueueIndicator';

const { Sider, Content } = Layout;

export default function ChatPage() {
  return (
    <Layout style={{ height: '100vh' }}>
      <Sider
        width={280}
        style={{
          background: 'linear-gradient(180deg, var(--sidebar-start) 0%, var(--sidebar-end) 100%)',
          height: '100vh',
          overflow: 'hidden',
        }}
      >
        <ConversationSidebar />
      </Sider>

      <Content style={{ display: 'flex', flexDirection: 'column', background: 'var(--bg-main)' }}>
        <QueueIndicator />
        <MessageList />
        <MessageInput />
      </Content>
    </Layout>
  );
}

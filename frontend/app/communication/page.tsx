import { getDemoLog } from '@/lib/data';
import CommunicationClient from '@/components/communication/CommunicationClient';

export default function CommunicationPage() {
  const logs = getDemoLog();
  return <CommunicationClient logs={logs} />;
}

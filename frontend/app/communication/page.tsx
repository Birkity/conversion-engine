import { getDemoLog, getAllCompanyData } from '@/lib/data';
import CommunicationClient from '@/components/communication/CommunicationClient';

export const dynamic = 'force-dynamic';

export default function CommunicationPage() {
  const logs = getDemoLog();
  const companies = getAllCompanyData();
  return <CommunicationClient logs={logs} companies={companies} />;
}

import { TaskDetailReplicaPage } from "@/components/app-pages-replica";

export default function TaskDetailPage({ params }: { params: { id: string } }) {
  return <TaskDetailReplicaPage taskId={params.id} />;
}

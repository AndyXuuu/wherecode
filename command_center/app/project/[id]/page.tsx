import { ProjectDetailReplicaPage } from "@/components/app-pages-replica";

export default function ProjectDetailPage({ params }: { params: { id: string } }) {
  return <ProjectDetailReplicaPage projectId={params.id} />;
}

import { ProjectSettingsReplicaPage } from "@/components/app-pages-replica";

export default function ProjectSettingsPage({ params }: { params: { id: string } }) {
  return <ProjectSettingsReplicaPage projectId={params.id} />;
}

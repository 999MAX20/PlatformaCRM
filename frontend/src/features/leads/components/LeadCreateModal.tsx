import { LeadForm } from "../../../components/forms/LeadForm";
import { Modal } from "../../../components/ui/Modal";
import type { LeadCreatePayload } from "../../../api/leads";
import type { Client, Id, Service, TeamMember } from "../../../types";

export function LeadCreateModal({
  open,
  title,
  businessId,
  initialClientId,
  clients,
  services,
  teamMembers,
  onClose,
  onSubmit,
  onOpenClient,
}: {
  open: boolean;
  title: string;
  businessId: Id;
  initialClientId?: Id;
  clients: Client[];
  services: Service[];
  teamMembers: TeamMember[];
  onClose: () => void;
  onSubmit: (payload: LeadCreatePayload) => Promise<unknown>;
  onOpenClient: (id: Id) => void;
}) {
  return (
    <Modal title={title} open={open} onClose={onClose}>
      <LeadForm
        businessId={businessId}
        initialClientId={initialClientId}
        clients={clients}
        services={services}
        teamMembers={teamMembers}
        onSubmit={onSubmit}
        onOpenClient={onOpenClient}
      />
    </Modal>
  );
}

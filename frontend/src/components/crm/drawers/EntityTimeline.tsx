import type { CrmCardPayload } from "../../../types";
import { EntityTimelineList } from "./timeline";

export function EntityTimeline({ data }: { data: CrmCardPayload }) {
  return <EntityTimelineList data={data} />;
}

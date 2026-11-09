import type { CrmCardPayload } from "../../../types";
import { EntityTimelineList } from "./timeline";

export function EntityTimeline({ data, locale, timeZone }: { data: CrmCardPayload; locale?: string; timeZone?: string }) {
  return <EntityTimelineList data={data} locale={locale} timeZone={timeZone} />;
}

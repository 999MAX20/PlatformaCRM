import { categoryConfig } from "../../components/crm/drawers/timelineHelpers";
import {
  DataTable,
  type DataTableRowInteraction,
} from "../../components/tables/DataTable";
import { Button } from "../../components/ui/Button";
import { useI18n } from "../../lib/i18n";
import type { TimelineEvent } from "../../types/timeline";
import { TimelineCategory, TimelineEventLabel } from "./TimelineDetails";
import { timelineDate, timelineSummary, timelineObjectLabel } from "./timelinePresentation";
import { Fragment } from "react";
import { useMediaQuery } from "../../hooks/useMediaQuery";

export function TimelineEventTable({
  rows,
  selectedId,
  timeZone,
  isLoading,
  busy,
  hasFilters,
  onReset,
  onSelect,
}: {
  rows: TimelineEvent[];
  selectedId?: TimelineEvent["id"];
  timeZone: string;
  isLoading: boolean;
  busy: boolean;
  hasFilters: boolean;
  onReset: () => void;
  onSelect: (
    event: TimelineEvent,
    interaction: DataTableRowInteraction,
  ) => void;
}) {
  const { language, t } = useI18n();
  const mobile = useMediaQuery("(max-width: 767px)");
  if (mobile && rows.length && !isLoading) return (
    <div className="h-full min-h-0 overflow-auto overscroll-contain" aria-label={t("timeline.title")}>
      {rows.map((event, index) => {
        const day = timelineDate(event.created_at, language, timeZone);
        const object = timelineObjectLabel(event, t);
        return <Fragment key={event.id}>
          {(index === 0 || timelineDate(rows[index - 1].created_at, language, timeZone) !== day) && <h3 className="bg-surface-muted px-3 py-2 text-xs font-semibold text-platforma-subtle">{day}</h3>}
          <button type="button" disabled={busy}
            data-testid={`timeline-event-${event.id}`} data-focus-return-id={`timeline-event-${event.id}`}
            aria-current={selectedId === event.id ? "true" : undefined}
            className={`platforma-focus-ring block w-full space-y-1 border-b border-platforma-border px-3 py-3 text-left ${selectedId === event.id ? "bg-surface-muted" : "bg-surface-card"}`}
            onClick={() => onSelect(event, { source: "pointer" })}
            onKeyDown={(key) => { if (key.key === "Enter" || key.key === " ") { key.preventDefault(); onSelect(event, {source: "keyboard", key: key.key}); } }}>
            <span className="flex items-start justify-between gap-2"><span className="min-w-0 break-words text-sm font-semibold"><TimelineEventLabel event={event}/></span><time className="shrink-0 text-xs tabular-nums text-platforma-subtle" dateTime={event.created_at}>{timelineDate(event.created_at, language, timeZone, true)}</time></span>
            <span className="block break-words text-sm">{object}</span>
            {event.client_name && event.client_name !== object && <span className="block break-words text-xs text-platforma-subtle">{event.client_name}</span>}
            <span className="flex flex-wrap items-center justify-between gap-2 text-xs text-platforma-subtle"><span>{t("timeline.actor")}: {event.actor_name || t(event.actor ? "timeline.unknownActor" : "timeline.noActor")}</span><TimelineCategory event={event}/></span>
          </button>
        </Fragment>;
      })}
    </div>
  );
  return (
    <DataTable
      className="h-full !rounded-none !border-0 !shadow-none"
      hideFooter
      rows={rows}
      rowKey={(event) => event.id}
      isLoading={isLoading}
      selectedRowKey={selectedId}
      tableLabel={t("timeline.title")}
      rowAriaLabel={(event) =>
        `${t("timeline.openDetails")}: ${timelineSummary(event.event_type, t)}, ${timelineObjectLabel(event, t)}, ${timelineDate(event.created_at, language, timeZone, true)}`
      }
      rowFocusReturnId={(event) => `timeline-event-${event.id}`}
      rowTestId={(event) => `timeline-event-${event.id}`}
      rowGroup={(event) => timelineDate(event.created_at, language, timeZone)}
      onRowSelect={
        busy
          ? undefined
          : (event, _index, interaction) => onSelect(event, interaction)
      }
      emptyTitle={t(hasFilters ? "common.noResults" : "timeline.emptyTitle")}
      emptyDescription={t(
        hasFilters ? "timeline.emptyFilteredText" : "timeline.emptyText",
      )}
      emptyAction={
        hasFilters ? (
          <Button variant="secondary" onClick={onReset}>
            {t("timeline.reset")}
          </Button>
        ) : undefined
      }
      columns={[
        {
          header: t("timeline.event"),
          className: "!whitespace-normal",
          cell: (event) => {
            const config =
              categoryConfig[event.category] || categoryConfig.system;
            const Icon = config.icon;
            return (
              <div className="flex max-w-[360px] items-start gap-3">
                <span
                  className={`grid h-8 w-8 shrink-0 place-items-center rounded-control ${config.iconClassName}`}
                >
                  <Icon aria-hidden size={17} />
                </span>
                <span className="min-w-0 break-words font-semibold text-platforma-text">
                  <TimelineEventLabel event={event} />
                </span>
              </div>
            );
          },
        },
        {
          header: t("timeline.object"),
          cell: (event) => (
            <span
              className="block max-w-[200px] truncate"
              title={timelineObjectLabel(event, t)}
            >
              {timelineObjectLabel(event, t)}
              {event.client_name && event.client_name !== timelineObjectLabel(event, t) && <span className="block truncate text-xs text-platforma-subtle">{event.client_name}</span>}
            </span>
          ),
        },
        {
          header: t("timeline.actor"),
          className: "min-w-[160px]",
          cell: (event) => (
            <span
              className="block max-w-[160px] truncate"
              title={event.actor_name}
            >
              {event.actor_name ||
                t(event.actor ? "timeline.unknownActor" : "timeline.noActor")}
            </span>
          ),
        },
        {
          header: t("timeline.time"),
          className: "min-w-20",
          cell: (event) => (
            <time
              dateTime={event.created_at}
              title={`${timelineDate(event.created_at, language, timeZone)} (${timeZone})`}
              className="tabular-nums"
            >
              {timelineDate(event.created_at, language, timeZone, true)}
            </time>
          ),
        },
        {
          header: t("timeline.category"),
          cell: (event) => <TimelineCategory event={event} />,
        },
      ]}
    />
  );
}

package kz.zani.mobile.core

import java.time.LocalDate
import java.time.ZoneId

enum class AgendaMode { LIST, CALENDAR }
enum class AgendaTimeIssue(val key: String) { UNKNOWN("agendaUnknownTime"), INVALID_RANGE("agendaInvalidRange"), OTHER_DAY("agendaOtherDay"), SOURCE_DAY("agendaSourceDayMismatch") }
data class AgendaDayRow(val appointment: Appointment, val issue: AgendaTimeIssue?)
class AgendaDayDisplay(items: List<Appointment>, day: String, responseDay: String?, timezone: String) {
    val sourceRows: List<AgendaDayRow> = items.map { item ->
        val issue = if (responseDay != day) AgendaTimeIssue.SOURCE_DAY else runCatching {
            val zone = ZoneId.of(timezone); require(LocalDate.parse(day).toString() == day)
            val start = item.start; val end = item.end
            when { end <= start -> AgendaTimeIssue.INVALID_RANGE; start.atZone(zone).toLocalDate().toString() != day -> AgendaTimeIssue.OTHER_DAY; else -> null }
        }.getOrElse { AgendaTimeIssue.UNKNOWN }
        AgendaDayRow(item,issue)
    }
    val uncertain: List<AgendaDayRow> get() = sourceRows.filter { it.issue != null }
    // Chronology is a display order, independent from original sourceRows.
    val scheduled: List<AgendaDayRow> get() = sourceRows.filter { it.issue == null }.sortedWith(compareBy<AgendaDayRow> { it.appointment.start }.thenBy { it.appointment.id })
}

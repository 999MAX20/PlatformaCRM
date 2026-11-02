package kz.zani.mobile.ui

import java.time.DateTimeException
import java.time.Instant
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.time.format.FormatStyle
import java.util.Locale

/** Presentation only: no changes to the source instant or Business context. */
internal fun formatAppointmentDate(startAt: String?, timezone: String?, language: String): String? {
    if (timezone == null || startAt == null) return null
    return try {
        val formatter = DateTimeFormatter.ofLocalizedDateTime(FormatStyle.MEDIUM, FormatStyle.SHORT)
            .withLocale(Locale.forLanguageTag(language))
        Instant.parse(startAt).atZone(ZoneId.of(timezone)).format(formatter)
    } catch (_: DateTimeException) { null }
}

internal fun formatAgendaEndpoint(raw: String?, timezone: String?, language: String): String? {
    if (raw == null || timezone == null) return null
    val label = formatAppointmentDate(raw, timezone, language) ?: return null
    return try {
        val offset = Instant.parse(raw).atZone(ZoneId.of(timezone)).offset.id.let { if (it == "Z") "+00:00" else it }
        "$label (UTC$offset)"
    } catch (_: DateTimeException) { null }
}

package kz.zani.mobile.data

import kz.zani.mobile.core.ReadException
import kz.zani.mobile.core.ReadProblem
import org.json.JSONObject
import java.util.Locale

/** UI labels only; never convert API enums or merchant-entered data. */
class UiCopy(document: String, preferredLanguage: String) {
    val language: String
    val values: Map<String, String>
    init {
        try {
            val root = JSONObject(document)
            val english = root.getJSONObject("en")
            val keys = english.keys().asSequence().toSet()
            require(keys.isNotEmpty())
            val dictionaries = listOf("en", "ru", "kk").associateWith { locale ->
                val copy = root.getJSONObject(locale)
                require(copy.keys().asSequence().toSet() == keys)
                keys.associateWith { key -> copy.getString(key).also { require(it.isNotBlank()) } }
            }
            val primary = preferredLanguage.trim().replace('_', '-').substringBefore('-').lowercase(Locale.ROOT)
            language = primary.takeIf { it in dictionaries } ?: "en"
            values = dictionaries.getValue(language)
        } catch (_: Exception) { throw ReadException(ReadProblem.INVALID_PAYLOAD) }
    }
    fun text(key: String): String = values[key] ?: key
}

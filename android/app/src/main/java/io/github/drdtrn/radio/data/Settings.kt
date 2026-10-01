package io.github.drdtrn.radio.data

import android.content.Context
import androidx.core.content.edit

data class Country(val code: String, val label: String)

/** The same two countries, in the same tab order, as the desktop app. */
val COUNTRIES = listOf(Country("XK", "Kosovo"), Country("SA", "Saudi Arabia"))

const val DEFAULT_VOLUME = 100
const val DEFAULT_TAB = "XK"

/** Persisted user settings: the Android counterpart of config.toml. */
class Settings(context: Context) {
    private val prefs = context.getSharedPreferences("settings", Context.MODE_PRIVATE)

    var volume: Int
        get() = prefs.getInt(KEY_VOLUME, DEFAULT_VOLUME).coerceIn(0, 100)
        set(value) = prefs.edit { putInt(KEY_VOLUME, value) }

    var lastTab: String
        get() = prefs.getString(KEY_LAST_TAB, null) ?: DEFAULT_TAB
        set(value) = prefs.edit { putString(KEY_LAST_TAB, value) }

    var sortOrder: SortOrder
        get() = SortOrder.entries.firstOrNull { it.name == prefs.getString(KEY_SORT, null) }
            ?: SortOrder.NAME
        set(value) = prefs.edit { putString(KEY_SORT, value.name) }

    private companion object {
        const val KEY_VOLUME = "volume"
        const val KEY_LAST_TAB = "last_tab"
        const val KEY_SORT = "sort_order"
    }
}

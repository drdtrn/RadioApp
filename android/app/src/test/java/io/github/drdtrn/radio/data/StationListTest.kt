package io.github.drdtrn.radio.data

import org.junit.Assert.assertEquals
import org.junit.Test

class StationListTest {
    private val stations = listOf(
        Station(stationuuid = "1", name = "radio Beta", countrycode = "XK", bitrate = 64, tags = listOf("pop")),
        Station(stationuuid = "2", name = "Alpha FM", countrycode = "XK", bitrate = 128, tags = listOf("news")),
        Station(stationuuid = "3", name = "Quran Radio", countrycode = "SA", bitrate = 128),
        Station(stationuuid = "4", name = "Gamma", countrycode = "XK", bitrate = 128),
        Station(stationuuid = "2", name = "Alpha FM", countrycode = "XK", bitrate = 128, tags = listOf("news")),
    )

    private fun names(code: String, query: String = "", order: SortOrder = SortOrder.NAME) =
        stationsFor(stations, code, query, order).map { it.name }

    @Test
    fun keepsOnlyTheTabsCountry_sortedByNameIgnoringCase_withoutDuplicates() {
        assertEquals(listOf("Alpha FM", "Gamma", "radio Beta"), names("XK"))
        assertEquals(listOf("Quran Radio"), names("SA"))
    }

    @Test
    fun bitrateOrder_isHighestFirstWithNamesBreakingTies() {
        assertEquals(listOf("Alpha FM", "Gamma", "radio Beta"), names("XK", order = SortOrder.BITRATE))
    }

    @Test
    fun query_filtersByNameOrTag() {
        assertEquals(listOf("radio Beta"), names("XK", "POP"))
        assertEquals(listOf("Alpha FM"), names("XK", "alpha"))
        assertEquals(emptyList<String>(), names("XK", "jazz"))
    }
}

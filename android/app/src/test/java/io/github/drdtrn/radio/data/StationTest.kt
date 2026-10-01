package io.github.drdtrn.radio.data

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class StationTest {
    @Test
    fun fromApiJson_prefersResolvedUrlAndSplitsTags() {
        val station = Station.fromApiJson(
            JSONObject(
                """
                {"stationuuid": "abc-123", "name": "Radio Kosova e Lire",
                 "url": "http://raw.example/stream", "url_resolved": "http://resolved.example/stream",
                 "countrycode": "XK", "tags": "news, talk , ", "language": "albanian",
                 "bitrate": "128", "hls": 0}
                """
            )
        )

        assertEquals("http://resolved.example/stream", station.url)
        assertEquals(listOf("news", "talk"), station.tags)
        assertEquals(128, station.bitrate)
        assertFalse(station.hls)
    }

    @Test
    fun fromApiJson_fallsBackToRawUrlAndDefaults() {
        val station = Station.fromApiJson(JSONObject("""{"name": "No Extras FM", "url": "http://raw.example"}"""))

        assertEquals("http://raw.example", station.url)
        assertEquals(emptyList<String>(), station.tags)
        assertEquals(0, station.bitrate)
        assertEquals("", station.countrycode)
    }

    @Test
    fun fromApiJson_treatsJsonNullAsMissing() {
        val station = Station.fromApiJson(
            JSONObject("""{"name": null, "url_resolved": null, "url": "http://x", "tags": null, "bitrate": null}""")
        )

        assertEquals(Station.UNKNOWN_NAME, station.name)
        assertEquals("http://x", station.url)
        assertEquals(emptyList<String>(), station.tags)
        assertEquals(0, station.bitrate)
    }

    @Test
    fun fromApiJson_readsHlsFlagAndTrimsName() {
        val station = Station.fromApiJson(JSONObject("""{"name": "  MBC FM \n", "hls": 1}"""))

        assertEquals("MBC FM", station.name)
        assertTrue(station.hls)
    }

    @Test
    fun cacheRoundTrip_preservesFields() {
        val station = Station(
            stationuuid = "abc-123",
            name = "Radio Kosova e Lire",
            url = "http://resolved.example/stream",
            countrycode = "XK",
            tags = listOf("news", "talk"),
            language = "albanian",
            bitrate = 128,
            hls = true,
        )

        assertEquals(station, Station.fromCacheJson(JSONObject(station.toCacheJson().toString())))
    }

    @Test
    fun matches_searchesNameAndTagsCaseInsensitively() {
        val station = Station(name = "Radio Kosova e Lire", tags = listOf("News", "talk"))

        assertTrue(station.matches("kosova"))
        assertTrue(station.matches("  NEWS "))
        assertTrue(station.matches(""))
        assertFalse(station.matches("jazz"))
    }
}

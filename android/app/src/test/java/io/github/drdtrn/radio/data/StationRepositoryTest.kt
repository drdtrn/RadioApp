package io.github.drdtrn.radio.data

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder
import java.io.File
import java.io.IOException

private const val HOUR = 60 * 60 * 1000L
private const val NOW = 1_000_000_000_000L

private fun stationJson(name: String = "Radio Test", countrycode: String = "XK") = """
    {"stationuuid": "uuid-$name", "name": "$name", "url": "http://example/stream",
     "url_resolved": "http://example/stream", "countrycode": "$countrycode",
     "tags": "pop", "language": "albanian", "bitrate": "128"}
"""

class StationRepositoryTest {
    @get:Rule
    val tmp = TemporaryFolder()

    private val cacheFile: File get() = File(tmp.root, "stations.json")

    private fun repository(http: HttpGet, countries: List<String> = listOf("XK")) =
        StationRepository(cacheFile, countries, http, clock = { NOW })

    private val offline = HttpGet { throw IOException("offline") }
    private val mustNotFetch = HttpGet { throw AssertionError("should not call the API") }

    @Test
    fun fetchStations_hitsOneUrlPerCountry() {
        val requested = mutableListOf<String>()
        val http = HttpGet { url ->
            requested += url
            "[${stationJson(name = url.takeLast(2))}]"
        }

        val stations = repository(http, listOf("XK", "SA")).fetchStations()

        assertEquals(listOf("$API_BASE/XK", "$API_BASE/SA"), requested)
        assertEquals(2, stations.size)
    }

    @Test
    fun saveAndLoadCache_roundTrip() {
        val repo = repository(mustNotFetch)
        val station = Station(stationuuid = "uuid-1", name = "Radio Test", url = "http://x", countrycode = "XK")

        repo.saveCache(listOf(station), fetchedAt = 1000L)

        assertEquals(CachedStations(listOf(station), 1000L), repo.loadCache())
    }

    @Test
    fun loadCache_returnsNullWhenMissingOrCorrupt() {
        assertNull(repository(mustNotFetch).loadCache())

        cacheFile.writeText("{\"fetched_at\": 12, \"stations\": [")
        assertNull(repository(mustNotFetch).loadCache())
    }

    @Test
    fun isStale_afterOneDay() {
        assertTrue(isStale(fetchedAt = NOW - 25 * HOUR, now = NOW))
        assertFalse(isStale(fetchedAt = NOW - 1 * HOUR, now = NOW))
    }

    @Test
    fun getStations_usesFreshCacheWithoutHittingApi() {
        val station = Station(stationuuid = "uuid-1", countrycode = "XK")
        repository(mustNotFetch).saveCache(listOf(station), fetchedAt = NOW - HOUR)

        val result = repository(mustNotFetch).getStations()

        assertTrue(result.fromCache)
        assertEquals(listOf(station), result.stations)
    }

    @Test
    fun getStations_refetchesAndRewritesStaleCache() {
        repository(mustNotFetch).saveCache(emptyList(), fetchedAt = NOW - 48 * HOUR)

        val result = repository({ "[${stationJson()}]" }).getStations()

        assertFalse(result.fromCache)
        assertEquals(NOW, result.cacheTimestamp)
        assertEquals(NOW, repository(mustNotFetch).loadCache()?.fetchedAt)
    }

    @Test
    fun getStations_forceRefreshBypassesFreshCache() {
        repository(mustNotFetch).saveCache(emptyList(), fetchedAt = NOW - HOUR)

        val result = repository({ "[${stationJson()}]" }).getStations(forceRefresh = true)

        assertFalse(result.fromCache)
        assertEquals(1, result.stations.size)
    }

    @Test
    fun getStations_fallsBackToStaleCacheOnApiFailure() {
        val stale = NOW - 48 * HOUR
        repository(mustNotFetch).saveCache(listOf(Station(stationuuid = "uuid-1")), fetchedAt = stale)

        val result = repository(offline).getStations()

        assertTrue(result.fromCache)
        assertEquals(stale, result.cacheTimestamp)
    }

    @Test
    fun getStations_fallsBackToCacheOnMalformedResponse() {
        repository(mustNotFetch).saveCache(listOf(Station(stationuuid = "uuid-1")), fetchedAt = NOW - 48 * HOUR)

        val result = repository({ "<html>502 Bad Gateway</html>" }).getStations()

        assertTrue(result.fromCache)
    }

    @Test(expected = NoStationsAvailable::class)
    fun getStations_throwsWhenApiFailsAndNoCache() {
        repository(offline).getStations()
    }
}

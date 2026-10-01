package io.github.drdtrn.radio.data

import org.json.JSONArray
import org.json.JSONException
import org.json.JSONObject
import java.io.File
import java.io.IOException
import java.net.HttpURLConnection
import java.net.URL

const val API_BASE = "https://all.api.radio-browser.info/json/stations/bycountrycodeexact"
const val USER_AGENT = "radio-tui-android/0.1"
const val CACHE_MAX_AGE_MILLIS = 24 * 60 * 60 * 1000L
private const val TIMEOUT_MILLIS = 10_000

/** Raised when stations can't be fetched and no local cache exists either. */
class NoStationsAvailable(message: String) : Exception(message)

/** Result of [StationRepository.getStations]: the station list plus where it came from. */
data class StationsResult(
    val stations: List<Station>,
    val fromCache: Boolean,
    val cacheTimestamp: Long?,
)

data class CachedStations(val stations: List<Station>, val fetchedAt: Long)

/** Fetches a URL's body as text. Swapped for a fake in tests. */
fun interface HttpGet {
    @Throws(IOException::class)
    fun get(url: String): String
}

object UrlConnectionHttpGet : HttpGet {
    override fun get(url: String): String {
        val connection = URL(url).openConnection() as HttpURLConnection
        try {
            connection.connectTimeout = TIMEOUT_MILLIS
            connection.readTimeout = TIMEOUT_MILLIS
            connection.setRequestProperty("User-Agent", USER_AGENT)
            val status = connection.responseCode
            if (status !in 200..299) throw IOException("HTTP $status from $url")
            return connection.inputStream.bufferedReader().use { it.readText() }
        } finally {
            connection.disconnect()
        }
    }
}

fun isStale(fetchedAt: Long, now: Long, maxAgeMillis: Long = CACHE_MAX_AGE_MILLIS): Boolean =
    now - fetchedAt > maxAgeMillis

/** Radio Browser API client with a local JSON cache. */
class StationRepository(
    private val cacheFile: File,
    private val countryCodes: List<String>,
    private val http: HttpGet = UrlConnectionHttpGet,
    private val clock: () -> Long = System::currentTimeMillis,
) {
    /** Fetch stations for every country from the Radio Browser API. */
    @Throws(IOException::class, JSONException::class)
    fun fetchStations(): List<Station> = countryCodes.flatMap { code ->
        val items = JSONArray(http.get("$API_BASE/$code"))
        List(items.length()) { Station.fromApiJson(items.getJSONObject(it)) }
    }

    /** Cached stations and their fetch time, or null if there's no usable cache. */
    fun loadCache(): CachedStations? {
        if (!cacheFile.exists()) return null
        return try {
            val payload = JSONObject(cacheFile.readText())
            val items = payload.getJSONArray("stations")
            CachedStations(
                stations = List(items.length()) { Station.fromCacheJson(items.getJSONObject(it)) },
                fetchedAt = payload.getLong("fetched_at"),
            )
        } catch (_: JSONException) {
            null // a truncated or corrupt cache is as good as none
        } catch (_: IOException) {
            null
        }
    }

    fun saveCache(stations: List<Station>, fetchedAt: Long) {
        cacheFile.parentFile?.mkdirs()
        val payload = JSONObject()
            .put("fetched_at", fetchedAt)
            .put("stations", JSONArray(stations.map { it.toCacheJson() }))
        // Write then rename, so a crash mid-write can't leave a half-written cache.
        val partial = File(cacheFile.path + ".tmp")
        partial.writeText(payload.toString())
        if (!partial.renameTo(cacheFile)) throw IOException("Could not replace $cacheFile")
    }

    /** Stations from a fresh cache, else the API, else a stale cache. */
    @Throws(NoStationsAvailable::class)
    fun getStations(forceRefresh: Boolean = false): StationsResult {
        val cached = loadCache()
        val now = clock()

        if (!forceRefresh && cached != null && !isStale(cached.fetchedAt, now)) {
            return StationsResult(cached.stations, fromCache = true, cacheTimestamp = cached.fetchedAt)
        }

        val stations = try {
            fetchStations()
        } catch (_: IOException) {
            return fallBackTo(cached)
        } catch (_: JSONException) {
            return fallBackTo(cached) // e.g. an HTML error page instead of JSON
        }

        try {
            saveCache(stations, now)
        } catch (_: IOException) {
            // Still show what we fetched; the next launch just refetches.
        }
        return StationsResult(stations, fromCache = false, cacheTimestamp = now)
    }

    private fun fallBackTo(cached: CachedStations?): StationsResult {
        if (cached == null) {
            throw NoStationsAvailable("Could not reach the Radio Browser API and no local cache exists.")
        }
        return StationsResult(cached.stations, fromCache = true, cacheTimestamp = cached.fetchedAt)
    }
}

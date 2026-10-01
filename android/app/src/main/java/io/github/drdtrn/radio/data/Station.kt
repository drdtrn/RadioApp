package io.github.drdtrn.radio.data

import org.json.JSONArray
import org.json.JSONObject

/** A single radio station, normalized from the Radio Browser API. */
data class Station(
    val stationuuid: String = "",
    val name: String = UNKNOWN_NAME,
    val url: String = "",
    val countrycode: String = "",
    val tags: List<String> = emptyList(),
    val language: String = "",
    val bitrate: Int = 0,
    /** The stream is HLS, which a URL without ".m3u8" doesn't reveal. */
    val hls: Boolean = false,
) {
    /**
     * True if [query] appears (case-insensitively) in the name or any tag.
     * A blank query matches every station.
     */
    fun matches(query: String): Boolean {
        val needle = query.trim().lowercase()
        if (needle.isEmpty()) return true
        return needle in name.lowercase() || tags.any { needle in it.lowercase() }
    }

    fun toCacheJson(): JSONObject = JSONObject()
        .put("stationuuid", stationuuid)
        .put("name", name)
        .put("url", url)
        .put("countrycode", countrycode)
        .put("tags", JSONArray(tags))
        .put("language", language)
        .put("bitrate", bitrate)
        .put("hls", hls)

    companion object {
        const val UNKNOWN_NAME = "Unknown station"

        /** Build a Station from one entry of the Radio Browser API response. */
        fun fromApiJson(data: JSONObject): Station = Station(
            stationuuid = data.string("stationuuid"),
            name = data.string("name").trim().ifEmpty { UNKNOWN_NAME },
            url = data.string("url_resolved").ifEmpty { data.string("url") },
            countrycode = data.string("countrycode"),
            tags = data.string("tags").split(",").map { it.trim() }.filter { it.isNotEmpty() },
            language = data.string("language"),
            bitrate = data.optInt("bitrate", 0),
            hls = data.optInt("hls", 0) != 0,
        )

        /** Rebuild a Station from a cached object (see [toCacheJson]). */
        fun fromCacheJson(data: JSONObject): Station {
            val tags = data.optJSONArray("tags") ?: JSONArray()
            return Station(
                stationuuid = data.getString("stationuuid"),
                name = data.getString("name"),
                url = data.getString("url"),
                countrycode = data.getString("countrycode"),
                tags = List(tags.length()) { tags.getString(it) },
                language = data.string("language"),
                bitrate = data.optInt("bitrate", 0),
                hls = data.optBoolean("hls", false),
            )
        }

        /**
         * The string at [key], or "" when it's missing or JSON null. Android's
         * optString() turns null into the text "null", so it can't be used
         * directly.
         */
        private fun JSONObject.string(key: String): String =
            if (isNull(key)) "" else optString(key)
    }
}

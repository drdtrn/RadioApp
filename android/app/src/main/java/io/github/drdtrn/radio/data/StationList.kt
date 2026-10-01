package io.github.drdtrn.radio.data

enum class SortOrder { NAME, BITRATE }

/**
 * The stations to list for one country tab: matching [query], in [order]
 * (names A–Z, or highest bitrate first with names breaking ties).
 */
fun stationsFor(
    stations: List<Station>,
    countryCode: String,
    query: String,
    order: SortOrder,
): List<Station> {
    val byName = compareBy<Station> { it.name.lowercase() }
    val comparator = when (order) {
        SortOrder.NAME -> byName
        SortOrder.BITRATE -> compareByDescending<Station> { it.bitrate }.then(byName)
    }
    return stations
        .filter { it.countrycode == countryCode && it.matches(query) }
        // The list is keyed by stationuuid, which must be unique.
        .distinctBy { it.stationuuid }
        .sortedWith(comparator)
}

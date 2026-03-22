package com.arthamantri.android.core

import android.content.Context
import android.content.Intent
import android.net.Uri
import java.net.URI

data class LinkContextSignals(
    val rawUrl: String,
    val linkClicked: Boolean,
    val linkScheme: String? = null,
    val urlHost: String? = null,
    val resolvedDomain: String? = null,
)

data class RecentLinkContextSnapshot(
    val signals: LinkContextSignals,
    val sourceApp: String? = null,
    val capturedAtMs: Long,
)

object LinkContextSignalExtractor {
    private val httpUrlRegex = Regex("""https?://\S+""", RegexOption.IGNORE_CASE)
    private val upiDeepLinkRegex = Regex("""upi://\S+""", RegexOption.IGNORE_CASE)
    private val trimTrailingChars = charArrayOf('.', ',', ';', ':', '!', '?', ')', ']', '}', '"', '\'')
    private val registrableSecondLevelSuffixes = setOf(
        "co.in",
        "co.uk",
        "com.au",
        "com.br",
        "com.sg",
        "co.za",
    )

    fun fromText(text: String, linkClicked: Boolean = false): LinkContextSignals? {
        val candidates = listOfNotNull(
            upiDeepLinkRegex.find(text)?.value,
            httpUrlRegex.find(text)?.value,
        )
        val earliest = candidates.minByOrNull { text.indexOf(it) } ?: return null
        return fromRawUrl(earliest.trimEnd(*trimTrailingChars), linkClicked = linkClicked)
    }

    fun fromIntent(intent: Intent?): LinkContextSignals? {
        if (intent?.action != Intent.ACTION_VIEW) {
            return null
        }
        return fromUri(intent.data, linkClicked = true)
    }

    fun fromUri(uri: Uri?, linkClicked: Boolean): LinkContextSignals? = fromRawUrl(uri?.toString(), linkClicked)

    fun fromRawUrl(rawUrl: String?, linkClicked: Boolean): LinkContextSignals? {
        val sanitized = rawUrl?.trim()?.trimEnd(*trimTrailingChars).orEmpty()
        if (sanitized.isBlank()) {
            return null
        }
        val uri = runCatching { URI(sanitized) }.getOrNull()
        val scheme = uri?.scheme?.lowercase()?.takeIf { it.isNotBlank() }
        val host = normalizeHost(uri?.host ?: uri?.authority ?: if (scheme == "upi") "pay" else null)
        return LinkContextSignals(
            rawUrl = sanitized,
            linkClicked = linkClicked,
            linkScheme = scheme,
            urlHost = host,
            resolvedDomain = resolveDomain(host),
        )
    }

    internal fun normalizeHost(host: String?): String? {
        val normalized = host
            ?.trim()
            ?.trim('.')
            ?.lowercase()
            ?.removePrefix("www.")
            ?.takeIf { it.isNotBlank() }
        return normalized
    }

    internal fun resolveDomain(host: String?): String? {
        val normalized = normalizeHost(host) ?: return null
        val labels = normalized.split('.').filter { it.isNotBlank() }
        if (labels.size <= 2) {
            return normalized
        }
        return if (registrableSecondLevelSuffixes.any { normalized.endsWith(".$it") } && labels.size >= 3) {
            labels.takeLast(3).joinToString(".")
        } else {
            labels.takeLast(2).joinToString(".")
        }
    }
}

object RecentLinkContextTracker {
    fun recordClick(
        context: Context,
        linkSignals: LinkContextSignals,
        sourceApp: String? = null,
        nowMs: Long = System.currentTimeMillis(),
    ) {
        context.getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE)
            .edit()
            .putString(AppConstants.Prefs.KEY_RECENT_LINK_URL, linkSignals.rawUrl)
            .putString(AppConstants.Prefs.KEY_RECENT_LINK_SCHEME, linkSignals.linkScheme)
            .putString(AppConstants.Prefs.KEY_RECENT_LINK_HOST, linkSignals.urlHost)
            .putString(AppConstants.Prefs.KEY_RECENT_LINK_RESOLVED_DOMAIN, linkSignals.resolvedDomain)
            .putString(AppConstants.Prefs.KEY_RECENT_LINK_SOURCE_APP, sourceApp)
            .putLong(AppConstants.Prefs.KEY_RECENT_LINK_CAPTURED_AT_MS, nowMs)
            .apply()
    }

    fun currentSnapshot(
        context: Context,
        nowMs: Long = System.currentTimeMillis(),
    ): RecentLinkContextSnapshot? {
        val prefs = context.getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE)
        val capturedAtMs = prefs.getLong(AppConstants.Prefs.KEY_RECENT_LINK_CAPTURED_AT_MS, 0L)
        if (capturedAtMs <= 0L || nowMs - capturedAtMs > AppConstants.Timing.RECENT_LINK_CONTEXT_WINDOW_MS) {
            return null
        }
        val rawUrl = prefs.getString(AppConstants.Prefs.KEY_RECENT_LINK_URL, null)?.takeIf { it.isNotBlank() } ?: return null
        return RecentLinkContextSnapshot(
            signals = LinkContextSignals(
                rawUrl = rawUrl,
                linkClicked = true,
                linkScheme = prefs.getString(AppConstants.Prefs.KEY_RECENT_LINK_SCHEME, null)?.takeIf { it.isNullOrBlank().not() },
                urlHost = prefs.getString(AppConstants.Prefs.KEY_RECENT_LINK_HOST, null)?.takeIf { it.isNullOrBlank().not() },
                resolvedDomain = prefs.getString(AppConstants.Prefs.KEY_RECENT_LINK_RESOLVED_DOMAIN, null)?.takeIf { it.isNullOrBlank().not() },
            ),
            sourceApp = prefs.getString(AppConstants.Prefs.KEY_RECENT_LINK_SOURCE_APP, null)?.takeIf { it.isNullOrBlank().not() },
            capturedAtMs = capturedAtMs,
        )
    }
}

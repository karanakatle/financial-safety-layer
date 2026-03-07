package com.arthamantri.android.notify

import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import android.util.Log
import com.arthamantri.android.R
import com.arthamantri.android.core.AppConstants
import com.arthamantri.android.repo.LiteracyRepository
import com.arthamantri.android.sms.SmsParser
import com.arthamantri.android.usage.UpiPackages
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch

class TransactionNotificationListenerService : NotificationListenerService() {
    private val serviceScope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private var lastFingerprint: String? = null
    private var lastProcessedAtMs: Long = 0L

    override fun onNotificationPosted(sbn: StatusBarNotification?) {
        if (sbn == null) {
            return
        }

        val pkg = sbn.packageName ?: return
        val extras = sbn.notification.extras
        val title = extras.getCharSequence(AppConstants.NotificationExtras.TITLE)?.toString().orEmpty()
        val text = extras.getCharSequence(AppConstants.NotificationExtras.TEXT)?.toString().orEmpty()
        val bigText = extras.getCharSequence(AppConstants.NotificationExtras.BIG_TEXT)?.toString().orEmpty()

        val payload = listOf(title, text, bigText)
            .filter { it.isNotBlank() }
            .joinToString(" ")
            .trim()

        if (payload.isBlank()) {
            return
        }

        if (!shouldInspect(pkg, payload)) {
            return
        }

        if (!isFresh(pkg, payload)) {
            return
        }

        val parsed = SmsParser.parseExpense(pkg, payload) ?: return
        val category = if (UpiPackages.isUpiPackage(this, pkg)) AppConstants.Domain.CATEGORY_UPI else parsed.category

        serviceScope.launch {
            try {
                val result = LiteracyRepository.sendSmsExpense(
                    context = this@TransactionNotificationListenerService,
                    amount = parsed.amount,
                    category = category,
                    note = "${AppConstants.Domain.NOTE_NOTIFICATION_PREFIX} $pkg",
                )

                result.alerts.forEach { alert ->
                    AlertNotifier.show(
                        context = this@TransactionNotificationListenerService,
                        title = getString(R.string.alert_title_default),
                        body = alert.message ?: getString(R.string.alert_txn_risk),
                        alertId = alert.alert_id,
                        pauseSeconds = alert.pause_seconds ?: 0,
                    )
                }
            } catch (e: Exception) {
                Log.e(
                    AppConstants.LogTags.TXN_NOTIFICATION_LISTENER,
                    AppConstants.LogMessages.TXN_NOTIFICATION_PROCESS_FAILED,
                    e,
                )
            }
        }
    }

    private fun shouldInspect(pkg: String, payload: String): Boolean {
        if (UpiPackages.isUpiPackage(this, pkg)) {
            return true
        }

        val lower = payload.lowercase()
        val hasTxnKeywords = AppConstants.Parsing.NOTIFICATION_TXN_KEYWORDS.any { lower.contains(it) }

        val hasMoneyMarker = AppConstants.Parsing.MONEY_MARKERS.any { lower.contains(it) }
        return hasTxnKeywords && hasMoneyMarker
    }

    private fun isFresh(pkg: String, payload: String): Boolean {
        val now = System.currentTimeMillis()
        val normalized = payload
            .replace(Regex(AppConstants.Parsing.NORMALIZE_WHITESPACE_REGEX), " ")
            .trim()
            .take(AppConstants.Parsing.DEDUPE_PAYLOAD_MAX_LENGTH)
        val fingerprint = "$pkg|$normalized"

        if (fingerprint == lastFingerprint && now - lastProcessedAtMs < AppConstants.Timing.NOTIFICATION_DEDUPE_WINDOW_MS) {
            return false
        }

        lastFingerprint = fingerprint
        lastProcessedAtMs = now
        return true
    }
}

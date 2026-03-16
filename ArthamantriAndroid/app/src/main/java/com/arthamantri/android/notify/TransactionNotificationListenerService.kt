package com.arthamantri.android.notify

import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import android.util.Log
import java.time.Instant
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
        if (AppConstants.Parsing.MESSAGING_APP_PACKAGES.contains(pkg)) {
            Log.i(
                AppConstants.LogTags.TXN_NOTIFICATION_LISTENER,
                "Skipping messaging-app notification to avoid duplicate SMS ingestion: $pkg",
            )
            return
        }
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

        val isUpiPackage = UpiPackages.isUpiPackage(this, pkg)
        val appName = UpiPackages.displayName(this, pkg)
        val paymentSignal = PaymentInspectionNotificationParser.parse(
            packageName = pkg,
            appName = appName,
            title = title,
            text = text,
            bigText = bigText,
            isUpiPackage = isUpiPackage,
        )
        val parsed = SmsParser.parseSignal(pkg, payload)
        val category = if (isUpiPackage) AppConstants.Domain.CATEGORY_UPI else parsed?.category

        serviceScope.launch {
            try {
                paymentSignal?.let { signal ->
                    val inspection = LiteracyRepository.inspectUpiRequest(
                        context = this@TransactionNotificationListenerService,
                        appName = signal.appName,
                        requestKind = signal.requestKind,
                        amount = signal.amount,
                        payeeLabel = signal.payeeLabel,
                        payeeHandle = signal.payeeHandle,
                        rawText = signal.rawText,
                        source = signal.source,
                        timestamp = Instant.ofEpochMilli(sbn.postTime).toString(),
                    )
                    val warningShown = PaymentInspectionAlertPresenter.maybeShow(
                        context = this@TransactionNotificationListenerService,
                        inspection = inspection,
                        requestKind = signal.requestKind,
                        amount = signal.amount,
                        payeeLabel = signal.payeeLabel,
                        payeeHandle = signal.payeeHandle,
                        rawText = signal.rawText,
                    )
                    if (warningShown) {
                        return@launch
                    }
                }

                if (parsed == null || category == null) {
                    return@launch
                }

                val result = LiteracyRepository.sendSmsSignal(
                    context = this@TransactionNotificationListenerService,
                    signalType = parsed.signalType,
                    confidence = parsed.confidence,
                    amount = parsed.amount,
                    category = category,
                    note = "${AppConstants.Domain.NOTE_NOTIFICATION_PREFIX} $pkg",
                    timestamp = Instant.ofEpochMilli(sbn.postTime).toString(),
                )

                result.alerts.forEach { alert ->
                    AlertNotifier.show(
                        context = this@TransactionNotificationListenerService,
                        title = getString(R.string.alert_title_default),
                        body = alert.message ?: getString(R.string.alert_txn_risk),
                        alertId = alert.alert_id,
                        severity = alert.severity ?: "medium",
                        pauseSeconds = alert.pause_seconds ?: 0,
                        whyThisAlert = alert.why_this_alert,
                        nextSafeAction = alert.next_best_action,
                        essentialGoalImpact = alert.essential_goal_impact,
                        alertFamily = AppConstants.Domain.ALERT_FAMILY_CASHFLOW,
                        showUsefulnessFeedback = true,
                    )
                }
            } catch (e: Exception) {
                val localFallbackShown = paymentSignal?.let { signal ->
                    PaymentInspectionAlertPresenter.showLocalFallback(
                        context = this@TransactionNotificationListenerService,
                        requestKind = signal.requestKind,
                        amount = signal.amount,
                        payeeLabel = signal.payeeLabel,
                        payeeHandle = signal.payeeHandle,
                        rawText = signal.rawText,
                    )
                } ?: false
                Log.e(
                    AppConstants.LogTags.TXN_NOTIFICATION_LISTENER,
                    if (localFallbackShown) {
                        "${AppConstants.LogMessages.TXN_NOTIFICATION_PROCESS_FAILED} - fallback_shown"
                    } else {
                        AppConstants.LogMessages.TXN_NOTIFICATION_PROCESS_FAILED
                    },
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

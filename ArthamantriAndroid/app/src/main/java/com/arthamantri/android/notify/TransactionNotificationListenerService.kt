package com.arthamantri.android.notify

import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import android.util.Log
import java.time.Instant
import com.arthamantri.android.R
import com.arthamantri.android.core.AppConstants
import com.arthamantri.android.core.DebugObservability
import com.arthamantri.android.core.LinkContextSignalExtractor
import com.arthamantri.android.core.LinkContextSignals
import com.arthamantri.android.core.RecentLinkContextTracker
import com.arthamantri.android.core.StructuredMessageSignalExtractor
import com.arthamantri.android.repo.LiteracyRepository
import com.arthamantri.android.sms.SmsParser
import com.arthamantri.android.usage.PaymentAppSetupStateTracker
import com.arthamantri.android.usage.PaymentAppSetupState
import com.arthamantri.android.usage.UpiPackages
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.launch
import java.util.UUID

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

        if (!isFresh(pkg, payload)) {
            return
        }

        val isUpiPackage = UpiPackages.isUpiPackage(this, pkg)
        val appName = UpiPackages.displayName(this, pkg)
        val signals = StructuredMessageSignalExtractor.extract(payload)
        val suppressionReason = StructuredMessageSignalExtractor.suppressionReason(signals)
        val shouldInspect = shouldInspect(pkg, payload, signals)
        val correlationId = UUID.randomUUID().toString()
        val setupState = PaymentAppSetupStateTracker.currentSnapshot(this).state
        val paymentSignal = PaymentInspectionNotificationParser.parse(
            packageName = pkg,
            appName = appName,
            title = title,
            text = text,
            bigText = bigText,
            isUpiPackage = isUpiPackage,
            setupState = setupState,
        )
        val parsed = SmsParser.parseSignal(pkg, payload, setupState = setupState)
        val category = if (isUpiPackage) AppConstants.Domain.CATEGORY_UPI else parsed?.category
        val messageLinkContext = LinkContextSignalExtractor.fromText(payload, linkClicked = false)
        val recentLinkContext = RecentLinkContextTracker.currentSnapshot(this, nowMs = sbn.postTime)
        val effectiveLinkContext = recentLinkContext?.signals ?: messageLinkContext
        val shouldCreateAccessCandidate = signals.isSensitiveAccessSignal ||
            (signals.isOtpVerification && recentLinkContext != null)

        serviceScope.launch {
            try {
                DebugObservability.trace(
                    context = this@TransactionNotificationListenerService,
                    tag = AppConstants.LogTags.TXN_NOTIFICATION_LISTENER,
                    event = "notification_received",
                    fields = mapOf(
                        "package" to pkg,
                        "app_name" to appName,
                        "title" to title,
                        "setup_state_before" to setupState.wireValue,
                        "correlation_id" to correlationId,
                    ),
                )

                LiteracyRepository.submitContextEvent(
                    context = this@TransactionNotificationListenerService,
                    eventType = AppConstants.ContextEvents.EVENT_NOTIFICATION_OBSERVED,
                    sourceApp = pkg,
                    targetApp = appName,
                    correlationId = correlationId,
                    classification = if (suppressionReason != null || !shouldInspect) {
                        AppConstants.ContextEvents.CLASSIFICATION_SUPPRESSED
                    } else {
                        AppConstants.ContextEvents.CLASSIFICATION_OBSERVED
                    },
                    suppressionReason = suppressionReason ?: if (!shouldInspect) "not_actionable_notification" else null,
                    messageFamily = StructuredMessageSignalExtractor.messageFamily(signals),
                    amount = paymentSignal?.amount ?: parsed?.amount,
                    hasOtp = signals.hasOtpCode,
                    hasUpiHandle = signals.hasUpiHandle,
                    hasUpiDeepLink = signals.hasUpiDeepLink,
                    hasUrl = signals.hasUrl,
                    linkClicked = effectiveLinkContext?.linkClicked,
                    linkScheme = effectiveLinkContext?.linkScheme,
                    urlHost = effectiveLinkContext?.urlHost,
                    resolvedDomain = effectiveLinkContext?.resolvedDomain,
                    metadata = buildLinkContextMetadata(
                        source = AppConstants.PaymentInspection.SOURCE_NOTIFICATION,
                        postedAt = Instant.ofEpochMilli(sbn.postTime).toString(),
                        isUpiPackage = isUpiPackage,
                        linkSignals = effectiveLinkContext,
                        recentLinkCapturedAtMs = recentLinkContext?.capturedAtMs,
                    ),
                )

                DebugObservability.trace(
                    context = this@TransactionNotificationListenerService,
                    tag = AppConstants.LogTags.TXN_NOTIFICATION_LISTENER,
                    event = "notification_classified",
                    fields = mapOf(
                        "package" to pkg,
                        "message_family" to StructuredMessageSignalExtractor.messageFamily(signals),
                        "suppression_reason" to (suppressionReason ?: if (!shouldInspect) "not_actionable_notification" else null),
                        "should_inspect" to shouldInspect.toString(),
                        "is_upi_package" to isUpiPackage.toString(),
                        "has_strong_payment_signal" to signals.hasStrongPaymentSignal.toString(),
                        "has_otp" to signals.hasOtpCode.toString(),
                        "has_url" to signals.hasUrl.toString(),
                        "setup_state_before" to setupState.wireValue,
                        "correlation_id" to correlationId,
                    ),
                )

                if (shouldCreateAccessCandidate) {
                    LiteracyRepository.submitContextEvent(
                        context = this@TransactionNotificationListenerService,
                        eventType = AppConstants.ContextEvents.EVENT_ACCOUNT_ACCESS_CANDIDATE,
                        sourceApp = pkg,
                        targetApp = appName,
                        correlationId = correlationId,
                        classification = AppConstants.ContextEvents.CLASSIFICATION_ACCOUNT_ACCESS_CANDIDATE,
                        suppressionReason = suppressionReason,
                        messageFamily = StructuredMessageSignalExtractor.messageFamily(signals),
                        amount = paymentSignal?.amount ?: parsed?.amount,
                        hasOtp = signals.hasOtpCode,
                        hasUpiHandle = signals.hasUpiHandle,
                        hasUpiDeepLink = signals.hasUpiDeepLink,
                        hasUrl = signals.hasUrl,
                        linkClicked = effectiveLinkContext?.linkClicked,
                        linkScheme = effectiveLinkContext?.linkScheme,
                        urlHost = effectiveLinkContext?.urlHost,
                        resolvedDomain = effectiveLinkContext?.resolvedDomain,
                        metadata = buildLinkContextMetadata(
                            source = AppConstants.PaymentInspection.SOURCE_NOTIFICATION,
                            postedAt = Instant.ofEpochMilli(sbn.postTime).toString(),
                            isUpiPackage = isUpiPackage,
                            linkSignals = effectiveLinkContext,
                            recentLinkCapturedAtMs = recentLinkContext?.capturedAtMs,
                        ),
                    )
                }

                val setupTransition = PaymentAppSetupStateTracker.onStructuredMessage(
                    context = this@TransactionNotificationListenerService,
                    sourceApp = pkg,
                    targetApp = appName,
                    rawText = payload,
                    signals = signals,
                    correlationId = correlationId,
                    nowMs = sbn.postTime,
                )

                setupTransition?.let { transition ->
                    DebugObservability.trace(
                        context = this@TransactionNotificationListenerService,
                        tag = AppConstants.LogTags.TXN_NOTIFICATION_LISTENER,
                        event = "notification_setup_transition",
                        fields = mapOf(
                            "package" to pkg,
                            "previous_state" to transition.previous.state.wireValue,
                            "current_state" to transition.current.state.wireValue,
                            "transition_signal" to transition.signal.wireValue,
                            "correlation_id" to correlationId,
                        ),
                    )
                }

                if (!shouldInspect) {
                    DebugObservability.trace(
                        context = this@TransactionNotificationListenerService,
                        tag = AppConstants.LogTags.TXN_NOTIFICATION_LISTENER,
                        event = "notification_suppressed",
                        fields = mapOf(
                            "package" to pkg,
                            "message_family" to StructuredMessageSignalExtractor.messageFamily(signals),
                            "suppression_reason" to (suppressionReason ?: "not_actionable_notification"),
                            "setup_state_after" to PaymentAppSetupStateTracker.currentSnapshot(this@TransactionNotificationListenerService).state.wireValue,
                            "correlation_id" to correlationId,
                        ),
                    )
                    return@launch
                }

                paymentSignal?.let { signal ->
                    DebugObservability.trace(
                        context = this@TransactionNotificationListenerService,
                        tag = AppConstants.LogTags.TXN_NOTIFICATION_LISTENER,
                        event = "notification_payment_candidate",
                        fields = mapOf(
                            "package" to pkg,
                            "request_kind" to signal.requestKind,
                            "amount" to signal.amount?.toString(),
                            "payee_label" to signal.payeeLabel,
                            "payee_handle" to signal.payeeHandle,
                            "setup_state_before" to setupState.wireValue,
                            "correlation_id" to correlationId,
                        ),
                    )
                    LiteracyRepository.submitContextEvent(
                        context = this@TransactionNotificationListenerService,
                        eventType = AppConstants.ContextEvents.EVENT_PAYMENT_CANDIDATE,
                        sourceApp = pkg,
                        targetApp = signal.appName,
                        correlationId = correlationId,
                        classification = AppConstants.ContextEvents.CLASSIFICATION_PAYMENT_CANDIDATE,
                        messageFamily = StructuredMessageSignalExtractor.messageFamily(signals),
                        amount = signal.amount,
                        hasOtp = signals.hasOtpCode,
                        hasUpiHandle = signals.hasUpiHandle,
                        hasUpiDeepLink = signals.hasUpiDeepLink,
                        hasUrl = signals.hasUrl,
                        linkClicked = effectiveLinkContext?.linkClicked,
                        linkScheme = effectiveLinkContext?.linkScheme,
                        urlHost = effectiveLinkContext?.urlHost,
                        resolvedDomain = effectiveLinkContext?.resolvedDomain,
                        metadata = buildLinkContextMetadata(
                            source = signal.source,
                            postedAt = Instant.ofEpochMilli(sbn.postTime).toString(),
                            isUpiPackage = isUpiPackage,
                            linkSignals = effectiveLinkContext,
                            recentLinkCapturedAtMs = recentLinkContext?.capturedAtMs,
                            extra = mapOf("request_kind" to signal.requestKind),
                        ),
                    )
                }

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
                        setupState = setupState.wireValue,
                        linkClicked = effectiveLinkContext?.linkClicked,
                        linkScheme = effectiveLinkContext?.linkScheme,
                        urlHost = effectiveLinkContext?.urlHost,
                        resolvedDomain = effectiveLinkContext?.resolvedDomain,
                        timestamp = Instant.ofEpochMilli(sbn.postTime).toString(),
                    )
                    DebugObservability.trace(
                        context = this@TransactionNotificationListenerService,
                        tag = AppConstants.LogTags.TXN_NOTIFICATION_LISTENER,
                        event = "notification_inspection_result",
                        fields = mapOf(
                            "package" to pkg,
                            "classification" to inspection.classification,
                            "scenario" to inspection.scenario,
                            "should_warn" to inspection.should_warn.toString(),
                            "alert_id" to inspection.alert_id,
                            "setup_state_before" to setupState.wireValue,
                            "setup_state_after" to PaymentAppSetupStateTracker.currentSnapshot(this@TransactionNotificationListenerService).state.wireValue,
                            "correlation_id" to correlationId,
                        ),
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
                    DebugObservability.trace(
                        context = this@TransactionNotificationListenerService,
                        tag = AppConstants.LogTags.TXN_NOTIFICATION_LISTENER,
                        event = "notification_warning_decision",
                        fields = mapOf(
                            "package" to pkg,
                            "warning_shown" to warningShown.toString(),
                            "alert_id" to inspection.alert_id,
                            "classification" to inspection.classification,
                            "scenario" to inspection.scenario,
                            "correlation_id" to correlationId,
                        ),
                    )
                    if (warningShown) {
                        return@launch
                    }
                }

                if (parsed == null || category == null) {
                    DebugObservability.trace(
                        context = this@TransactionNotificationListenerService,
                        tag = AppConstants.LogTags.TXN_NOTIFICATION_LISTENER,
                        event = "notification_no_cashflow_parse",
                        fields = mapOf(
                            "package" to pkg,
                            "category" to category,
                            "message_family" to StructuredMessageSignalExtractor.messageFamily(signals),
                            "correlation_id" to correlationId,
                        ),
                    )
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
                DebugObservability.trace(
                    context = this@TransactionNotificationListenerService,
                    tag = AppConstants.LogTags.TXN_NOTIFICATION_LISTENER,
                    event = "notification_cashflow_result",
                    fields = mapOf(
                        "package" to pkg,
                        "signal_type" to parsed.signalType,
                        "confidence" to parsed.confidence,
                        "amount" to parsed.amount?.toString(),
                        "category" to category,
                        "alerts_count" to result.alerts.size.toString(),
                        "participant_id" to result.participantId,
                        "correlation_id" to correlationId,
                    ),
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
                DebugObservability.trace(
                    context = this@TransactionNotificationListenerService,
                    tag = AppConstants.LogTags.TXN_NOTIFICATION_LISTENER,
                    event = "notification_processing_error",
                    fields = mapOf(
                        "package" to pkg,
                        "fallback_shown" to localFallbackShown.toString(),
                        "error" to e::class.java.simpleName,
                        "correlation_id" to correlationId,
                    ),
                )
            }
        }
    }

    private fun shouldInspect(pkg: String, payload: String, signals: com.arthamantri.android.core.StructuredMessageSignals): Boolean {
        if (
            signals.isCallMetadata ||
            signals.isSetupOrRegistration ||
            signals.isOtpVerification ||
            signals.isReceiveOnly ||
            signals.isPostTransactionConfirmation ||
            signals.isStatementOrReport ||
            signals.isEmiStatus ||
            signals.isPortfolioInfo ||
            signals.isMarketingOrProductStatus ||
            signals.isSensitiveAccessSignal
        ) {
            return false
        }

        if (UpiPackages.isUpiPackage(this, pkg)) {
            if (signals.hasStrongPaymentSignal) {
                return true
            }
        }

        val lower = payload.lowercase()
        val hasTxnKeywords = AppConstants.Parsing.NOTIFICATION_TXN_KEYWORDS.any { lower.contains(it) }
        val hasMoneyMarker = AppConstants.Parsing.MONEY_MARKERS.any { lower.contains(it) }
        return hasTxnKeywords && hasMoneyMarker
    }

    private fun buildLinkContextMetadata(
        source: String,
        postedAt: String,
        isUpiPackage: Boolean,
        linkSignals: LinkContextSignals?,
        recentLinkCapturedAtMs: Long?,
        extra: Map<String, String> = emptyMap(),
    ): Map<String, String> = buildMap {
        put("source", source)
        put("posted_at", postedAt)
        put("is_upi_package", isUpiPackage.toString())
        putAll(extra)
        linkSignals?.let {
            put("raw_url", it.rawUrl)
            put("link_context_source", if (it.linkClicked) "recent_click" else "message_text")
        }
        recentLinkCapturedAtMs?.let {
            put("link_age_ms", (System.currentTimeMillis() - it).toString())
        }
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

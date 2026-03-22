package com.arthamantri.android.sms

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.provider.Telephony
import android.util.Log
import com.arthamantri.android.R
import com.arthamantri.android.config.AppConfig
import com.arthamantri.android.core.AppConstants
import com.arthamantri.android.core.LinkContextSignalExtractor
import com.arthamantri.android.core.LinkContextSignals
import com.arthamantri.android.core.RecentLinkContextTracker
import com.arthamantri.android.core.StructuredMessageSignalExtractor
import com.arthamantri.android.notify.AlertNotifier
import com.arthamantri.android.repo.LiteracyRepository
import com.arthamantri.android.usage.PaymentAppSetupStateTracker
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import java.time.Instant
import java.util.UUID

class BankSmsReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (Telephony.Sms.Intents.SMS_RECEIVED_ACTION != intent.action) {
            return
        }

        Log.i(AppConstants.LogTags.BANK_SMS_RECEIVER, "SMS_RECEIVED broadcast received")
        val messages = Telephony.Sms.Intents.getMessagesFromIntent(intent)
        if (messages.isEmpty()) {
            Log.w(AppConstants.LogTags.BANK_SMS_RECEIVER, "SMS_RECEIVED had no message parts")
            return
        }

        val sender = messages[0].originatingAddress
        val body = messages.joinToString(separator = "") { it.messageBody ?: "" }
        Log.i(
            AppConstants.LogTags.BANK_SMS_RECEIVER,
            "Incoming SMS sender=$sender body='${body.take(180)}'"
        )

        val signals = StructuredMessageSignalExtractor.extract(body)
        val messageFamily = StructuredMessageSignalExtractor.messageFamily(signals)
        val suppressionReason = StructuredMessageSignalExtractor.suppressionReason(signals)
        val setupState = PaymentAppSetupStateTracker.currentSnapshot(context).state
        val parsed = SmsParser.parseSignal(sender, body, setupState = setupState)
        val messageLinkContext = LinkContextSignalExtractor.fromText(body, linkClicked = false)
        val recentLinkContext = RecentLinkContextTracker.currentSnapshot(context)
        val effectiveLinkContext = recentLinkContext?.signals ?: messageLinkContext
        val shouldTrackContext =
            parsed != null || suppressionReason != null || signals.isSensitiveAccessSignal || signals.hasStrongPaymentSignal || signals.hasUrl
        val correlationId = UUID.randomUUID().toString()
        val shouldCreateAccessCandidate = signals.isSensitiveAccessSignal ||
            (signals.isOtpVerification && recentLinkContext != null)

        CoroutineScope(Dispatchers.IO).launch {
            try {
                if (shouldTrackContext) {
                    LiteracyRepository.submitContextEvent(
                        context = context,
                        eventType = AppConstants.ContextEvents.EVENT_SMS_OBSERVED,
                        sourceApp = sender,
                        correlationId = correlationId,
                        classification = if (suppressionReason != null) {
                            AppConstants.ContextEvents.CLASSIFICATION_SUPPRESSED
                        } else {
                            AppConstants.ContextEvents.CLASSIFICATION_OBSERVED
                        },
                        suppressionReason = suppressionReason,
                        messageFamily = messageFamily,
                        amount = parsed?.amount,
                        hasOtp = signals.hasOtpCode,
                        hasUpiHandle = signals.hasUpiHandle,
                        hasUpiDeepLink = signals.hasUpiDeepLink,
                        hasUrl = signals.hasUrl,
                        linkClicked = effectiveLinkContext?.linkClicked,
                        linkScheme = effectiveLinkContext?.linkScheme,
                        urlHost = effectiveLinkContext?.urlHost,
                        resolvedDomain = effectiveLinkContext?.resolvedDomain,
                        metadata = buildLinkContextMetadata(
                            source = "sms",
                            linkSignals = effectiveLinkContext,
                            recentLinkCapturedAtMs = recentLinkContext?.capturedAtMs,
                        ),
                    )
                }

                if (shouldCreateAccessCandidate) {
                    LiteracyRepository.submitContextEvent(
                        context = context,
                        eventType = AppConstants.ContextEvents.EVENT_ACCOUNT_ACCESS_CANDIDATE,
                        sourceApp = sender,
                        correlationId = correlationId,
                        classification = AppConstants.ContextEvents.CLASSIFICATION_ACCOUNT_ACCESS_CANDIDATE,
                        suppressionReason = suppressionReason,
                        messageFamily = messageFamily,
                        amount = parsed?.amount,
                        hasOtp = signals.hasOtpCode,
                        hasUpiHandle = signals.hasUpiHandle,
                        hasUpiDeepLink = signals.hasUpiDeepLink,
                        hasUrl = signals.hasUrl,
                        linkClicked = effectiveLinkContext?.linkClicked,
                        linkScheme = effectiveLinkContext?.linkScheme,
                        urlHost = effectiveLinkContext?.urlHost,
                        resolvedDomain = effectiveLinkContext?.resolvedDomain,
                        metadata = buildLinkContextMetadata(
                            source = "sms",
                            linkSignals = effectiveLinkContext,
                            recentLinkCapturedAtMs = recentLinkContext?.capturedAtMs,
                        ),
                    )
                }

                PaymentAppSetupStateTracker.onStructuredMessage(
                    context = context,
                    sourceApp = sender,
                    targetApp = null,
                    rawText = body,
                    signals = signals,
                    correlationId = correlationId,
                    nowMs = messages[0].timestampMillis,
                )

                if (parsed == null) {
                    Log.w(
                        AppConstants.LogTags.BANK_SMS_RECEIVER,
                        "SMS ignored: parser did not detect financial signal pattern"
                    )
                    return@launch
                }

                Log.i(
                    AppConstants.LogTags.BANK_SMS_RECEIVER,
                    "Parsed SMS signal type=${parsed.signalType} confidence=${parsed.confidence} amount=${parsed.amount} category=${parsed.category} baseUrl=${AppConfig.getBaseUrl(context)}"
                )

                val result = LiteracyRepository.sendSmsSignal(
                    context = context,
                    signalType = parsed.signalType,
                    confidence = parsed.confidence,
                    amount = parsed.amount,
                    category = parsed.category,
                    note = parsed.note,
                    timestamp = Instant.ofEpochMilli(messages[0].timestampMillis).toString(),
                )
                Log.i(
                    AppConstants.LogTags.BANK_SMS_RECEIVER,
                    "sms-ingest API success; participantId=${result.participantId}; alertsCount=${result.alerts.size}"
                )

                if (result.alerts.isEmpty() && parsed.signalType == AppConstants.Domain.SMS_SIGNAL_PARTIAL) {
                    showLocalFallback(
                        context = context,
                        parsed = parsed,
                        telemetryReason = "partial_context",
                    )
                }

                result.alerts.forEach { alert ->
                    AlertNotifier.show(
                        context,
                        title = context.getString(R.string.alert_title_default),
                        body = alert.message ?: context.getString(R.string.alert_spending_threshold),
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
                Log.e(
                    AppConstants.LogTags.BANK_SMS_RECEIVER,
                    AppConstants.LogMessages.BANK_SMS_PROCESS_FAILED,
                    e,
                )
                parsed?.let {
                    showLocalFallback(
                        context = context,
                        parsed = it,
                        telemetryReason = "network_unavailable",
                    )
                }
            }
        }
    }

    private suspend fun showLocalFallback(
        context: Context,
        parsed: ParsedSmsSignal,
        telemetryReason: String,
    ) {
        val guidance = CashflowFallbackGuidanceBuilder.build(
            context = context,
            signalType = parsed.signalType,
            amount = parsed.amount,
        ) ?: return
        val alertId = "${AppConstants.Domain.LOCAL_FALLBACK_ALERT_PREFIX}-${UUID.randomUUID()}"

        AlertNotifier.show(
            context = context,
            title = context.getString(R.string.alert_title_default),
            body = guidance.body,
            alertId = alertId,
            severity = "soft",
            whyThisAlert = guidance.whyThisAlert,
            nextSafeAction = guidance.nextSafeAction,
            alertFamily = AppConstants.Domain.ALERT_FAMILY_CASHFLOW,
            showUsefulnessFeedback = true,
        )

        LiteracyRepository.submitAppLog(
            context = context,
            level = AppConstants.Domain.APP_LOG_LEVEL_WARN,
            message = listOf(
                "cashflow_fallback_shown",
                alertId,
                telemetryReason,
                parsed.signalType,
                parsed.amount?.toString() ?: "unknown",
            ).joinToString(":"),
            language = LiteracyRepository.language(context),
            participantId = LiteracyRepository.participantId(context),
        )
    }

    private fun buildLinkContextMetadata(
        source: String,
        linkSignals: LinkContextSignals?,
        recentLinkCapturedAtMs: Long?,
    ): Map<String, String> = buildMap {
        put("source", source)
        linkSignals?.let {
            put("raw_url", it.rawUrl)
            put("link_context_source", if (it.linkClicked) "recent_click" else "message_text")
        }
        recentLinkCapturedAtMs?.let {
            put("link_age_ms", (System.currentTimeMillis() - it).toString())
        }
    }
}

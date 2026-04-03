package com.arthamantri.android.repo

import android.content.Context
import android.provider.Settings
import com.arthamantri.android.api.ApiClient
import com.arthamantri.android.core.AppConstants
import com.arthamantri.android.core.RecentLinkContextTracker
import com.arthamantri.android.model.LiteracyAlert
import com.arthamantri.android.model.LiteracyAlertFeedbackRequest
import com.arthamantri.android.model.LiteracyState
import com.arthamantri.android.model.PilotContextEvent
import com.arthamantri.android.model.PilotAppLogRequest
import com.arthamantri.android.model.PilotConsentRequest
import com.arthamantri.android.model.PilotFeedbackRequest
import com.arthamantri.android.model.PilotMetaResponse
import com.arthamantri.android.model.EssentialGoalProfileRequest
import com.arthamantri.android.model.EssentialGoalProfileResponse
import com.arthamantri.android.model.ExperimentAssignmentRequest
import com.arthamantri.android.model.SmsIngestRequest
import com.arthamantri.android.model.UpiRequestInspectRequest
import com.arthamantri.android.model.UpiRequestInspectResponse
import com.arthamantri.android.model.UpiOpenRequest
import java.time.Instant
import java.util.UUID
import com.arthamantri.android.usage.PaymentAppSetupStateTracker

object LiteracyRepository {
    data class SmsSendResult(
        val alerts: List<LiteracyAlert>,
        val state: LiteracyState?,
        val participantId: String?,
    )

    data class DeliveryResult(
        val delivered: Boolean,
        val queued: Boolean,
        val flushedCount: Int = 0,
    )

    suspend fun sendSmsSignal(
        context: Context,
        signalType: String,
        confidence: String,
        amount: Double?,
        category: String,
        note: String,
        timestamp: String? = null,
    ): SmsSendResult {
        val participantId = resolveParticipantId(context)
        val language = resolveLanguage(context)
        val api = ApiClient.literacyApi(context)
        val response = api.smsIngest(
            SmsIngestRequest(
                participant_id = participantId,
                language = language,
                signal_type = signalType,
                signal_confidence = confidence,
                amount = amount,
                category = category,
                note = note,
                timestamp = timestamp,
            )
        )
        flushQueuedTelemetry(context)
        return SmsSendResult(
            alerts = response.literacy_alerts,
            state = response.literacy_state,
            participantId = response.participant_id ?: participantId,
        )
    }

    suspend fun notifyUpiOpen(
        context: Context,
        appName: String,
        intentAmount: Double = 0.0,
    ): LiteracyAlert? {
        val participantId = resolveParticipantId(context)
        val language = resolveLanguage(context)
        val api = ApiClient.literacyApi(context)
        val alert = api.upiOpen(
            UpiOpenRequest(
                participant_id = participantId,
                language = language,
                app_name = appName,
                intent_amount = intentAmount,
            )
        ).alert
        flushQueuedTelemetry(context)
        return alert
    }

    suspend fun inspectUpiRequest(
        context: Context,
        appName: String = "",
        requestKind: String = AppConstants.PaymentInspection.REQUEST_KIND_UNKNOWN,
        amount: Double? = null,
        payeeLabel: String = "",
        payeeHandle: String = "",
        rawText: String = "",
        source: String = AppConstants.PaymentInspection.SOURCE_FOREGROUND_APP,
        setupState: String? = PaymentAppSetupStateTracker.currentSnapshot(context).state.wireValue,
        linkClicked: Boolean? = null,
        linkScheme: String? = null,
        urlHost: String? = null,
        resolvedDomain: String? = null,
        domainClass: String? = null,
        timestamp: String? = null,
    ): UpiRequestInspectResponse {
        val participantId = resolveParticipantId(context)
        val language = resolveLanguage(context)
        val api = ApiClient.literacyApi(context)
        val recentLinkContext = RecentLinkContextTracker.currentSnapshot(context)?.signals
        val response = api.upiRequestInspect(
            UpiRequestInspectRequest(
                participant_id = participantId,
                language = language,
                app_name = appName,
                request_kind = requestKind.ifBlank { AppConstants.PaymentInspection.REQUEST_KIND_UNKNOWN },
                amount = amount,
                payee_label = payeeLabel,
                payee_handle = payeeHandle,
                raw_text = rawText,
                source = source,
                setup_state = setupState,
                link_clicked = linkClicked ?: recentLinkContext?.linkClicked,
                link_scheme = linkScheme ?: recentLinkContext?.linkScheme,
                url_host = urlHost ?: recentLinkContext?.urlHost,
                resolved_domain = resolvedDomain ?: recentLinkContext?.resolvedDomain,
                domain_class = domainClass,
                timestamp = timestamp,
            )
        )
        flushQueuedTelemetry(context)
        return response
    }

    suspend fun status(context: Context): LiteracyState {
        return ApiClient.literacyApi(context).status(resolveParticipantId(context))
    }

    suspend fun pilotMeta(context: Context): PilotMetaResponse {
        return ApiClient.literacyApi(context).pilotMeta(resolveLanguage(context))
    }

    suspend fun submitPilotConsent(
        context: Context,
        participantId: String,
        accepted: Boolean,
        language: String = AppConstants.Locale.DEFAULT_LANGUAGE,
    ): Boolean {
        return ApiClient.literacyApi(context).pilotConsent(
            PilotConsentRequest(
                participant_id = participantId,
                accepted = accepted,
                language = language,
            )
        ).ok
    }

    suspend fun submitPilotFeedback(
        context: Context,
        participantId: String,
        rating: Int,
        comment: String,
        language: String = AppConstants.Locale.DEFAULT_LANGUAGE,
    ): Boolean {
        return ApiClient.literacyApi(context).pilotFeedback(
            PilotFeedbackRequest(
                participant_id = participantId,
                rating = rating,
                comment = comment,
                language = language,
            )
        ).ok
    }

    suspend fun submitAppLog(
        context: Context,
        participantId: String = resolveParticipantId(context),
        level: String,
        message: String,
        language: String = AppConstants.Locale.DEFAULT_LANGUAGE,
        contextEvent: PilotContextEvent? = null,
    ): DeliveryResult {
        val request = PilotAppLogRequest(
                event_id = UUID.randomUUID().toString(),
                participant_id = participantId,
                level = level,
                message = message,
                language = language,
                timestamp = currentTimestamp(),
                context_event = contextEvent,
            )
        return runCatching {
            val ok = ApiClient.literacyApi(context).pilotAppLog(request).ok
            if (ok) {
                DeliveryResult(delivered = true, queued = false, flushedCount = flushQueuedTelemetry(context))
            } else {
                OfflineTelemetryQueue.enqueueAppLog(context, request)
                DeliveryResult(delivered = false, queued = true)
            }
        }.getOrElse {
            OfflineTelemetryQueue.enqueueAppLog(context, request)
            DeliveryResult(delivered = false, queued = true)
        }
    }

    suspend fun submitContextEvent(
        context: Context,
        eventType: String,
        sourceApp: String? = null,
        targetApp: String? = null,
        correlationId: String? = null,
        classification: String? = null,
        setupState: String? = AppConstants.ContextEvents.SETUP_STATE_UNKNOWN,
        suppressionReason: String? = null,
        messageFamily: String? = null,
        amount: Double? = null,
        hasOtp: Boolean? = null,
        hasUpiHandle: Boolean? = null,
        hasUpiDeepLink: Boolean? = null,
        hasUrl: Boolean? = null,
        linkClicked: Boolean? = null,
        linkScheme: String? = null,
        urlHost: String? = null,
        resolvedDomain: String? = null,
        domainClass: String? = null,
        metadata: Map<String, String> = emptyMap(),
    ): DeliveryResult {
        val event = PilotContextEvent(
            event_type = eventType,
            source_app = sourceApp,
            target_app = targetApp,
            correlation_id = correlationId,
            classification = classification,
            setup_state = setupState,
            suppression_reason = suppressionReason,
            message_family = messageFamily,
            amount = amount,
            has_otp = hasOtp,
            has_upi_handle = hasUpiHandle,
            has_upi_deeplink = hasUpiDeepLink,
            has_url = hasUrl,
            link_clicked = linkClicked,
            link_scheme = linkScheme,
            url_host = urlHost,
            resolved_domain = resolvedDomain,
            domain_class = domainClass,
            metadata = metadata,
        )
        val summary = buildString {
            append("context_event:")
            append(eventType)
            if (!sourceApp.isNullOrBlank()) {
                append(":")
                append(sourceApp)
            }
        }
        return submitAppLog(
            context = context,
            level = AppConstants.Domain.PILOT_LOG_LEVEL_INFO,
            message = summary,
            language = resolveLanguage(context),
            contextEvent = event,
        )
    }

    suspend fun submitAlertFeedback(
        context: Context,
        alertId: String,
        action: String,
        channel: String,
        title: String,
        message: String,
    ): DeliveryResult {
        val participantId = resolveParticipantId(context)
        val request = LiteracyAlertFeedbackRequest(
                event_id = UUID.randomUUID().toString(),
                alert_id = alertId,
                participant_id = participantId,
                action = action,
                channel = channel,
                title = title,
                message = message,
                timestamp = currentTimestamp(),
            )
        return runCatching {
            val ok = ApiClient.literacyApi(context).alertFeedback(request).ok
            if (ok) {
                DeliveryResult(delivered = true, queued = false, flushedCount = flushQueuedTelemetry(context))
            } else {
                OfflineTelemetryQueue.enqueueAlertFeedback(context, request)
                DeliveryResult(delivered = false, queued = true)
            }
        }.getOrElse {
            OfflineTelemetryQueue.enqueueAlertFeedback(context, request)
            DeliveryResult(delivered = false, queued = true)
        }
    }

    suspend fun getEssentialGoals(context: Context): EssentialGoalProfileResponse {
        val participantId = resolveParticipantId(context)
        return ApiClient.literacyApi(context).essentialGoals(participantId)
    }

    suspend fun saveEssentialGoals(
        context: Context,
        cohort: String,
        essentialGoals: List<String>,
        allSelectedEssentials: List<String>,
        selectionSource: String?,
        goalSourceMap: Map<String, String>,
        affordabilityQuestionKey: String?,
        affordabilityBucketId: String?,
        setupSkipped: Boolean,
    ): EssentialGoalProfileResponse {
        val participantId = resolveParticipantId(context)
        val language = resolveLanguage(context)
        return ApiClient.literacyApi(context).upsertEssentialGoals(
            EssentialGoalProfileRequest(
                participant_id = participantId,
                cohort = cohort,
                essential_goals = essentialGoals,
                all_selected_essentials = allSelectedEssentials,
                active_priority_essentials = essentialGoals,
                selection_source = selectionSource,
                goal_source_map = goalSourceMap,
                affordability_question_key = affordabilityQuestionKey,
                affordability_bucket_id = affordabilityBucketId,
                language = language,
                setup_skipped = setupSkipped,
            )
        )
    }

    suspend fun ensureExperimentAssignment(
        context: Context,
        experimentName: String = "adaptive_alerts_v1",
    ): String {
        val participantId = resolveParticipantId(context)
        return ApiClient.literacyApi(context).assignVariant(
            ExperimentAssignmentRequest(
                participant_id = participantId,
                experiment_name = experimentName,
            )
        ).variant ?: "adaptive"
    }

    suspend fun flushQueuedTelemetry(context: Context): Int {
        return OfflineTelemetryQueue.flush(context)
    }

    fun participantId(context: Context): String {
        return resolveParticipantId(context)
    }

    fun language(context: Context): String {
        return resolveLanguage(context)
    }

    private fun resolveParticipantId(context: Context): String {
        val deviceId = Settings.Secure.getString(
            context.contentResolver,
            Settings.Secure.ANDROID_ID,
        )
        return deviceId ?: AppConstants.Domain.UNKNOWN_PARTICIPANT_ID
    }

    private fun resolveLanguage(context: Context): String {
        val prefs = context.getSharedPreferences(AppConstants.Prefs.PILOT_PREFS, Context.MODE_PRIVATE)
        val code = prefs.getString(AppConstants.Prefs.KEY_APP_LANGUAGE, AppConstants.Locale.DEFAULT_LANGUAGE)
        return if (code == AppConstants.Locale.HINDI_LANGUAGE) {
            AppConstants.Locale.HINDI_LANGUAGE
        } else {
            AppConstants.Locale.DEFAULT_LANGUAGE
        }
    }

    private fun currentTimestamp(): String {
        return Instant.now().toString()
    }
}

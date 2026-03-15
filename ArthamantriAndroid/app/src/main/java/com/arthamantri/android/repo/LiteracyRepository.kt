package com.arthamantri.android.repo

import android.content.Context
import android.provider.Settings
import com.arthamantri.android.api.ApiClient
import com.arthamantri.android.core.AppConstants
import com.arthamantri.android.model.LiteracyAlert
import com.arthamantri.android.model.LiteracyAlertFeedbackRequest
import com.arthamantri.android.model.LiteracyState
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
        timestamp: String? = null,
    ): UpiRequestInspectResponse {
        val participantId = resolveParticipantId(context)
        val language = resolveLanguage(context)
        val api = ApiClient.literacyApi(context)
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
    ): DeliveryResult {
        val request = PilotAppLogRequest(
                event_id = UUID.randomUUID().toString(),
                participant_id = participantId,
                level = level,
                message = message,
                language = language,
                timestamp = currentTimestamp(),
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
        setupSkipped: Boolean,
    ): EssentialGoalProfileResponse {
        val participantId = resolveParticipantId(context)
        val language = resolveLanguage(context)
        return ApiClient.literacyApi(context).upsertEssentialGoals(
            EssentialGoalProfileRequest(
                participant_id = participantId,
                cohort = cohort,
                essential_goals = essentialGoals,
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

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
import com.arthamantri.android.model.UpiOpenRequest

object LiteracyRepository {
    data class SmsSendResult(
        val alerts: List<LiteracyAlert>,
        val state: LiteracyState?,
        val participantId: String?,
    )

    suspend fun sendSmsExpense(
        context: Context,
        amount: Double,
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
                amount = amount,
                category = category,
                note = note,
            )
        )
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
        return api.upiOpen(
            UpiOpenRequest(
                participant_id = participantId,
                language = language,
                app_name = appName,
                intent_amount = intentAmount,
            )
        ).alert
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
        participantId: String,
        level: String,
        message: String,
        language: String = AppConstants.Locale.DEFAULT_LANGUAGE,
    ) {
        ApiClient.literacyApi(context).pilotAppLog(
            PilotAppLogRequest(
                participant_id = participantId,
                level = level,
                message = message,
                language = language,
            )
        )
    }

    suspend fun submitAlertFeedback(
        context: Context,
        alertId: String,
        action: String,
        channel: String,
        title: String,
        message: String,
    ): Boolean {
        val participantId = resolveParticipantId(context)
        return ApiClient.literacyApi(context).alertFeedback(
            LiteracyAlertFeedbackRequest(
                alert_id = alertId,
                participant_id = participantId,
                action = action,
                channel = channel,
                title = title,
                message = message,
            )
        ).ok
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
}

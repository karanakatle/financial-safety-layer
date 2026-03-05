package com.arthamantri.android.repo

import android.content.Context
import com.arthamantri.android.api.ApiClient
import com.arthamantri.android.core.AppConstants
import com.arthamantri.android.model.LiteracyAlert
import com.arthamantri.android.model.LiteracyState
import com.arthamantri.android.model.PilotAppLogRequest
import com.arthamantri.android.model.PilotConsentRequest
import com.arthamantri.android.model.PilotFeedbackRequest
import com.arthamantri.android.model.PilotMetaResponse
import com.arthamantri.android.model.SmsIngestRequest
import com.arthamantri.android.model.UpiOpenRequest

object LiteracyRepository {
    suspend fun sendSmsExpense(
        context: Context,
        amount: Double,
        category: String,
        note: String,
    ): Pair<List<LiteracyAlert>, LiteracyState?> {
        val api = ApiClient.literacyApi(context)
        val response = api.smsIngest(
            SmsIngestRequest(
                amount = amount,
                category = category,
                note = note,
            )
        )
        return response.literacy_alerts to response.literacy_state
    }

    suspend fun notifyUpiOpen(
        context: Context,
        appName: String,
        intentAmount: Double = 0.0,
    ): LiteracyAlert? {
        val api = ApiClient.literacyApi(context)
        return api.upiOpen(
            UpiOpenRequest(
                app_name = appName,
                intent_amount = intentAmount,
            )
        ).alert
    }

    suspend fun status(context: Context): LiteracyState {
        return ApiClient.literacyApi(context).status()
    }

    suspend fun pilotMeta(context: Context): PilotMetaResponse {
        return ApiClient.literacyApi(context).pilotMeta()
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
}

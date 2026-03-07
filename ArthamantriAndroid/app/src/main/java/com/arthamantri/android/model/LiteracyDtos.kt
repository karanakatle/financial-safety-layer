package com.arthamantri.android.model

import com.arthamantri.android.core.AppConstants

data class SmsIngestRequest(
    val participant_id: String,
    val language: String = AppConstants.Locale.DEFAULT_LANGUAGE,
    val amount: Double,
    val category: String = AppConstants.Domain.CATEGORY_BANK_SMS,
    val note: String = AppConstants.Domain.NOTE_ANDROID_SMS_LISTENER,
    val timestamp: String? = null,
)

data class UpiOpenRequest(
    val participant_id: String,
    val language: String = AppConstants.Locale.DEFAULT_LANGUAGE,
    val app_name: String,
    val intent_amount: Double = 0.0,
    val timestamp: String? = null,
)

data class LiteracyAlert(
    val alert_id: String? = null,
    val type: String? = null,
    val priority: String? = null,
    val reason: String? = null,
    val stage: Int? = null,
    val source: String? = null,
    val app_name: String? = null,
    val message: String? = null,
    val projected_daily_spend: Double? = null,
    val daily_safe_limit: Double? = null,
    val risk_score: Double? = null,
    val confidence_score: Double? = null,
    val tone_selected: String? = null,
    val frequency_bucket: String? = null,
    val pause_seconds: Int? = null,
)

data class LiteracyState(
    val date: String? = null,
    val daily_spend: Double? = null,
    val daily_safe_limit: Double? = null,
    val warning_ratio: Double? = null,
    val threshold_risk_active: Boolean? = null,
    val stage1_sent: Boolean? = null,
    val stage2_sent: Boolean? = null,
    val notifications_count: Int? = null,
)

data class SmsIngestResponse(
    val literacy_alerts: List<LiteracyAlert> = emptyList(),
    val literacy_state: LiteracyState? = null,
)

data class UpiOpenResponse(
    val alert: LiteracyAlert? = null,
    val literacy_state: LiteracyState? = null,
)

data class PilotMetaResponse(
    val pilot_mode: Boolean = true,
    val target_cohort_size: Int = 60,
    val disclaimer: String = "",
)

data class PilotConsentRequest(
    val participant_id: String,
    val accepted: Boolean,
    val language: String = AppConstants.Locale.DEFAULT_LANGUAGE,
    val timestamp: String? = null,
)

data class PilotConsentResponse(
    val ok: Boolean = false,
)

data class PilotFeedbackRequest(
    val participant_id: String,
    val rating: Int,
    val comment: String = "",
    val language: String = AppConstants.Locale.DEFAULT_LANGUAGE,
    val timestamp: String? = null,
)

data class PilotFeedbackResponse(
    val ok: Boolean = false,
    val feedback_count: Int = 0,
)

data class PilotAppLogRequest(
    val participant_id: String,
    val level: String = AppConstants.Domain.PILOT_LOG_LEVEL_INFO,
    val message: String,
    val language: String = AppConstants.Locale.DEFAULT_LANGUAGE,
    val timestamp: String? = null,
)

data class PilotAppLogResponse(
    val ok: Boolean = false,
)

data class LiteracyAlertFeedbackRequest(
    val alert_id: String,
    val participant_id: String,
    val action: String,
    val channel: String,
    val title: String,
    val message: String,
    val timestamp: String? = null,
)

data class LiteracyAlertFeedbackResponse(
    val ok: Boolean = false,
)

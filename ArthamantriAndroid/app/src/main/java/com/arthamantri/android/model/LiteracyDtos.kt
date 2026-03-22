package com.arthamantri.android.model

import com.arthamantri.android.core.AppConstants

data class SmsIngestRequest(
    val participant_id: String,
    val language: String = AppConstants.Locale.DEFAULT_LANGUAGE,
    val amount: Double? = null,
    val signal_type: String = AppConstants.Domain.SMS_SIGNAL_EXPENSE,
    val signal_confidence: String = AppConstants.Domain.SMS_SIGNAL_CONFIRMED,
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

data class UpiRequestInspectRequest(
    val participant_id: String,
    val language: String = AppConstants.Locale.DEFAULT_LANGUAGE,
    val app_name: String = "",
    val request_kind: String = AppConstants.PaymentInspection.REQUEST_KIND_UNKNOWN,
    val amount: Double? = null,
    val payee_label: String = "",
    val payee_handle: String = "",
    val raw_text: String = "",
    val source: String = AppConstants.PaymentInspection.SOURCE_FOREGROUND_APP,
    val timestamp: String? = null,
)

data class UpiRequestInspectResponse(
    val scenario: String? = null,
    val classification: String? = null,
    val should_warn: Boolean = true,
    val risk_level: String? = null,
    val message: String? = null,
    val why_this_alert: String? = null,
    val next_best_action: String? = null,
    val actions: List<String> = emptyList(),
    val alert_id: String? = null,
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
    val risk_level: String? = null,
    val severity: String? = null,
    val tone_selected: String? = null,
    val frequency_bucket: String? = null,
    val pause_seconds: Int? = null,
    val why_this_alert: String? = null,
    val next_best_action: String? = null,
    val essential_goal_impact: String? = null,
    val essential_goals: List<String>? = null,
    val goal_reserve_ratio: Double? = null,
    val goal_protected_limit: Double? = null,
)

data class EssentialGoalProfileDto(
    val cohort: String? = null,
    val essential_goals: List<String> = emptyList(),
    val language: String? = null,
    val setup_skipped: Boolean? = null,
)

data class EssentialGoalEnvelopeDto(
    val cohort: String? = null,
    val essential_goals: List<String> = emptyList(),
    val reserve_ratio: Double? = null,
    val reserve_amount: Double? = null,
    val protected_limit: Double? = null,
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
    val essential_goal_profile: EssentialGoalProfileDto? = null,
    val essential_goal_envelope: EssentialGoalEnvelopeDto? = null,
    val participant_id: String? = null,
    val language: String? = null,
    val experiment_variant: String? = null,
    val policy_recalibrated: Boolean? = null,
)

data class UpiOpenResponse(
    val alert: LiteracyAlert? = null,
    val literacy_state: LiteracyState? = null,
    val essential_goal_profile: EssentialGoalProfileDto? = null,
    val essential_goal_envelope: EssentialGoalEnvelopeDto? = null,
    val participant_id: String? = null,
    val language: String? = null,
    val experiment_variant: String? = null,
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
    val event_id: String? = null,
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
    val event_id: String? = null,
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

data class EssentialGoalProfileRequest(
    val participant_id: String,
    val cohort: String,
    val essential_goals: List<String> = emptyList(),
    val language: String = AppConstants.Locale.DEFAULT_LANGUAGE,
    val setup_skipped: Boolean = false,
)

data class EssentialGoalProfileResponse(
    val ok: Boolean? = null,
    val participant_id: String? = null,
    val profile: EssentialGoalProfileDto? = null,
    val envelope: EssentialGoalEnvelopeDto? = null,
)

data class ExperimentAssignmentRequest(
    val participant_id: String,
    val experiment_name: String = "adaptive_alerts_v1",
    val preferred_variant: String? = null,
)

data class ExperimentAssignmentResponse(
    val ok: Boolean = false,
    val participant_id: String? = null,
    val experiment_name: String? = null,
    val variant: String? = null,
)

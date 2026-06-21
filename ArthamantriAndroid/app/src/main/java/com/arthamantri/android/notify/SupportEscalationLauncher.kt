package com.arthamantri.android.notify

import android.app.Activity
import android.content.Context
import android.content.Intent
import com.arthamantri.android.MainActivity
import com.arthamantri.android.core.AppConstants

object SupportEscalationLauncher {
    fun launch(
        context: Context,
        alertId: String,
        title: String,
        body: String,
        severity: String,
        pauseSeconds: Int,
        whyThisAlert: String,
        nextSafeAction: String,
        essentialGoalImpact: String,
        primaryActionLabel: String,
        focusedActionLabels: List<String>,
        proceedConfirmationLabel: String,
        useFocusedPaymentActions: Boolean,
        humanReviewMetadata: HumanReviewSupportMetadata? = null,
    ): Boolean {
        val supportIntent = Intent(context, MainActivity::class.java).apply {
            putExtra(AppConstants.IntentExtras.ALERT_OPEN_SUPPORT_PATH, true)
            putExtra(AppConstants.IntentExtras.ALERT_ID, alertId)
            putExtra(AppConstants.IntentExtras.ALERT_TITLE, title)
            putExtra(AppConstants.IntentExtras.ALERT_MESSAGE, body)
            putExtra(AppConstants.IntentExtras.ALERT_SEVERITY, severity)
            putExtra(AppConstants.IntentExtras.ALERT_PAUSE_SECONDS, pauseSeconds)
            putExtra(AppConstants.IntentExtras.ALERT_WHY_THIS_ALERT, whyThisAlert)
            putExtra(AppConstants.IntentExtras.ALERT_NEXT_SAFE_ACTION, nextSafeAction)
            putExtra(AppConstants.IntentExtras.ALERT_ESSENTIAL_GOAL_IMPACT, essentialGoalImpact)
            putExtra(AppConstants.IntentExtras.ALERT_PRIMARY_ACTION_LABEL, primaryActionLabel)
            putStringArrayListExtra(
                AppConstants.IntentExtras.ALERT_FOCUSED_ACTION_LABELS,
                ArrayList(focusedActionLabels),
            )
            putExtra(
                AppConstants.IntentExtras.ALERT_PROCEED_CONFIRMATION_LABEL,
                proceedConfirmationLabel,
            )
            putExtra(AppConstants.IntentExtras.ALERT_USE_FOCUSED_PAYMENT_ACTIONS, useFocusedPaymentActions)
            putExtra(AppConstants.IntentExtras.HUMAN_REVIEW_REDACTED_SNIPPET, humanReviewMetadata?.redactedSnippet)
            putExtra(AppConstants.IntentExtras.HUMAN_REVIEW_CATEGORY, humanReviewMetadata?.category)
            putExtra(AppConstants.IntentExtras.HUMAN_REVIEW_RISK_LEVEL, humanReviewMetadata?.riskLevel)
            humanReviewMetadata?.confidenceScore?.let {
                putExtra(AppConstants.IntentExtras.HUMAN_REVIEW_CONFIDENCE_SCORE, it)
            }
            putExtra(AppConstants.IntentExtras.HUMAN_REVIEW_REVIEWABLE, humanReviewMetadata?.reviewable ?: false)
            putExtra(AppConstants.IntentExtras.HUMAN_REVIEW_SOURCE_TYPE, humanReviewMetadata?.sourceType)
            putExtra(AppConstants.IntentExtras.HUMAN_REVIEW_REASON_CODE, humanReviewMetadata?.reasonCode)
            addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP)
            if (context !is Activity) {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
        }

        return runCatching {
            context.startActivity(supportIntent)
            true
        }.getOrElse { false }
    }
}

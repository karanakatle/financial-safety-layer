package com.arthamantri.android.notify

import android.content.Context
import android.util.Log
import com.arthamantri.android.core.AppConstants
import com.arthamantri.android.repo.LiteracyRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

object AlertFeedbackReporter {
    fun report(
        context: Context,
        alertId: String,
        action: String,
        channel: String,
        title: String,
        message: String,
        metadata: AlertFeedbackMetadata? = null,
    ) {
        val safeMessage = safeReportMessage(message, metadata)
        val overlayReactionLog = overlayReactionLogMessage(action, channel)
        CoroutineScope(Dispatchers.IO).launch {
            runCatching {
                val feedbackResult = LiteracyRepository.submitAlertFeedback(
                    context = context,
                    alertId = alertId,
                    action = action,
                    channel = channel,
                    title = title,
                    message = safeMessage,
                    category = metadata?.category,
                    riskLevel = metadata?.riskLevel,
                    sourceType = metadata?.sourceType,
                    reasonCode = metadata?.reasonCode,
                )
                if (overlayReactionLog != null) {
                    LiteracyRepository.submitAppLog(
                        context = context,
                        level = AppConstants.Domain.PILOT_LOG_LEVEL_INFO,
                        message = overlayReactionLog,
                    )
                }
                feedbackResult
            }.onSuccess { result ->
                if (result.queued) {
                    Log.w(
                        AppConstants.LogTags.MAIN_ACTIVITY,
                        "Alert feedback queued for later sync",
                    )
                }
            }.onFailure {
                Log.e(
                    AppConstants.LogTags.MAIN_ACTIVITY,
                    "Failed to submit alert feedback",
                    it,
                )
            }
        }
    }

    internal fun safeReportMessage(
        message: String,
        metadata: AlertFeedbackMetadata?,
    ): String {
        return metadata?.safeSummary() ?: message
    }

    internal fun overlayReactionLogMessage(action: String, channel: String): String? {
        val normalizedChannel = channel.trim().lowercase()
        if (normalizedChannel !in setOf("overlay", "overlay_window")) {
            return null
        }
        return when (action.trim().lowercase()) {
            AppConstants.Domain.ALERT_ACTION_USEFUL -> "overlay_reaction_useful"
            AppConstants.Domain.ALERT_ACTION_NOT_USEFUL,
            AppConstants.Domain.ALERT_ACTION_DISMISSED,
            AppConstants.Domain.ALERT_ACTION_BACKED_OUT,
            AppConstants.Domain.ALERT_ACTION_BACKGROUNDED,
            AppConstants.Domain.ALERT_ACTION_REPLACED -> "overlay_reaction_irritating"
            else -> null
        }
    }
}

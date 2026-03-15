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
    ) {
        CoroutineScope(Dispatchers.IO).launch {
            runCatching {
                LiteracyRepository.submitAlertFeedback(
                    context = context,
                    alertId = alertId,
                    action = action,
                    channel = channel,
                    title = title,
                    message = message,
                )
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
}

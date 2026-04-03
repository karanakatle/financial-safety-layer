package com.arthamantri.android.savings

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import com.arthamantri.android.core.AppConstants
import com.arthamantri.android.notify.SavingsNudgeNotifier
import com.arthamantri.android.repo.LiteracyRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class SavingsNudgeReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != AppConstants.BroadcastActions.RUN_SAVINGS_NUDGE) {
            return
        }
        val pendingResult = goAsync()
        CoroutineScope(Dispatchers.IO).launch {
            try {
                val preview = LiteracyRepository.fetchEndOfDaySavingsPreview(context)
                val nudge = preview.nudge
                if (nudge?.should_notify == true && !nudge.title.isNullOrBlank() && !nudge.message.isNullOrBlank()) {
                    SavingsNudgeNotifier.show(
                        context = context,
                        title = nudge.title,
                        body = nudge.message,
                    )
                }
            } finally {
                pendingResult.finish()
            }
        }
    }
}

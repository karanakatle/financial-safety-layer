package com.arthamantri.android.savings

import android.app.AlarmManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import com.arthamantri.android.core.AppConstants
import java.util.Calendar

object SavingsNudgeScheduler {
    fun scheduleDaily(context: Context) {
        val alarmManager = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        val pendingIntent = pendingIntent(context)
        val triggerAtMillis = nextTriggerAtMillis()
        alarmManager.setInexactRepeating(
            AlarmManager.RTC_WAKEUP,
            triggerAtMillis,
            AlarmManager.INTERVAL_DAY,
            pendingIntent,
        )
    }

    fun cancel(context: Context) {
        val alarmManager = context.getSystemService(Context.ALARM_SERVICE) as AlarmManager
        alarmManager.cancel(pendingIntent(context))
    }

    fun nextTriggerAtMillis(now: Calendar = Calendar.getInstance()): Long {
        val trigger = now.clone() as Calendar
        trigger.set(Calendar.HOUR_OF_DAY, 20)
        trigger.set(Calendar.MINUTE, 0)
        trigger.set(Calendar.SECOND, 0)
        trigger.set(Calendar.MILLISECOND, 0)
        if (!trigger.after(now)) {
            trigger.add(Calendar.DAY_OF_YEAR, 1)
        }
        return trigger.timeInMillis
    }

    private fun pendingIntent(context: Context): PendingIntent {
        val intent = Intent(context, SavingsNudgeReceiver::class.java).apply {
            action = AppConstants.BroadcastActions.RUN_SAVINGS_NUDGE
        }
        return PendingIntent.getBroadcast(
            context,
            AppConstants.Notifications.SAVINGS_NUDGE_REQUEST_CODE,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
    }
}

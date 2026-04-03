package com.arthamantri.android.usage

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import com.arthamantri.android.savings.SavingsNudgeScheduler

class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (Intent.ACTION_BOOT_COMPLETED != intent.action) {
            return
        }
        val serviceIntent = Intent(context, AppUsageForegroundService::class.java)
        context.startForegroundService(serviceIntent)
        SavingsNudgeScheduler.scheduleDaily(context)
    }
}

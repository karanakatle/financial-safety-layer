package com.arthamantri.android.usage

import android.app.Notification
import android.app.Service
import android.app.usage.UsageEvents
import android.app.usage.UsageStatsManager
import android.content.Context
import android.content.Intent
import android.os.IBinder
import android.util.Log
import com.arthamantri.android.R
import com.arthamantri.android.core.AppConstants
import com.arthamantri.android.notify.AlertNotifier
import com.arthamantri.android.repo.LiteracyRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch

class AppUsageForegroundService : Service() {
    private val serviceScope = CoroutineScope(Dispatchers.IO + Job())
    private var lastForegroundPackage: String? = null
    private var lastUpiSignalAtMs: Long = 0L

    override fun onCreate() {
        super.onCreate()
        AlertNotifier.ensureChannel(this)
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        startForeground(AppConstants.Notifications.FOREGROUND_SERVICE_ID, buildServiceNotification())
        startMonitoringLoop()
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun buildServiceNotification(): Notification {
        return androidx.core.app.NotificationCompat.Builder(this, AppConstants.Notifications.SAFETY_CHANNEL_ID)
            .setSmallIcon(android.R.drawable.ic_popup_sync)
            .setContentTitle(getString(R.string.service_notif_title))
            .setContentText(getString(R.string.service_notif_text))
            .setPriority(androidx.core.app.NotificationCompat.PRIORITY_LOW)
            .build()
    }

    private fun startMonitoringLoop() {
        serviceScope.launch {
            while (isActive) {
                try {
                    val pkg = foregroundPackageName()
                    if (pkg != null && pkg != lastForegroundPackage) {
                        lastForegroundPackage = pkg
                        if (UpiPackages.isUpiPackage(this@AppUsageForegroundService, pkg)) {
                            maybeSignalUpiOpen(pkg)
                        }
                    }
                } catch (e: Exception) {
                    Log.e(
                        AppConstants.LogTags.APP_USAGE_SERVICE,
                        AppConstants.LogMessages.APP_USAGE_MONITOR_LOOP_ERROR,
                        e,
                    )
                }
                delay(AppConstants.Timing.MONITOR_LOOP_DELAY_MS)
            }
        }
    }

    private suspend fun maybeSignalUpiOpen(packageName: String) {
        val now = System.currentTimeMillis()
        if (now - lastUpiSignalAtMs < AppConstants.Timing.UPI_SIGNAL_DEBOUNCE_MS) {
            return
        }
        lastUpiSignalAtMs = now

        try {
            val appName = UpiPackages.displayName(this, packageName)
            val alert = LiteracyRepository.notifyUpiOpen(
                context = this,
                appName = appName,
                intentAmount = 0.0,
            )

            if (alert != null) {
                AlertNotifier.show(
                    this,
                    title = getString(R.string.alert_payment_risk_title),
                    body = alert.message ?: getString(R.string.alert_body_default),
                    alertId = alert.alert_id,
                    pauseSeconds = alert.pause_seconds ?: 0,
                    nextSafeAction = alert.next_best_action,
                    essentialGoalImpact = alert.essential_goal_impact,
                )
            }
        } catch (e: Exception) {
            Log.e(
                AppConstants.LogTags.APP_USAGE_SERVICE,
                AppConstants.LogMessages.APP_USAGE_NOTIFY_UPI_FAILED,
                e,
            )
        }
    }

    private fun foregroundPackageName(): String? {
        val usm = getSystemService(Context.USAGE_STATS_SERVICE) as UsageStatsManager
        val end = System.currentTimeMillis()
        val begin = end - AppConstants.Timing.FOREGROUND_QUERY_WINDOW_MS
        val events = usm.queryEvents(begin, end)
        val event = UsageEvents.Event()

        var lastPackage: String? = null
        while (events.hasNextEvent()) {
            events.getNextEvent(event)
            if (event.eventType == UsageEvents.Event.MOVE_TO_FOREGROUND) {
                lastPackage = event.packageName
            }
        }
        return lastPackage
    }
}

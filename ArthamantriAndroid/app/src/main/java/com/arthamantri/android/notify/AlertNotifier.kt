package com.arthamantri.android.notify

import android.Manifest
import android.app.PendingIntent
import android.app.NotificationChannel
import android.app.KeyguardManager
import android.app.NotificationManager
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Handler
import android.os.Build
import android.os.Looper
import android.provider.Settings
import androidx.core.app.ActivityCompat
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.arthamantri.android.R
import com.arthamantri.android.core.AppConstants

object AlertNotifier {
    private val mainHandler = Handler(Looper.getMainLooper())

    fun ensureChannel(context: Context) {
        if (Build.VERSION.SDK_INT < Build.VERSION_CODES.O) {
            return
        }

        val manager = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        val channel = NotificationChannel(
            AppConstants.Notifications.SAFETY_CHANNEL_ID,
            context.getString(R.string.notif_channel_name),
            NotificationManager.IMPORTANCE_HIGH,
        ).apply {
            description = context.getString(R.string.notif_channel_desc)
        }
        manager.createNotificationChannel(channel)
    }

    fun show(
        context: Context,
        title: String,
        body: String,
        alertId: String? = null,
        pauseSeconds: Int = 0,
    ) {
        ensureChannel(context)

        mainHandler.post {
            val resolvedAlertId = alertId ?: java.util.UUID.randomUUID().toString()
            val keyguardManager = context.getSystemService(Context.KEYGUARD_SERVICE) as KeyguardManager
            if (keyguardManager.isKeyguardLocked) {
                return@post
            }

            val overlayShown = if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M || Settings.canDrawOverlays(context)) {
                OverlayAlertWindow.show(context, resolvedAlertId, title, body, pauseSeconds)
            } else {
                false
            }

            val alertIntent = Intent(context, AlertDisplayActivity::class.java).apply {
                putExtra(AlertDisplayActivity.EXTRA_TITLE, title)
                putExtra(AlertDisplayActivity.EXTRA_MESSAGE, body)
                putExtra(AlertDisplayActivity.EXTRA_ALERT_ID, resolvedAlertId)
                putExtra(AlertDisplayActivity.EXTRA_PAUSE_SECONDS, pauseSeconds)
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP)
            }

            if (!overlayShown) {
                // Fallback when overlay permission is absent or blocked.
                runCatching { context.startActivity(alertIntent) }
            }

            val pendingIntentFlags = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
                PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
            } else {
                PendingIntent.FLAG_UPDATE_CURRENT
            }
            val fullScreenIntent = PendingIntent.getActivity(
                context,
                AppConstants.Notifications.FULL_SCREEN_INTENT_ID,
                alertIntent,
                pendingIntentFlags,
            )

            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU &&
                ActivityCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS)
                != PackageManager.PERMISSION_GRANTED
            ) {
                return@post
            }

            val id = (System.currentTimeMillis() % Int.MAX_VALUE).toInt()
            val notification = NotificationCompat.Builder(context, AppConstants.Notifications.SAFETY_CHANNEL_ID)
                .setSmallIcon(android.R.drawable.ic_dialog_alert)
                .setContentTitle(title)
                .setContentText(body)
                .setStyle(NotificationCompat.BigTextStyle().bigText(body))
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .setCategory(NotificationCompat.CATEGORY_RECOMMENDATION)
                .setVisibility(NotificationCompat.VISIBILITY_PRIVATE)
                .setContentIntent(fullScreenIntent)
                .setAutoCancel(true)
                .build()

            NotificationManagerCompat.from(context).notify(id, notification)
        }
    }
}

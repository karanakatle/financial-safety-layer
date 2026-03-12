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
import androidx.annotation.ColorRes
import androidx.core.app.ActivityCompat
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.content.ContextCompat
import com.arthamantri.android.R
import com.arthamantri.android.core.AppConstants

object AlertNotifier {
    data class AlertVisualStyle(
        @param:ColorRes val scrimColorRes: Int,
        @param:ColorRes val badgeBgColorRes: Int,
        @param:ColorRes val badgeTextColorRes: Int,
        val tagTextRes: Int,
        val notificationPriority: Int,
    )

    private val mainHandler = Handler(Looper.getMainLooper())
    private val explainabilityMarkers = listOf(
        "\nRisk level:",
        "\nWhy this alert:",
        "\nNext safe action:",
        "\nEssential-goal impact:",
        "\nजोखिम स्तर:",
        "\nक्यों दिखा:",
        "\nअगला सुरक्षित कदम:",
        "\nआवश्यक लक्ष्य प्रभाव:",
    )

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
        severity: String = "medium",
        pauseSeconds: Int = 0,
        nextSafeAction: String? = null,
        essentialGoalImpact: String? = null,
    ) {
        ensureChannel(context)
        val resolvedSeverity = normalizeSeverity(severity)
        val style = styleForSeverity(resolvedSeverity)
        val primaryBody = sanitizeBody(
            body = body,
            hasExplainabilitySections = !nextSafeAction.isNullOrBlank() || !essentialGoalImpact.isNullOrBlank(),
        )

        mainHandler.post {
            val resolvedAlertId = alertId ?: java.util.UUID.randomUUID().toString()
            val keyguardManager = context.getSystemService(Context.KEYGUARD_SERVICE) as KeyguardManager
            if (keyguardManager.isKeyguardLocked) {
                return@post
            }

            val overlayShown = if (Build.VERSION.SDK_INT < Build.VERSION_CODES.M || Settings.canDrawOverlays(context)) {
                OverlayAlertWindow.show(
                    context = context,
                    alertId = resolvedAlertId,
                    title = title,
                    message = primaryBody,
                    severity = resolvedSeverity,
                    pauseSeconds = pauseSeconds,
                    nextSafeAction = nextSafeAction,
                    essentialGoalImpact = essentialGoalImpact,
                )
            } else {
                false
            }

            val alertIntent = Intent(context, AlertDisplayActivity::class.java).apply {
                putExtra(AlertDisplayActivity.EXTRA_TITLE, title)
                putExtra(AlertDisplayActivity.EXTRA_MESSAGE, primaryBody)
                putExtra(AlertDisplayActivity.EXTRA_ALERT_ID, resolvedAlertId)
                putExtra(AlertDisplayActivity.EXTRA_PAUSE_SECONDS, pauseSeconds)
                putExtra(AlertDisplayActivity.EXTRA_SEVERITY, resolvedSeverity)
                putExtra(AlertDisplayActivity.EXTRA_NEXT_SAFE_ACTION, nextSafeAction)
                putExtra(AlertDisplayActivity.EXTRA_ESSENTIAL_GOAL_IMPACT, essentialGoalImpact)
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
                .setContentText(primaryBody)
                .setStyle(NotificationCompat.BigTextStyle().bigText(primaryBody))
                .setPriority(style.notificationPriority)
                .setCategory(NotificationCompat.CATEGORY_RECOMMENDATION)
                .setVisibility(NotificationCompat.VISIBILITY_PRIVATE)
                .setContentIntent(fullScreenIntent)
                .setAutoCancel(true)
                .setColor(ContextCompat.getColor(context, style.badgeTextColorRes))
                .build()

            NotificationManagerCompat.from(context).notify(id, notification)
        }
    }

    private fun sanitizeBody(body: String, hasExplainabilitySections: Boolean): String {
        if (!hasExplainabilitySections) {
            return body
        }
        var minIndex = -1
        for (marker in explainabilityMarkers) {
            val idx = body.indexOf(marker)
            if (idx >= 0 && (minIndex == -1 || idx < minIndex)) {
                minIndex = idx
            }
        }
        return if (minIndex > 0) body.substring(0, minIndex).trim() else body
    }

    fun normalizeSeverity(severity: String?): String {
        return when (severity?.trim()?.lowercase()) {
            "soft" -> "soft"
            "hard" -> "hard"
            else -> "medium"
        }
    }

    fun styleForSeverity(severity: String): AlertVisualStyle {
        return when (normalizeSeverity(severity)) {
            "soft" -> AlertVisualStyle(
                scrimColorRes = R.color.alert_soft_scrim,
                badgeBgColorRes = R.color.alert_soft_badge_bg,
                badgeTextColorRes = R.color.alert_soft_badge_text,
                tagTextRes = R.string.alert_tag_soft,
                notificationPriority = NotificationCompat.PRIORITY_DEFAULT,
            )
            "hard" -> AlertVisualStyle(
                scrimColorRes = R.color.alert_hard_scrim,
                badgeBgColorRes = R.color.alert_hard_badge_bg,
                badgeTextColorRes = R.color.alert_hard_badge_text,
                tagTextRes = R.string.alert_tag_hard,
                notificationPriority = NotificationCompat.PRIORITY_HIGH,
            )
            else -> AlertVisualStyle(
                scrimColorRes = R.color.alert_medium_scrim,
                badgeBgColorRes = R.color.alert_medium_badge_bg,
                badgeTextColorRes = R.color.alert_medium_badge_text,
                tagTextRes = R.string.alert_tag_medium,
                notificationPriority = NotificationCompat.PRIORITY_HIGH,
            )
        }
    }
}

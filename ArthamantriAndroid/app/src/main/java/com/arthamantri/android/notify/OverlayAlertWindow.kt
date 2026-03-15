package com.arthamantri.android.notify

import android.content.Context
import android.content.res.ColorStateList
import android.os.CountDownTimer
import android.graphics.PixelFormat
import android.os.Build
import android.provider.Settings
import android.view.Gravity
import android.view.LayoutInflater
import android.view.View
import android.view.WindowManager
import android.widget.Button
import android.widget.TextView
import androidx.core.content.ContextCompat
import com.arthamantri.android.R
import com.arthamantri.android.core.AppConstants
import java.util.UUID

object OverlayAlertWindow {
    private var overlayView: View? = null
    private var pauseTimer: CountDownTimer? = null
    private var currentAlertId: String? = null
    private var currentTitle: String = ""
    private var currentMessage: String = ""
    private var currentWhyThisAlert: String = ""
    private var currentNextSafeAction: String = ""
    private var currentEssentialGoalImpact: String = ""

    fun show(
        context: Context,
        alertId: String,
        title: String,
        message: String,
        severity: String = "medium",
        pauseSeconds: Int = 0,
        whyThisAlert: String? = null,
        nextSafeAction: String? = null,
        essentialGoalImpact: String? = null,
        primaryActionLabel: String? = null,
    ): Boolean {
        if (!canShowOverlay(context)) {
            return false
        }

        val appContext = context.applicationContext
        val wm = appContext.getSystemService(Context.WINDOW_SERVICE) as WindowManager

        if (overlayView != null) {
            updateContent(
                alertId = alertId,
                title = title,
                message = message,
                severity = severity,
                pauseSeconds = pauseSeconds,
                whyThisAlert = whyThisAlert,
                nextSafeAction = nextSafeAction,
                essentialGoalImpact = essentialGoalImpact,
                primaryActionLabel = primaryActionLabel,
            )
            return true
        }

        val view = LayoutInflater.from(appContext).inflate(R.layout.view_overlay_alert, null, false)
        view.findViewById<TextView>(R.id.overlayAlertTitle).text = title
        view.findViewById<TextView>(R.id.overlayAlertMessage).text = message
        applySeverityStyle(view, severity)
        bindExplainability(
            view = view,
            whyThisAlert = whyThisAlert,
            nextSafeAction = nextSafeAction,
            essentialGoalImpact = essentialGoalImpact,
        )
        val dismissBtn = view.findViewById<Button>(R.id.overlayDismissBtn)
        val usefulBtn = view.findViewById<Button>(R.id.overlayUsefulBtn)
        val notUsefulBtn = view.findViewById<Button>(R.id.overlayNotUsefulBtn)
        if (!primaryActionLabel.isNullOrBlank()) {
            dismissBtn.text = primaryActionLabel
        }
        currentAlertId = alertId
        currentTitle = title
        currentMessage = message
        currentWhyThisAlert = whyThisAlert.orEmpty()
        currentNextSafeAction = nextSafeAction.orEmpty()
        currentEssentialGoalImpact = essentialGoalImpact.orEmpty()
        dismissBtn.setOnClickListener {
            reportFeedback(appContext, AppConstants.Domain.ALERT_ACTION_DISMISSED)
            dismiss(appContext)
        }
        usefulBtn.setOnClickListener {
            reportFeedback(appContext, AppConstants.Domain.ALERT_ACTION_USEFUL)
            dismiss(appContext)
        }
        notUsefulBtn.setOnClickListener {
            reportFeedback(appContext, AppConstants.Domain.ALERT_ACTION_NOT_USEFUL)
            dismiss(appContext)
        }
        setupPause(view, pauseSeconds, dismissBtn, usefulBtn, notUsefulBtn)

        val type = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
        } else {
            @Suppress("DEPRECATION")
            WindowManager.LayoutParams.TYPE_PHONE
        }

        val params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.MATCH_PARENT,
            WindowManager.LayoutParams.MATCH_PARENT,
            type,
            WindowManager.LayoutParams.FLAG_LAYOUT_IN_SCREEN,
            PixelFormat.TRANSLUCENT,
        ).apply {
            gravity = Gravity.CENTER
        }

        wm.addView(view, params)
        overlayView = view
        return true
    }

    fun dismiss(context: Context) {
        val view = overlayView ?: return
        pauseTimer?.cancel()
        pauseTimer = null
        val appContext = context.applicationContext
        val wm = appContext.getSystemService(Context.WINDOW_SERVICE) as WindowManager
        runCatching { wm.removeView(view) }
        overlayView = null
        currentAlertId = null
        currentTitle = ""
        currentMessage = ""
        currentWhyThisAlert = ""
        currentNextSafeAction = ""
        currentEssentialGoalImpact = ""
    }

    private fun updateContent(
        alertId: String,
        title: String,
        message: String,
        severity: String,
        pauseSeconds: Int,
        whyThisAlert: String?,
        nextSafeAction: String?,
        essentialGoalImpact: String?,
        primaryActionLabel: String?,
    ) {
        val view = overlayView ?: return
        currentAlertId = alertId
        currentTitle = title
        currentMessage = message
        currentWhyThisAlert = whyThisAlert.orEmpty()
        currentNextSafeAction = nextSafeAction.orEmpty()
        currentEssentialGoalImpact = essentialGoalImpact.orEmpty()
        view.findViewById<TextView>(R.id.overlayAlertTitle).text = title
        view.findViewById<TextView>(R.id.overlayAlertMessage).text = message
        applySeverityStyle(view, severity)
        bindExplainability(
            view = view,
            whyThisAlert = whyThisAlert,
            nextSafeAction = nextSafeAction,
            essentialGoalImpact = essentialGoalImpact,
        )
        val dismissBtn = view.findViewById<Button>(R.id.overlayDismissBtn)
        val usefulBtn = view.findViewById<Button>(R.id.overlayUsefulBtn)
        val notUsefulBtn = view.findViewById<Button>(R.id.overlayNotUsefulBtn)
        if (!primaryActionLabel.isNullOrBlank()) {
            dismissBtn.text = primaryActionLabel
        }
        setupPause(view, pauseSeconds, dismissBtn, usefulBtn, notUsefulBtn)
    }

    private fun bindExplainability(
        view: View,
        whyThisAlert: String?,
        nextSafeAction: String?,
        essentialGoalImpact: String?,
    ) {
        val whyHeading = view.findViewById<TextView>(R.id.overlayWhyHeading)
        val whyBody = view.findViewById<TextView>(R.id.overlayWhyBody)
        val nextActionHeading = view.findViewById<TextView>(R.id.overlayNextActionHeading)
        val nextActionBody = view.findViewById<TextView>(R.id.overlayNextActionBody)
        val goalImpactHeading = view.findViewById<TextView>(R.id.overlayGoalImpactHeading)
        val goalImpactBody = view.findViewById<TextView>(R.id.overlayGoalImpactBody)

        val whyValue = whyThisAlert?.trim().orEmpty()
        if (whyValue.isNotEmpty()) {
            whyHeading.visibility = View.VISIBLE
            whyBody.visibility = View.VISIBLE
            whyBody.text = whyValue
        } else {
            whyHeading.visibility = View.GONE
            whyBody.visibility = View.GONE
        }

        val nextActionValue = nextSafeAction?.trim().orEmpty()
        if (nextActionValue.isNotEmpty()) {
            nextActionHeading.visibility = View.VISIBLE
            nextActionBody.visibility = View.VISIBLE
            nextActionBody.text = nextActionValue
        } else {
            nextActionHeading.visibility = View.GONE
            nextActionBody.visibility = View.GONE
        }

        val goalImpactValue = essentialGoalImpact?.trim().orEmpty()
        if (goalImpactValue.isNotEmpty()) {
            goalImpactHeading.visibility = View.VISIBLE
            goalImpactBody.visibility = View.VISIBLE
            goalImpactBody.text = goalImpactValue
        } else {
            goalImpactHeading.visibility = View.GONE
            goalImpactBody.visibility = View.GONE
        }
    }

    private fun setupPause(
        view: View,
        pauseSeconds: Int,
        dismissBtn: Button,
        usefulBtn: Button,
        notUsefulBtn: Button,
    ) {
        pauseTimer?.cancel()
        pauseTimer = null
        val pauseHint = view.findViewById<TextView>(R.id.overlayPauseHint)
        if (pauseSeconds <= 0) {
            pauseHint.visibility = View.GONE
            dismissBtn.isEnabled = true
            usefulBtn.isEnabled = true
            notUsefulBtn.isEnabled = true
            return
        }

        dismissBtn.isEnabled = false
        usefulBtn.isEnabled = false
        notUsefulBtn.isEnabled = false
        pauseHint.visibility = View.VISIBLE
        pauseHint.text = view.context.getString(R.string.alert_pause_countdown, pauseSeconds)

        pauseTimer = object : CountDownTimer((pauseSeconds * 1000L), 1000L) {
            override fun onTick(millisUntilFinished: Long) {
                val secondsLeft = ((millisUntilFinished + 999L) / 1000L).toInt()
                pauseHint.text = view.context.getString(R.string.alert_pause_countdown, secondsLeft)
            }

            override fun onFinish() {
                pauseHint.visibility = View.GONE
                dismissBtn.isEnabled = true
                usefulBtn.isEnabled = true
                notUsefulBtn.isEnabled = true
            }
        }.start()
    }

    private fun reportFeedback(context: Context, action: String) {
        AlertFeedbackReporter.report(
            context = context,
            alertId = currentAlertId ?: UUID.randomUUID().toString(),
            action = action,
            channel = "overlay_window",
            title = currentTitle,
            message = listOf(
                currentMessage,
                currentWhyThisAlert,
                currentNextSafeAction,
                currentEssentialGoalImpact,
            ).filter { it.isNotBlank() }.joinToString("\n"),
        )
    }

    private fun canShowOverlay(context: Context): Boolean {
        return Build.VERSION.SDK_INT < Build.VERSION_CODES.M || Settings.canDrawOverlays(context)
    }

    private fun applySeverityStyle(view: View, severity: String) {
        val context = view.context
        val style = AlertNotifier.styleForSeverity(severity)
        val scrim = view.findViewById<View>(R.id.overlayScrim)
        val tag = view.findViewById<TextView>(R.id.overlayAlertTag)
        val title = view.findViewById<TextView>(R.id.overlayAlertTitle)
        val dismissBtn = view.findViewById<Button>(R.id.overlayDismissBtn)

        scrim.setBackgroundColor(ContextCompat.getColor(context, style.scrimColorRes))
        tag.text = context.getString(style.tagTextRes)
        tag.backgroundTintList = ColorStateList.valueOf(ContextCompat.getColor(context, style.badgeBgColorRes))
        tag.setTextColor(ContextCompat.getColor(context, style.badgeTextColorRes))
        title.setTextColor(ContextCompat.getColor(context, style.badgeTextColorRes))
        dismissBtn.backgroundTintList = ColorStateList.valueOf(ContextCompat.getColor(context, style.badgeTextColorRes))
    }
}

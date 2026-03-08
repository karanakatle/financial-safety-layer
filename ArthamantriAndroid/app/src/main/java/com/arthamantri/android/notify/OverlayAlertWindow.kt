package com.arthamantri.android.notify

import android.content.Context
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
import com.arthamantri.android.R
import com.arthamantri.android.core.AppConstants
import java.util.UUID

object OverlayAlertWindow {
    private var overlayView: View? = null
    private var pauseTimer: CountDownTimer? = null
    private var currentAlertId: String? = null
    private var currentTitle: String = ""
    private var currentMessage: String = ""
    private var currentNextSafeAction: String = ""
    private var currentEssentialGoalImpact: String = ""

    fun show(
        context: Context,
        alertId: String,
        title: String,
        message: String,
        pauseSeconds: Int = 0,
        nextSafeAction: String? = null,
        essentialGoalImpact: String? = null,
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
                pauseSeconds = pauseSeconds,
                nextSafeAction = nextSafeAction,
                essentialGoalImpact = essentialGoalImpact,
            )
            return true
        }

        val view = LayoutInflater.from(appContext).inflate(R.layout.view_overlay_alert, null, false)
        view.findViewById<TextView>(R.id.overlayAlertTitle).text = title
        view.findViewById<TextView>(R.id.overlayAlertMessage).text = message
        bindExplainability(
            view = view,
            nextSafeAction = nextSafeAction,
            essentialGoalImpact = essentialGoalImpact,
        )
        val dismissBtn = view.findViewById<Button>(R.id.overlayDismissBtn)
        val usefulBtn = view.findViewById<Button>(R.id.overlayUsefulBtn)
        val notUsefulBtn = view.findViewById<Button>(R.id.overlayNotUsefulBtn)
        currentAlertId = alertId
        currentTitle = title
        currentMessage = message
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
        currentNextSafeAction = ""
        currentEssentialGoalImpact = ""
    }

    private fun updateContent(
        alertId: String,
        title: String,
        message: String,
        pauseSeconds: Int,
        nextSafeAction: String?,
        essentialGoalImpact: String?,
    ) {
        val view = overlayView ?: return
        currentAlertId = alertId
        currentTitle = title
        currentMessage = message
        currentNextSafeAction = nextSafeAction.orEmpty()
        currentEssentialGoalImpact = essentialGoalImpact.orEmpty()
        view.findViewById<TextView>(R.id.overlayAlertTitle).text = title
        view.findViewById<TextView>(R.id.overlayAlertMessage).text = message
        bindExplainability(
            view = view,
            nextSafeAction = nextSafeAction,
            essentialGoalImpact = essentialGoalImpact,
        )
        val dismissBtn = view.findViewById<Button>(R.id.overlayDismissBtn)
        val usefulBtn = view.findViewById<Button>(R.id.overlayUsefulBtn)
        val notUsefulBtn = view.findViewById<Button>(R.id.overlayNotUsefulBtn)
        setupPause(view, pauseSeconds, dismissBtn, usefulBtn, notUsefulBtn)
    }

    private fun bindExplainability(
        view: View,
        nextSafeAction: String?,
        essentialGoalImpact: String?,
    ) {
        val nextActionHeading = view.findViewById<TextView>(R.id.overlayNextActionHeading)
        val nextActionBody = view.findViewById<TextView>(R.id.overlayNextActionBody)
        val goalImpactHeading = view.findViewById<TextView>(R.id.overlayGoalImpactHeading)
        val goalImpactBody = view.findViewById<TextView>(R.id.overlayGoalImpactBody)

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
                currentNextSafeAction,
                currentEssentialGoalImpact,
            ).filter { it.isNotBlank() }.joinToString("\n"),
        )
    }

    private fun canShowOverlay(context: Context): Boolean {
        return Build.VERSION.SDK_INT < Build.VERSION_CODES.M || Settings.canDrawOverlays(context)
    }
}

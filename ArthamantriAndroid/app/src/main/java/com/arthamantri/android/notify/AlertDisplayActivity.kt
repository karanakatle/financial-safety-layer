package com.arthamantri.android.notify

import android.os.Bundle
import android.os.CountDownTimer
import android.view.View
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import com.arthamantri.android.R
import com.arthamantri.android.core.AppConstants
import java.util.UUID

class AlertDisplayActivity : AppCompatActivity() {
    private var pauseTimer: CountDownTimer? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_alert_display)

        val alertId = intent.getStringExtra(EXTRA_ALERT_ID) ?: UUID.randomUUID().toString()
        val title = intent.getStringExtra(EXTRA_TITLE) ?: getString(R.string.alert_title_default)
        val message = intent.getStringExtra(EXTRA_MESSAGE)
            ?: getString(R.string.alert_body_default)
        val pauseSeconds = intent.getIntExtra(EXTRA_PAUSE_SECONDS, 0)
        val nextSafeAction = intent.getStringExtra(EXTRA_NEXT_SAFE_ACTION).orEmpty()
        val essentialGoalImpact = intent.getStringExtra(EXTRA_ESSENTIAL_GOAL_IMPACT).orEmpty()

        findViewById<TextView>(R.id.alertTitle).text = title
        findViewById<TextView>(R.id.alertMessage).text = message
        bindExplainability(nextSafeAction, essentialGoalImpact)
        val dismissBtn = findViewById<Button>(R.id.dismissBtn)
        val usefulBtn = findViewById<Button>(R.id.usefulBtn)
        val notUsefulBtn = findViewById<Button>(R.id.notUsefulBtn)
        val pauseHint = findViewById<TextView>(R.id.alertPauseHint)

        setupPause(
            pauseSeconds = pauseSeconds,
            pauseHint = pauseHint,
            dismissBtn = dismissBtn,
            usefulBtn = usefulBtn,
            notUsefulBtn = notUsefulBtn,
        )

        usefulBtn.setOnClickListener {
            AlertFeedbackReporter.report(
                context = this,
                alertId = alertId,
                action = AppConstants.Domain.ALERT_ACTION_USEFUL,
                channel = "fullscreen_activity",
                title = title,
                message = listOf(message, nextSafeAction, essentialGoalImpact)
                    .filter { it.isNotBlank() }
                    .joinToString("\n"),
            )
            finish()
        }
        notUsefulBtn.setOnClickListener {
            AlertFeedbackReporter.report(
                context = this,
                alertId = alertId,
                action = AppConstants.Domain.ALERT_ACTION_NOT_USEFUL,
                channel = "fullscreen_activity",
                title = title,
                message = listOf(message, nextSafeAction, essentialGoalImpact)
                    .filter { it.isNotBlank() }
                    .joinToString("\n"),
            )
            finish()
        }
        dismissBtn.setOnClickListener {
            AlertFeedbackReporter.report(
                context = this,
                alertId = alertId,
                action = AppConstants.Domain.ALERT_ACTION_DISMISSED,
                channel = "fullscreen_activity",
                title = title,
                message = listOf(message, nextSafeAction, essentialGoalImpact)
                    .filter { it.isNotBlank() }
                    .joinToString("\n"),
            )
            finish()
        }
    }

    override fun onDestroy() {
        pauseTimer?.cancel()
        pauseTimer = null
        super.onDestroy()
    }

    private fun setupPause(
        pauseSeconds: Int,
        pauseHint: TextView,
        dismissBtn: Button,
        usefulBtn: Button,
        notUsefulBtn: Button,
    ) {
        pauseTimer?.cancel()
        pauseTimer = null
        if (pauseSeconds <= 0) {
            pauseHint.text = ""
            dismissBtn.isEnabled = true
            usefulBtn.isEnabled = true
            notUsefulBtn.isEnabled = true
            return
        }

        dismissBtn.isEnabled = false
        usefulBtn.isEnabled = false
        notUsefulBtn.isEnabled = false
        pauseHint.text = getString(R.string.alert_pause_countdown, pauseSeconds)

        pauseTimer = object : CountDownTimer((pauseSeconds * 1000L), 1000L) {
            override fun onTick(millisUntilFinished: Long) {
                val secondsLeft = ((millisUntilFinished + 999L) / 1000L).toInt()
                pauseHint.text = getString(R.string.alert_pause_countdown, secondsLeft)
            }

            override fun onFinish() {
                pauseHint.text = ""
                dismissBtn.isEnabled = true
                usefulBtn.isEnabled = true
                notUsefulBtn.isEnabled = true
            }
        }.start()
    }

    private fun bindExplainability(nextSafeAction: String, essentialGoalImpact: String) {
        val nextActionHeading = findViewById<TextView>(R.id.alertNextActionHeading)
        val nextActionBody = findViewById<TextView>(R.id.alertNextActionBody)
        val goalImpactHeading = findViewById<TextView>(R.id.alertGoalImpactHeading)
        val goalImpactBody = findViewById<TextView>(R.id.alertGoalImpactBody)

        if (nextSafeAction.isNotBlank()) {
            nextActionHeading.text = getString(R.string.alert_next_safe_action_label)
            nextActionHeading.visibility = View.VISIBLE
            nextActionBody.text = nextSafeAction
            nextActionBody.visibility = View.VISIBLE
        } else {
            nextActionHeading.visibility = View.GONE
            nextActionBody.visibility = View.GONE
        }

        if (essentialGoalImpact.isNotBlank()) {
            goalImpactHeading.text = getString(R.string.alert_essential_goal_impact_label)
            goalImpactHeading.visibility = View.VISIBLE
            goalImpactBody.text = essentialGoalImpact
            goalImpactBody.visibility = View.VISIBLE
        } else {
            goalImpactHeading.visibility = View.GONE
            goalImpactBody.visibility = View.GONE
        }
    }

    companion object {
        const val EXTRA_TITLE = AppConstants.IntentExtras.ALERT_TITLE
        const val EXTRA_MESSAGE = AppConstants.IntentExtras.ALERT_MESSAGE
        const val EXTRA_ALERT_ID = AppConstants.IntentExtras.ALERT_ID
        const val EXTRA_PAUSE_SECONDS = AppConstants.IntentExtras.ALERT_PAUSE_SECONDS
        const val EXTRA_NEXT_SAFE_ACTION = AppConstants.IntentExtras.ALERT_NEXT_SAFE_ACTION
        const val EXTRA_ESSENTIAL_GOAL_IMPACT = AppConstants.IntentExtras.ALERT_ESSENTIAL_GOAL_IMPACT
    }
}

package com.arthamantri.android.sms

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.provider.Telephony
import android.util.Log
import com.arthamantri.android.R
import com.arthamantri.android.config.AppConfig
import com.arthamantri.android.core.AppConstants
import com.arthamantri.android.notify.AlertNotifier
import com.arthamantri.android.repo.LiteracyRepository
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

class BankSmsReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (Telephony.Sms.Intents.SMS_RECEIVED_ACTION != intent.action) {
            return
        }

        Log.i(AppConstants.LogTags.BANK_SMS_RECEIVER, "SMS_RECEIVED broadcast received")
        val messages = Telephony.Sms.Intents.getMessagesFromIntent(intent)
        if (messages.isEmpty()) {
            Log.w(AppConstants.LogTags.BANK_SMS_RECEIVER, "SMS_RECEIVED had no message parts")
            return
        }

        val sender = messages[0].originatingAddress
        val body = messages.joinToString(separator = "") { it.messageBody ?: "" }
        Log.i(
            AppConstants.LogTags.BANK_SMS_RECEIVER,
            "Incoming SMS sender=$sender body='${body.take(180)}'"
        )

        val parsed = SmsParser.parseSignal(sender, body)
        if (parsed == null) {
            Log.w(
                AppConstants.LogTags.BANK_SMS_RECEIVER,
                "SMS ignored: parser did not detect financial signal pattern"
            )
            return
        }
        Log.i(
            AppConstants.LogTags.BANK_SMS_RECEIVER,
            "Parsed SMS signal type=${parsed.signalType} confidence=${parsed.confidence} amount=${parsed.amount} category=${parsed.category} baseUrl=${AppConfig.getBaseUrl(context)}"
        )

        CoroutineScope(Dispatchers.IO).launch {
            try {
                val result = LiteracyRepository.sendSmsSignal(
                    context = context,
                    signalType = parsed.signalType,
                    confidence = parsed.confidence,
                    amount = parsed.amount,
                    category = parsed.category,
                    note = parsed.note,
                )
                Log.i(
                    AppConstants.LogTags.BANK_SMS_RECEIVER,
                    "sms-ingest API success; participantId=${result.participantId}; alertsCount=${result.alerts.size}"
                )

                result.alerts.forEach { alert ->
                    AlertNotifier.show(
                        context,
                        title = context.getString(R.string.alert_title_default),
                        body = alert.message ?: context.getString(R.string.alert_spending_threshold),
                        alertId = alert.alert_id,
                        severity = alert.severity ?: "medium",
                        pauseSeconds = alert.pause_seconds ?: 0,
                        whyThisAlert = alert.why_this_alert,
                        nextSafeAction = alert.next_best_action,
                        essentialGoalImpact = alert.essential_goal_impact,
                    )
                }
            } catch (e: Exception) {
                Log.e(
                    AppConstants.LogTags.BANK_SMS_RECEIVER,
                    AppConstants.LogMessages.BANK_SMS_PROCESS_FAILED,
                    e,
                )
                // ADD THIS FOR TESTING: Show the overlay even if the API fails
                AlertNotifier.show(
                    context = context,
                    title = "SMS Processed (Offline)",
                    body = "Signal: ${parsed.signalType}\nAmount: ${parsed.amount ?: "unknown"}\nStatus: Network Error. Could not sync with server.",
                    severity = "medium"
                )
            }
        }
    }
}

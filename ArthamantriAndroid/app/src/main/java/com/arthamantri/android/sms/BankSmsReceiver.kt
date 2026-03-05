package com.arthamantri.android.sms

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.provider.Telephony
import android.util.Log
import com.arthamantri.android.R
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

        val messages = Telephony.Sms.Intents.getMessagesFromIntent(intent)
        if (messages.isEmpty()) {
            return
        }

        val sender = messages[0].originatingAddress
        val body = messages.joinToString(separator = "") { it.messageBody ?: "" }

        val parsed = SmsParser.parseExpense(sender, body) ?: return

        CoroutineScope(Dispatchers.IO).launch {
            try {
                val (alerts, _) = LiteracyRepository.sendSmsExpense(
                    context = context,
                    amount = parsed.amount,
                    category = parsed.category,
                    note = parsed.note,
                )

                alerts.forEach { alert ->
                    AlertNotifier.show(
                        context,
                        title = context.getString(R.string.alert_title_default),
                        body = alert.message ?: context.getString(R.string.alert_spending_threshold),
                    )
                }
            } catch (e: Exception) {
                Log.e(
                    AppConstants.LogTags.BANK_SMS_RECEIVER,
                    AppConstants.LogMessages.BANK_SMS_PROCESS_FAILED,
                    e,
                )
            }
        }
    }
}

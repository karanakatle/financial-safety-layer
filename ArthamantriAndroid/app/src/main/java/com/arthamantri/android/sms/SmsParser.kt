package com.arthamantri.android.sms

import com.arthamantri.android.core.AppConstants

data class ParsedSmsExpense(
    val amount: Double,
    val category: String,
    val note: String,
)

object SmsParser {
    private val amountRegex = Regex(AppConstants.Parsing.AMOUNT_REGEX_PATTERN, RegexOption.IGNORE_CASE)

    fun parseExpense(sender: String?, message: String): ParsedSmsExpense? {
        val body = message.lowercase()

        val looksLikeDebit = AppConstants.Parsing.SMS_DEBIT_KEYWORDS.any { body.contains(it) }

        if (!looksLikeDebit) {
            return null
        }

        val match = amountRegex.find(message) ?: return null
        val amount = match.groupValues.getOrNull(1)?.toDoubleOrNull() ?: return null

        val category = when {
            body.contains("upi") -> AppConstants.Domain.CATEGORY_UPI
            body.contains("card") -> AppConstants.Domain.CATEGORY_CARD
            body.contains("atm") -> AppConstants.Domain.CATEGORY_ATM
            else -> AppConstants.Domain.CATEGORY_BANK_SMS
        }

        return ParsedSmsExpense(
            amount = amount,
            category = category,
            note = "${AppConstants.Domain.NOTE_SMS_PREFIX} ${sender ?: AppConstants.Domain.NOTE_SMS_UNKNOWN_SENDER}",
        )
    }
}

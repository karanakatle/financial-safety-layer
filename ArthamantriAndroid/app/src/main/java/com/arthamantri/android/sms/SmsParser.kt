package com.arthamantri.android.sms

import com.arthamantri.android.core.AppConstants

data class ParsedSmsSignal(
    val signalType: String,
    val confidence: String,
    val amount: Double?,
    val category: String,
    val note: String,
)

object SmsParser {
    private val amountRegexes = AppConstants.Parsing.AMOUNT_REGEX_PATTERNS.map {
        Regex(it, RegexOption.IGNORE_CASE)
    }

    fun parseSignal(sender: String?, message: String): ParsedSmsSignal? {
        val body = message.lowercase()
        val amount = extractAmountValue(message)
        val looksLikeDebit = AppConstants.Parsing.SMS_DEBIT_KEYWORDS.any { body.contains(it) }
        val looksLikeIncome = AppConstants.Parsing.SMS_CREDIT_KEYWORDS.any { body.contains(it) }
        val looksFinancial = AppConstants.Parsing.SMS_FINANCIAL_KEYWORDS.any { body.contains(it) } ||
            (amount != null && AppConstants.Parsing.MONEY_MARKERS.any { body.contains(it) })

        if (!looksFinancial && amount == null) {
            return null
        }

        val category = when {
            body.contains("upi") -> AppConstants.Domain.CATEGORY_UPI
            body.contains("card") -> AppConstants.Domain.CATEGORY_CARD
            body.contains("atm") -> AppConstants.Domain.CATEGORY_ATM
            else -> AppConstants.Domain.CATEGORY_BANK_SMS
        }

        val signalType = when {
            looksLikeDebit && !looksLikeIncome && amount != null -> AppConstants.Domain.SMS_SIGNAL_EXPENSE
            looksLikeIncome && !looksLikeDebit && amount != null -> AppConstants.Domain.SMS_SIGNAL_INCOME
            else -> AppConstants.Domain.SMS_SIGNAL_PARTIAL
        }
        val confidence = if (signalType == AppConstants.Domain.SMS_SIGNAL_PARTIAL) {
            AppConstants.Domain.SMS_SIGNAL_PARTIAL_CONFIDENCE
        } else {
            AppConstants.Domain.SMS_SIGNAL_CONFIRMED
        }

        return ParsedSmsSignal(
            signalType = signalType,
            confidence = confidence,
            amount = amount,
            category = category,
            note = "${AppConstants.Domain.NOTE_SMS_PREFIX} ${sender ?: AppConstants.Domain.NOTE_SMS_UNKNOWN_SENDER}",
        )
    }

    fun extractAmountValue(message: String): Double? {
        for (regex in amountRegexes) {
            val value = regex.find(message)
                ?.groupValues
                ?.getOrNull(1)
                ?.replace(",", "")
                ?.trim()
            if (!value.isNullOrEmpty()) {
                return value.toDoubleOrNull()
            }
        }
        return null
    }
}

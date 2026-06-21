package com.arthamantri.android.core

object HumanReviewRedactor {
    private val secretAfterLabelPattern = Regex(
        """\b(otp|one\s*time\s*password|upi\s*pin|pin|password|passcode|cvv)\s*(?:is|=|:|-)?\s*(?:[A-Za-z0-9][A-Za-z0-9-]{3,31}|(?:\d[\s-]*){3,8})\b""",
        RegexOption.IGNORE_CASE,
    )
    private val secretBeforeLabelPattern = Regex(
        """\b(?:[A-Za-z]*\d[A-Za-z0-9-]{3,31}|(?:\d[\s-]*){4,8})\s*(?:is|=|:|-)?\s*(otp|one\s*time\s*password|upi\s*pin|pin|password|passcode|cvv)\b""",
        RegexOption.IGNORE_CASE,
    )
    private val exactBalancePattern = Regex(
        """\b(?:avl\.?\s*bal|available\s+balance|balance)\s*(?:is|=|:|-)?\s*(?:rs\.?|inr|₹)?\s*[\d,]+(?:\.\d{1,2})?\b""",
        RegexOption.IGNORE_CASE,
    )
    private val panPattern = Regex("""\b[a-z]{5}\d{4}[a-z]\b""", RegexOption.IGNORE_CASE)
    private val aadhaarPattern = Regex("""\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b""")
    private val cardPattern = Regex("""\b(?:\d[ -]*?){13,19}\b""")
    private val longNumberPattern = Regex("""\b\d{9,18}\b""")
    private val standaloneShortCodePattern = Regex("""\b\d{4,8}\b""")
    private val ifscPattern = Regex("""\b[A-Z]{4}0[A-Z0-9]{6}\b""", RegexOption.IGNORE_CASE)
    private val handlePattern = Regex("""\b[\w.-]+@[\w.-]+\b""", RegexOption.IGNORE_CASE)
    private val urlPattern = Regex("""https?://\S+|www\.\S+""", RegexOption.IGNORE_CASE)
    private val whitespacePattern = Regex("""\s+""")

    fun redact(value: String, maxLength: Int = 160): String {
        var redacted = value
        redacted = secretAfterLabelPattern.replace(redacted) { "${it.groupValues[1]} [redacted]" }
        redacted = secretBeforeLabelPattern.replace(redacted) { "[redacted] ${it.groupValues[1]}" }
        redacted = exactBalancePattern.replace(redacted, "[redacted_balance]")
        redacted = panPattern.replace(redacted, "[redacted_pan]")
        redacted = aadhaarPattern.replace(redacted, "[redacted_aadhaar]")
        redacted = cardPattern.replace(redacted, "[redacted_card]")
        redacted = longNumberPattern.replace(redacted, "[redacted_number]")
        redacted = standaloneShortCodePattern.replace(redacted, "[redacted_code]")
        redacted = ifscPattern.replace(redacted, "[redacted_ifsc]")
        redacted = handlePattern.replace(redacted, "[redacted_handle]")
        redacted = urlPattern.replace(redacted, "[redacted_url]")
        redacted = whitespacePattern.replace(redacted, " ").trim()
        return if (redacted.length > maxLength) {
            "${redacted.take(maxLength).trimEnd()}..."
        } else {
            redacted
        }
    }
}

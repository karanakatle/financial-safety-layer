package com.finsaathi.android.core

data class FinancialRiskMessageFixture(
    val id: String,
    val message: String,
    val expectedRiskLevel: FinancialRiskLevel,
    val expectedCategory: FinancialRiskCategory,
    val expectedReasonCode: String,
)

object FinancialRiskMessageFixtures {
    val firstSprintSamples: List<FinancialRiskMessageFixture> = listOf(
        FinancialRiskMessageFixture(
            id = "hinglish-packing-job-registration-fee",
            message = "Ghar baithe packing job. Pay Rs. 499 registration fee and earn Rs. 30000 monthly.",
            expectedRiskLevel = FinancialRiskLevel.RED,
            expectedCategory = FinancialRiskCategory.UPFRONT_FEE_RISK,
            expectedReasonCode = "pay_before_benefit",
        ),
        FinancialRiskMessageFixture(
            id = "hinglish-kyc-link-pressure",
            message = "Aapka KYC expire ho gaya. Verify now at https://bank-verify-help.top to avoid block.",
            expectedRiskLevel = FinancialRiskLevel.RED,
            expectedCategory = FinancialRiskCategory.KYC_ACCOUNT_BLOCK_PRESSURE,
            expectedReasonCode = "kyc_or_account_pressure",
        ),
        FinancialRiskMessageFixture(
            id = "double-money-payment-pressure",
            message = "Double your money in 30 days. Pay now. Limited time scheme.",
            expectedRiskLevel = FinancialRiskLevel.RED,
            expectedCategory = FinancialRiskCategory.GUARANTEED_RETURN_SCHEME,
            expectedReasonCode = "unrealistic_return_promise",
        ),
        FinancialRiskMessageFixture(
            id = "double-money-no-payment-pressure",
            message = "Double money ideas are being discussed in my group.",
            expectedRiskLevel = FinancialRiskLevel.YELLOW,
            expectedCategory = FinancialRiskCategory.GUARANTEED_RETURN_SCHEME,
            expectedReasonCode = "unrealistic_return_promise",
        ),
        FinancialRiskMessageFixture(
            id = "otp-only-safety-message",
            message = "Your OTP is 246810 for login. Do not share it with anyone.",
            expectedRiskLevel = FinancialRiskLevel.GREEN,
            expectedCategory = FinancialRiskCategory.BENIGN_OR_ROUTINE,
            expectedReasonCode = "routine_financial_message",
        ),
        FinancialRiskMessageFixture(
            id = "routine-debit-sms",
            message = "Rs. 500 debited from your a/c via UPI. Avl bal Rs. 1200.",
            expectedRiskLevel = FinancialRiskLevel.GREEN,
            expectedCategory = FinancialRiskCategory.BENIGN_OR_ROUTINE,
            expectedReasonCode = "routine_financial_message",
        ),
    )

    val missedScamRegressionSamples: List<FinancialRiskMessageFixture> =
        firstSprintSamples.filter { it.expectedRiskLevel != FinancialRiskLevel.GREEN }

    val benignSuppressionSamples: List<FinancialRiskMessageFixture> =
        firstSprintSamples.filter { it.expectedRiskLevel == FinancialRiskLevel.GREEN }
}

object FinancialRiskDetectorHarness {
    data class Result(
        val fixtureId: String,
        val expectedRiskLevel: FinancialRiskLevel,
        val actualRiskLevel: FinancialRiskLevel,
        val expectedCategory: FinancialRiskCategory,
        val actualCategory: FinancialRiskCategory,
        val expectedReasonCode: String,
        val actualReasonCode: String,
    ) {
        val matchesExpected: Boolean
            get() = expectedRiskLevel == actualRiskLevel &&
                expectedCategory == actualCategory &&
                expectedReasonCode == actualReasonCode
    }

    fun evaluate(fixtures: List<FinancialRiskMessageFixture>): List<Result> {
        return fixtures.map { fixture ->
            val actual = FinancialRiskMessageDetector.detect(fixture.message)
            Result(
                fixtureId = fixture.id,
                expectedRiskLevel = fixture.expectedRiskLevel,
                actualRiskLevel = actual.riskLevel,
                expectedCategory = fixture.expectedCategory,
                actualCategory = actual.category,
                expectedReasonCode = fixture.expectedReasonCode,
                actualReasonCode = actual.reasonCode,
            )
        }
    }

    fun failureReport(failures: List<Result>): String {
        if (failures.isEmpty()) {
            return "All detector fixtures matched expected risk, category, and reason."
        }
        return failures.joinToString(separator = "\n") { failure ->
            "${failure.fixtureId}: expected risk=${failure.expectedRiskLevel}, " +
                "actual risk=${failure.actualRiskLevel}; " +
                "expected category=${failure.expectedCategory}, actual category=${failure.actualCategory}; " +
                "expected reason=${failure.expectedReasonCode}, actual reason=${failure.actualReasonCode}"
        }
    }
}

package com.finsaathi.android.core

import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotEquals
import org.junit.Test

class FinancialRiskMessageDetectorTest {
    @Test
    fun `fixture harness evaluates realistic synthetic detector samples`() {
        val failures = FinancialRiskDetectorHarness.evaluate(FinancialRiskMessageFixtures.firstSprintSamples)
            .filterNot { it.matchesExpected }

        assertEquals(
            FinancialRiskDetectorHarness.failureReport(failures),
            emptyList<FinancialRiskDetectorHarness.Result>(),
            failures,
        )
    }

    @Test
    fun `missed scam regression samples remain alerting`() {
        val failures = FinancialRiskDetectorHarness.evaluate(FinancialRiskMessageFixtures.missedScamRegressionSamples)
            .filter { it.actualRiskLevel == FinancialRiskLevel.GREEN }

        assertEquals(
            FinancialRiskDetectorHarness.failureReport(failures),
            emptyList<FinancialRiskDetectorHarness.Result>(),
            failures,
        )
    }

    @Test
    fun `benign suppression samples stay non red`() {
        FinancialRiskDetectorHarness.evaluate(FinancialRiskMessageFixtures.benignSuppressionSamples)
            .forEach { result ->
                assertNotEquals(
                    "${result.fixtureId} should not produce a red alert after benign suppression review",
                    FinancialRiskLevel.RED,
                    result.actualRiskLevel,
                )
            }
    }

    @Test
    fun `fixture harness failure report shows expected and actual risk`() {
        val report = FinancialRiskDetectorHarness.failureReport(
            listOf(
                FinancialRiskDetectorHarness.Result(
                    fixtureId = "sample",
                    expectedRiskLevel = FinancialRiskLevel.RED,
                    actualRiskLevel = FinancialRiskLevel.YELLOW,
                    expectedCategory = FinancialRiskCategory.UPFRONT_FEE_RISK,
                    actualCategory = FinancialRiskCategory.GENERIC_PROMOTION,
                    expectedReasonCode = "pay_before_benefit",
                    actualReasonCode = "generic_financial_promotion",
                )
            )
        )

        assertEquals(
            "sample: expected risk=RED, actual risk=YELLOW; " +
                "expected category=UPFRONT_FEE_RISK, actual category=GENERIC_PROMOTION; " +
                "expected reason=pay_before_benefit, actual reason=generic_financial_promotion",
            report,
        )
    }

    @Test
    fun `detects upfront fee earning scam as red`() {
        val result = FinancialRiskMessageDetector.detect(
            "Pay Rs. 499 registration and earn Rs. 30,000 monthly",
        )

        assertEquals(FinancialRiskLevel.RED, result.riskLevel)
        assertEquals(FinancialRiskCategory.UPFRONT_FEE_RISK, result.category)
    }

    @Test
    fun `detects loan processing fee as red`() {
        val result = FinancialRiskMessageDetector.detect(
            "Loan approved, pay processing fee today to receive amount",
        )

        assertEquals(FinancialRiskLevel.RED, result.riskLevel)
        assertEquals(FinancialRiskCategory.UPFRONT_FEE_RISK, result.category)
    }

    @Test
    fun `detects otp and upi pin sharing request as red`() {
        val result = FinancialRiskMessageDetector.detect(
            "Share OTP or UPI PIN to receive refund",
        )

        assertEquals(FinancialRiskLevel.RED, result.riskLevel)
        assertEquals(FinancialRiskCategory.SENSITIVE_DATA_REQUEST, result.category)
    }

    @Test
    fun `detects sensitive data request even when message includes safety wording`() {
        val result = FinancialRiskMessageDetector.detect(
            "Do not share OTP with anyone. For account unlock, send OTP here now.",
        )

        assertEquals(FinancialRiskLevel.RED, result.riskLevel)
        assertEquals(FinancialRiskCategory.SENSITIVE_DATA_REQUEST, result.category)
    }

    @Test
    fun `detects enter otp request as red`() {
        val result = FinancialRiskMessageDetector.detect(
            "Enter OTP to receive refund immediately.",
        )

        assertEquals(FinancialRiskLevel.RED, result.riskLevel)
        assertEquals(FinancialRiskCategory.SENSITIVE_DATA_REQUEST, result.category)
    }

    @Test
    fun `detects kyc pressure with link as red`() {
        val result = FinancialRiskMessageDetector.detect(
            "Your KYC will be blocked today. Verify now at https://bank-verify-help.top",
        )

        assertEquals(FinancialRiskLevel.RED, result.riskLevel)
        assertEquals(FinancialRiskCategory.KYC_ACCOUNT_BLOCK_PRESSURE, result.category)
    }

    @Test
    fun `detects unknown short link money pressure as red`() {
        val result = FinancialRiskMessageDetector.detect(
            "Claim refund today at bit.ly/pay-help and confirm payment.",
        )

        assertEquals(FinancialRiskLevel.RED, result.riskLevel)
        assertEquals(FinancialRiskCategory.UNKNOWN_LINK_MONEY_PRESSURE, result.category)
        assertEquals(true, result.reviewable)
        assertEquals(0.62, result.confidenceScore, 0.001)
    }

    @Test
    fun `detects double money scheme as yellow without payment pressure`() {
        val result = FinancialRiskMessageDetector.detect(
            "Double your money in 30 days with this investment idea",
        )

        assertEquals(FinancialRiskLevel.YELLOW, result.riskLevel)
        assertEquals(FinancialRiskCategory.GUARANTEED_RETURN_SCHEME, result.category)
    }

    @Test
    fun `detects guaranteed return with payment pressure as red`() {
        val result = FinancialRiskMessageDetector.detect(
            "Guaranteed return. Pay now. Limited time offer.",
        )

        assertEquals(FinancialRiskLevel.RED, result.riskLevel)
        assertEquals(FinancialRiskCategory.GUARANTEED_RETURN_SCHEME, result.category)
    }

    @Test
    fun `keeps otp only message green`() {
        val result = FinancialRiskMessageDetector.detect(
            "Your OTP is 123456 for login. Do not share it with anyone.",
        )

        assertEquals(FinancialRiskLevel.GREEN, result.riskLevel)
        assertEquals(FinancialRiskCategory.BENIGN_OR_ROUTINE, result.category)
    }

    @Test
    fun `escalates otp after recent suspicious clicked link as red`() {
        val result = FinancialRiskMessageDetector.detect(
            message = "Your OTP is 123456 for mobile banking login. Do not share it with anyone.",
            recentLinkContext = LinkContextSignalExtractor.fromRawUrl(
                rawUrl = "https://bank-verify-help.top/login",
                linkClicked = true,
            ),
        )

        assertEquals(FinancialRiskLevel.RED, result.riskLevel)
        assertEquals(FinancialRiskCategory.KYC_ACCOUNT_BLOCK_PRESSURE, result.category)
        assertEquals("recent_link_account_access", result.reasonCode)
    }

    @Test
    fun `keeps otp after official looking bank domain non red`() {
        val result = FinancialRiskMessageDetector.detect(
            message = "Your OTP is 123456 for mobile banking login. Do not share it with anyone.",
            recentLinkContext = LinkContextSignalExtractor.fromRawUrl(
                rawUrl = "https://secure.icicibank.com/login",
                linkClicked = true,
            ),
        )

        assertEquals(FinancialRiskLevel.GREEN, result.riskLevel)
        assertEquals(FinancialRiskCategory.BENIGN_OR_ROUTINE, result.category)
    }

    @Test
    fun `keeps normal debit sms green for detector`() {
        val result = FinancialRiskMessageDetector.detect(
            "Rs. 500 debited from your a/c via UPI. Avl bal Rs. 1200.",
        )

        assertEquals(FinancialRiskLevel.GREEN, result.riskLevel)
        assertEquals(FinancialRiskCategory.BENIGN_OR_ROUTINE, result.category)
    }

    @Test
    fun `keeps generic loan promotion non red`() {
        val result = FinancialRiskMessageDetector.detect(
            "Exclusive loan offer available for you. Apply now.",
        )

        assertEquals(FinancialRiskLevel.YELLOW, result.riskLevel)
        assertEquals(FinancialRiskCategory.GENERIC_PROMOTION, result.category)
    }
}

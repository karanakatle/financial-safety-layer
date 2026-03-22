package com.arthamantri.android.core

import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNotNull
import org.junit.Test

class LinkContextIntelligenceTest {
    @Test
    fun extractsHttpLinkFromMessageText() {
        val signals = LinkContextSignalExtractor.fromText(
            "Update your account at https://secure.icicibank.com/login today",
            linkClicked = false,
        )

        assertNotNull(signals)
        assertFalse(signals!!.linkClicked)
        assertEquals("https", signals.linkScheme)
        assertEquals("secure.icicibank.com", signals.urlHost)
        assertEquals("icicibank.com", signals.resolvedDomain)
    }

    @Test
    fun extractsUpiDeepLinkFromMessageText() {
        val signals = LinkContextSignalExtractor.fromText(
            "Pay now using upi://pay?pa=merchant@upi&pn=Merchant",
            linkClicked = false,
        )

        assertNotNull(signals)
        assertEquals("upi", signals!!.linkScheme)
        assertEquals("pay", signals.urlHost)
        assertEquals("pay", signals.resolvedDomain)
    }

    @Test
    fun resolvesRegistrableDomainForSecondLevelCountrySuffix() {
        assertEquals("federalbank.co.in", LinkContextSignalExtractor.resolveDomain("secure.federalbank.co.in"))
    }
}

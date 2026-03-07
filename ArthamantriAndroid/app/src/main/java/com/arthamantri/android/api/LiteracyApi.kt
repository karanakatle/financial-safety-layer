package com.arthamantri.android.api

import com.arthamantri.android.model.LiteracyState
import com.arthamantri.android.model.PilotConsentRequest
import com.arthamantri.android.model.PilotConsentResponse
import com.arthamantri.android.model.PilotAppLogRequest
import com.arthamantri.android.model.PilotAppLogResponse
import com.arthamantri.android.model.PilotFeedbackRequest
import com.arthamantri.android.model.PilotFeedbackResponse
import com.arthamantri.android.model.PilotMetaResponse
import com.arthamantri.android.model.LiteracyAlertFeedbackRequest
import com.arthamantri.android.model.LiteracyAlertFeedbackResponse
import com.arthamantri.android.model.SmsIngestRequest
import com.arthamantri.android.model.SmsIngestResponse
import com.arthamantri.android.model.UpiOpenRequest
import com.arthamantri.android.model.UpiOpenResponse
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Query

interface LiteracyApi {
    @POST("api/literacy/sms-ingest")
    suspend fun smsIngest(@Body body: SmsIngestRequest): SmsIngestResponse

    @POST("api/literacy/upi-open")
    suspend fun upiOpen(@Body body: UpiOpenRequest): UpiOpenResponse

    @GET("api/literacy/status")
    suspend fun status(@Query("participant_id") participantId: String): LiteracyState

    @GET("api/pilot/meta")
    suspend fun pilotMeta(): PilotMetaResponse

    @POST("api/pilot/consent")
    suspend fun pilotConsent(@Body body: PilotConsentRequest): PilotConsentResponse

    @POST("api/pilot/feedback")
    suspend fun pilotFeedback(@Body body: PilotFeedbackRequest): PilotFeedbackResponse

    @POST("api/pilot/app-log")
    suspend fun pilotAppLog(@Body body: PilotAppLogRequest): PilotAppLogResponse

    @POST("api/literacy/alert-feedback")
    suspend fun alertFeedback(@Body body: LiteracyAlertFeedbackRequest): LiteracyAlertFeedbackResponse
}

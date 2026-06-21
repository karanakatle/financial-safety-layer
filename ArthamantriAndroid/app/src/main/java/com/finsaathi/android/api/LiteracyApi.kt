package com.finsaathi.android.api

import com.finsaathi.android.model.LiteracyState
import com.finsaathi.android.model.PilotConsentRequest
import com.finsaathi.android.model.PilotConsentResponse
import com.finsaathi.android.model.PilotAppLogRequest
import com.finsaathi.android.model.PilotAppLogResponse
import com.finsaathi.android.model.PilotFeedbackRequest
import com.finsaathi.android.model.PilotFeedbackResponse
import com.finsaathi.android.model.PilotHumanReviewRequest
import com.finsaathi.android.model.PilotHumanReviewResponse
import com.finsaathi.android.model.PilotMetaResponse
import com.finsaathi.android.model.LiteracyAlertFeedbackRequest
import com.finsaathi.android.model.LiteracyAlertFeedbackResponse
import com.finsaathi.android.model.EssentialGoalProfileRequest
import com.finsaathi.android.model.EssentialGoalProfileResponse
import com.finsaathi.android.model.ExperimentAssignmentRequest
import com.finsaathi.android.model.ExperimentAssignmentResponse
import com.finsaathi.android.model.CurrentBalanceRequest
import com.finsaathi.android.model.CurrentBalanceResponse
import com.finsaathi.android.model.EodSavingsPreviewRequest
import com.finsaathi.android.model.EodSavingsPreviewResponse
import com.finsaathi.android.model.SmsIngestRequest
import com.finsaathi.android.model.SmsIngestResponse
import com.finsaathi.android.model.UpiRequestInspectRequest
import com.finsaathi.android.model.UpiRequestInspectResponse
import com.finsaathi.android.model.UpiOpenRequest
import com.finsaathi.android.model.UpiOpenResponse
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Query

interface LiteracyApi {
    @POST("api/literacy/sms-ingest")
    suspend fun smsIngest(@Body body: SmsIngestRequest): SmsIngestResponse

    @POST("api/literacy/upi-open")
    suspend fun upiOpen(@Body body: UpiOpenRequest): UpiOpenResponse

    @POST("api/literacy/upi-request-inspect")
    suspend fun upiRequestInspect(@Body body: UpiRequestInspectRequest): UpiRequestInspectResponse

    @GET("api/literacy/status")
    suspend fun status(@Query("participant_id") participantId: String): LiteracyState

    @GET("api/pilot/meta")
    suspend fun pilotMeta(@Query("language") language: String): PilotMetaResponse

    @POST("api/pilot/consent")
    suspend fun pilotConsent(@Body body: PilotConsentRequest): PilotConsentResponse

    @POST("api/pilot/feedback")
    suspend fun pilotFeedback(@Body body: PilotFeedbackRequest): PilotFeedbackResponse

    @POST("api/pilot/app-log")
    suspend fun pilotAppLog(@Body body: PilotAppLogRequest): PilotAppLogResponse

    @POST("api/pilot/human-review-queue")
    suspend fun pilotHumanReview(@Body body: PilotHumanReviewRequest): PilotHumanReviewResponse

    @POST("api/literacy/alert-feedback")
    suspend fun alertFeedback(@Body body: LiteracyAlertFeedbackRequest): LiteracyAlertFeedbackResponse

    @GET("api/literacy/essential-goals")
    suspend fun essentialGoals(@Query("participant_id") participantId: String): EssentialGoalProfileResponse

    @POST("api/literacy/essential-goals")
    suspend fun upsertEssentialGoals(@Body body: EssentialGoalProfileRequest): EssentialGoalProfileResponse

    @GET("api/literacy/current-balance")
    suspend fun currentBalance(@Query("participant_id") participantId: String): CurrentBalanceResponse

    @POST("api/literacy/current-balance")
    suspend fun upsertCurrentBalance(@Body body: CurrentBalanceRequest): CurrentBalanceResponse

    @POST("api/literacy/eod-savings-preview")
    suspend fun eodSavingsPreview(@Body body: EodSavingsPreviewRequest): EodSavingsPreviewResponse

    @POST("api/research/assignment")
    suspend fun assignVariant(@Body body: ExperimentAssignmentRequest): ExperimentAssignmentResponse
}

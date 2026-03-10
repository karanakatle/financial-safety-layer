package com.arthamantri.android.api

import android.content.Context
import com.arthamantri.android.BuildConfig
import com.arthamantri.android.config.AppConfig
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.converter.gson.GsonConverterFactory
import java.util.concurrent.TimeUnit

object ApiClient {
    @Volatile
    private var cachedBaseUrl: String? = null

    @Volatile
    private var cachedApi: LiteracyApi? = null

    fun literacyApi(context: Context): LiteracyApi {
        val baseUrl = AppConfig.getBaseUrl(context)
        cachedApi?.let { existing ->
            if (cachedBaseUrl == baseUrl) {
                return existing
            }
        }

        synchronized(this) {
            cachedApi?.let { existing ->
                if (cachedBaseUrl == baseUrl) {
                    return existing
                }
            }

            val logging = HttpLoggingInterceptor().apply {
                level = if (BuildConfig.DEBUG) {
                    HttpLoggingInterceptor.Level.BASIC
                } else {
                    HttpLoggingInterceptor.Level.NONE
                }
            }

            val client = OkHttpClient.Builder()
                .connectTimeout(12, TimeUnit.SECONDS)
                .readTimeout(12, TimeUnit.SECONDS)
                .addInterceptor(logging)
                .build()

            val api = Retrofit.Builder()
                .baseUrl(baseUrl)
                .client(client)
                .addConverterFactory(GsonConverterFactory.create())
                .build()
                .create(LiteracyApi::class.java)

            cachedBaseUrl = baseUrl
            cachedApi = api
            return api
        }
    }
}

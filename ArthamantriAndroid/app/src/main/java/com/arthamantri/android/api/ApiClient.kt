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
    fun literacyApi(context: Context): LiteracyApi {
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

        return Retrofit.Builder()
            .baseUrl(AppConfig.getBaseUrl(context))
            .client(client)
            .addConverterFactory(GsonConverterFactory.create())
            .build()
            .create(LiteracyApi::class.java)
    }
}

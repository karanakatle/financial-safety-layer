@file:Suppress("DEPRECATION")

import java.util.Properties
import java.io.File
import org.jetbrains.kotlin.gradle.dsl.JvmTarget

plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
}

val keystoreProperties = Properties()
val keystorePropertiesFile = rootProject.file("keystore.properties")
val hasKeystoreProperties = keystorePropertiesFile.exists()
val releaseTaskRequested = gradle.startParameter.taskNames.any { taskName ->
    val requestedTask = taskName.substringAfterLast(":")
    requestedTask.contains("Release")
}
val configuredApiBaseUrl = ((project.findProperty("API_BASE_URL") as String?)
    ?: System.getenv("API_BASE_URL"))
    ?.trim()
    ?.takeIf { it.isNotBlank() }
val defaultDebugApiBaseUrl = "http://10.0.2.2:8765/"
val apiBaseUrl = configuredApiBaseUrl
    ?: if (releaseTaskRequested) {
        error(
            "Release builds require an explicit API_BASE_URL. " +
                "Pass -PAPI_BASE_URL=https://api.yourdomain.com/ or set API_BASE_URL."
        )
    } else {
        defaultDebugApiBaseUrl
    }
require(apiBaseUrl.startsWith("http://") || apiBaseUrl.startsWith("https://")) {
    "API_BASE_URL must start with http:// or https://"
}
require(apiBaseUrl.endsWith("/")) {
    "API_BASE_URL must end with / for Retrofit base URL compatibility."
}
val privacyPolicyUrl = ((project.findProperty("PRIVACY_POLICY_URL") as String?)
    ?: System.getenv("PRIVACY_POLICY_URL")
    ?: "https://karanakatle.github.io/finsaathi-legal/privacy-policy.html")
    .trim()
if (hasKeystoreProperties) {
    keystorePropertiesFile.inputStream().use { keystoreProperties.load(it) }
}

android {
    namespace = "com.finsaathi.android"
    compileSdk = 35

    buildFeatures {
        buildConfig = true
    }
    defaultConfig {
        applicationId = "com.finsaathi.android"
        minSdk = 26
        targetSdk = 35
        versionCode = 3
        versionName = "1.2"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
        buildConfigField("String", "DEFAULT_BASE_URL", "\"${apiBaseUrl.replace("\"", "\\\"")}\"")
        buildConfigField("String", "PRIVACY_POLICY_URL", "\"${privacyPolicyUrl.replace("\"", "\\\"")}\"")
    }

    signingConfigs {
        if (hasKeystoreProperties) {
            create("release") {
                val storeFilePath = keystoreProperties.getProperty("storeFile")
                val storePasswordValue = keystoreProperties.getProperty("storePassword")
                val keyAliasValue = keystoreProperties.getProperty("keyAlias")
                val keyPasswordValue = keystoreProperties.getProperty("keyPassword")

                require(!storeFilePath.isNullOrBlank()) { "Missing 'storeFile' in keystore.properties" }
                require(!storePasswordValue.isNullOrBlank()) { "Missing 'storePassword' in keystore.properties" }
                require(!keyAliasValue.isNullOrBlank()) { "Missing 'keyAlias' in keystore.properties" }
                require(!keyPasswordValue.isNullOrBlank()) { "Missing 'keyPassword' in keystore.properties" }

                val resolvedStoreFile = if (File(storeFilePath).isAbsolute) {
                    File(storeFilePath)
                } else {
                    rootProject.file(storeFilePath)
                }
                storeFile = resolvedStoreFile
                storePassword = storePasswordValue
                keyAlias = keyAliasValue
                keyPassword = keyPasswordValue
            }
        }
    }
    buildTypes {
        debug {
            applicationIdSuffix = ".dev"
            versionNameSuffix = "-dev"
        }
        release {
            if (releaseTaskRequested && !hasKeystoreProperties) {
                error("Release builds require keystore.properties; refusing to fall back to debug signing.")
            }
            signingConfig = if (hasKeystoreProperties) {
                signingConfigs.getByName("release")
            } else {
                signingConfigs.getByName("debug")
            }
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
}

kotlin {
    compilerOptions {
        jvmTarget.set(JvmTarget.JVM_17)
    }
}

dependencies {
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("com.google.android.material:material:1.12.0")
    implementation("androidx.work:work-runtime-ktx:2.9.1")

    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.8.1")

    implementation("com.squareup.retrofit2:retrofit:2.11.0")
    implementation("com.squareup.retrofit2:converter-gson:2.11.0")
    implementation("com.squareup.okhttp3:logging-interceptor:4.12.0")

    testImplementation("junit:junit:4.13.2")
}

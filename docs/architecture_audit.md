# Repository Architecture Audit

This audit is the file-by-file backing inventory for `docs/architecture.md`. It groups every tracked repository file by subsystem, records its architectural role, and notes the main inbound and outbound relationships that matter when reading the system.

Legend:

- `runtime-critical`: directly participates in shipped runtime behavior.
- `support-tooling`: build, deployment, simulation, or operational support.
- `test-only`: used only for verification.
- `documentation-only`: explanatory or policy content, not executed.
- `asset`: static visual or bundled resource consumed by a runtime surface.

## Cross-cutting overlaps worth knowing first

- `backend/main.py` is both composition root and a controller module; pilot and legacy routes are delegated, but literacy endpoints remain inline.
- `rule_engine/engine.py` and `backend/literacy/safety_monitor.py` both create alerts, but they serve different product surfaces and persistence models.
- `frontend/script.js` and `ArthamantriAndroid/.../LiteracyRepository.kt` are parallel API consumers with different endpoint subsets.
- `BankSmsReceiver.kt` and `TransactionNotificationListenerService.kt` both transform device-side events into `POST /api/literacy/sms-ingest`.
- `research/simulator/*` is not a deployment runtime, but it depends on the same literacy safety concepts that power Android-facing alerts.

## Root, Packaging, And Deployment

- `.gitignore` — repository-wide ignore policy; inbound: Git; outbound: developer workflow hygiene; `support-tooling`.
- `.gitkeep` — placeholder to keep an otherwise empty tracked path available; inbound: Git; outbound: repo structure continuity; `support-tooling`.
- `README.md` — primary project entrypoint covering product scope, APIs, local run, PWA/mobile, and research summary; inbound: developers/operators; outbound: all major subsystems; `documentation-only`.
- `render.yaml` — Render deployment blueprint wiring install/start commands and health check path; inbound: Render; outbound: `backend.main:app`; `support-tooling`.
- `requirements.txt` — pinned Python dependency manifest for backend, tests, and simulator; inbound: pip/venv setup; outbound: Python runtime surfaces; `support-tooling`.

## Backend Runtime

### Package Markers And Shared Models

- `backend/__init__.py` — package marker for backend imports; inbound: Python import system; outbound: package namespace; `support-tooling`.
- `backend/api_models.py` — Pydantic request models for legacy, literacy, pilot, and research endpoints; inbound: FastAPI handlers and tests; outbound: request validation boundary; `runtime-critical`.
- `backend/config/__init__.py` — config package export surface; inbound: `backend.main`; outbound: `load_literacy_policy`; `support-tooling`.
- `backend/config/literacy_policy.py` — env-backed literacy policy loader and defaults; inbound: `backend.main`, tests; outbound: `LiteracyPolicyConfig`; `runtime-critical`.

### App Bootstrap And Shared Helpers

- `backend/main.py` — FastAPI composition root, CORS/static hosting setup, per-participant agent cache, inline literacy endpoints, and router inclusion; inbound: `uvicorn`, `render.yaml`, scripts, tests; outbound: routes, literacy stack, storage, voice factory, frontend mount; `runtime-critical`.
- `backend/interaction_manager.py` — response-mode adapter that turns text replies into popup/chat/voice payloads; inbound: legacy routes; outbound: optional voice synthesis; `runtime-critical`.
- `backend/nlp/pipeline.py` — minimal text pipeline that normalizes text and resolves intent; inbound: legacy voice/chat endpoints; outbound: `normalize_text`, `detect_intent`; `runtime-critical`.
- `backend/utils/logger.py` — shared logger configuration used by backend services and rule engine; inbound: `backend.main`, `rule_engine.engine`; outbound: runtime logging; `runtime-critical`.
- `backend/utils/normalize.py` — text normalization for speech/query processing using transliteration and punctuation stripping; inbound: NLP pipeline; outbound: normalized text; `runtime-critical`.
- `backend/utils/intent.py` — fuzzy phrase-to-intent matcher for balance/safe-spend/schemes queries; inbound: NLP pipeline; outbound: intent/confidence tuples; `runtime-critical`.

### Route Composition

- `backend/routes/__init__.py` — exports legacy and pilot router builders; inbound: `backend.main`; outbound: `build_legacy_router`, `build_pilot_router`; `support-tooling`.
- `backend/routes/legacy.py` — APIRouter for legacy state, alerts, transactions, voice, chat, savings confirmation, and schemes; inbound: `backend.main`; outbound: `FinancialAgent`, NLP, orchestration, voice, storage hooks; `runtime-critical`.
- `backend/routes/pilot.py` — APIRouter for health, consent, feedback, analytics, grievances, experiment assignment, and experiment export; inbound: `backend.main`; outbound: `PilotStorage`, experiment assignment resolver; `runtime-critical`.

### Literacy Safety Stack

- `backend/literacy/__init__.py` — aggregator/export surface for literacy modules; inbound: `backend.main` and simulator callers; outbound: re-exported literacy functions/classes; `support-tooling`.
- `backend/literacy/context.py` — contextual score computation, anomaly scoring, and score clamping used to enrich alerts; inbound: `backend.main`, tests; outbound: risk/confidence features; `runtime-critical`.
- `backend/literacy/decisioning.py` — goal-envelope, localization, severity, why-text, and next-step generation helpers; inbound: `backend.main`, tests; outbound: user-facing alert payload enrichment; `runtime-critical`.
- `backend/literacy/goals.py` — merchant-note normalization, keyword inference, memory lookup, and feedback-driven goal learning; inbound: `backend.main`, tests, storage; outbound: goal context and learned updates; `runtime-critical`.
- `backend/literacy/messages.py` — centralized bilingual message catalog and formatting helpers for pilot/literacy UX; inbound: config, pilot routes, decisioning, safety monitor; outbound: localized copy; `runtime-critical`.
- `backend/literacy/policy.py` — participant policy resolution, experiment assignment fallback, and auto-recalibration logic; inbound: `backend.main`, simulator/tests; outbound: daily safe limit + warning ratio decisions; `runtime-critical`.
- `backend/literacy/runtime.py` — reconstructs/persists `FinancialLiteracySafetyMonitor` from SQLite-backed state; inbound: `backend.main`; outbound: monitor lifecycle; `runtime-critical`.
- `backend/literacy/safety_monitor.py` — core stage-1/stage-2 literacy alert state machine with warmup and catastrophic overrides; inbound: `backend.main`, simulator, tests; outbound: threshold alerts and status snapshots; `runtime-critical`.

### Voice Layer

- `backend/voice/provider_base.py` — abstract voice-provider contract for STT/TTS adapters; inbound: concrete providers and legacy routes; outbound: interface boundary; `runtime-critical`.
- `backend/voice/factory.py` — env-driven provider selector for OpenAI vs Bhashini; inbound: `backend.main`; outbound: concrete provider instance; `runtime-critical`.
- `backend/voice/openai_provider.py` — OpenAI-backed speech-to-text and text-to-speech adapter with lazy client creation; inbound: voice factory and legacy audio route; outbound: OpenAI API calls; `runtime-critical`.
- `backend/voice/bhashini_provider.py` — placeholder Bhashini adapter contract implementation; inbound: voice factory; outbound: future Bhashini integration points; `runtime-critical`.

### Pilot Persistence

- `backend/pilot/__init__.py` — pilot package export surface; inbound: `backend.main`; outbound: `PilotStorage`; `support-tooling`.
- `backend/pilot/storage.py` — SQLite schema owner and persistence layer for consent, literacy state, events, feedback, features, policy, experiment, grievance, and goal-learning data; inbound: main app, routes, tests; outbound: on-disk SQLite file; `runtime-critical`.

### Legacy Agent And Fraud Layer

- `rule_engine/__init__.py` — package marker/export surface for legacy engine package; inbound: imports; outbound: package namespace; `support-tooling`.
- `rule_engine/engine.py` — legacy `FinancialAgent` with balance state, savings nudges, deterministic guidance, and risk integration; inbound: legacy routes, main app tests; outbound: alerts and state snapshots; `runtime-critical`.
- `rule_engine/schemes.py` — deterministic government-scheme eligibility helper for the legacy frontend; inbound: `/api/schemes`; outbound: eligible scheme list; `runtime-critical`.
- `backend/risk/risk_engine.py` — applies ordered fraud/risk rules and returns highest-priority signal; inbound: `FinancialAgent`; outbound: chosen risk finding; `runtime-critical`.
- `backend/risk/risk_rules.py` — large-transaction, balance, rapid-transaction, and night-time fraud heuristics; inbound: `RiskEngine`; outbound: risk dicts; `runtime-critical`.
- `backend/risk/risk_types.py` — enum for named risk levels; inbound: risk-related code; outbound: shared vocabulary; `support-tooling`.
- `backend/risk/risk_loggers.py` — currently empty placeholder for future risk-specific logging utilities; inbound: none today; outbound: reserved extension point; `support-tooling`.

### Notification Helpers

- `backend/notification/__init__.py` — package marker for notification helpers; inbound: imports; outbound: namespace only; `support-tooling`.
- `backend/notification/ussd.py` — older USSD-style alert object helpers retained as a support module for alert construction patterns; inbound: optional/manual usage; outbound: alert dict shapes; `support-tooling`.

## Frontend / PWA

- `frontend/index.html` — single-page legacy browser UI shell for transactions, alerts, voice input, and schemes; inbound: FastAPI static mount; outbound: DOM structure consumed by `script.js`; `runtime-critical`.
- `frontend/script.js` — browser client that persists `participant_id`, calls legacy APIs, records microphone input, renders alerts/state, and registers the service worker; inbound: `index.html`; outbound: backend HTTP APIs, Web Speech, MediaRecorder, service worker; `runtime-critical`.
- `frontend/styles.css` — visual styling for the browser/PWA interface; inbound: `index.html`; outbound: rendered look and feel; `asset`.
- `frontend/sw.js` — service worker for installability/offline-friendly static asset caching; inbound: browser registration from `script.js`; outbound: fetch/cache lifecycle; `runtime-critical`.
- `frontend/manifest.webmanifest` — PWA manifest for install metadata and icons; inbound: browser/PWA install flow; outbound: homescreen/install behavior; `asset`.
- `frontend/privacy-policy.html` — static privacy policy page consumed by web/mobile release flows; inbound: browser users and Android release metadata; outbound: compliance surface; `documentation-only`.
- `frontend/icons/icon.svg` — app/icon source used by PWA metadata and branding; inbound: manifest/docs; outbound: installed app iconography; `asset`.

## Android Native App

### Android Project Docs And Build Files

- `ArthamantriAndroid/.gitignore` — Android-project ignore rules; inbound: Git; outbound: build hygiene; `support-tooling`.
- `ArthamantriAndroid/README.md` — native Android setup, API compatibility, release, and validation guide; inbound: developers/testers; outbound: Android app workflows; `documentation-only`.
- `ArthamantriAndroid/PRODUCTION_SETUP.md` — release signing and production build instructions; inbound: release engineers; outbound: secure app packaging flow; `documentation-only`.
- `ArthamantriAndroid/PLAY_CONSOLE_CHECKLIST.md` — store-readiness and compliance checklist for Play submission; inbound: release operations; outbound: distribution workflow; `documentation-only`.
- `ArthamantriAndroid/CONSTANTS_GUIDE.md` — contributor guide for `AppConstants` organization; inbound: Android maintainers; outbound: source consistency; `documentation-only`.
- `ArthamantriAndroid/ASSET_ATTRIBUTIONS.md` — licenses/source notes for bundled visual assets; inbound: maintainers/reviewers; outbound: attribution compliance; `documentation-only`.
- `ArthamantriAndroid/build.gradle.kts` — top-level Gradle build configuration; inbound: Gradle; outbound: Android build graph; `support-tooling`.
- `ArthamantriAndroid/settings.gradle.kts` — Gradle project/module inclusion file; inbound: Gradle; outbound: app module discovery; `support-tooling`.
- `ArthamantriAndroid/gradle.properties` — Gradle JVM/build flags and project properties; inbound: Gradle; outbound: build behavior; `support-tooling`.
- `ArthamantriAndroid/gradle/gradle-daemon-jvm.properties` — daemon/JVM tuning for Gradle execution; inbound: Gradle; outbound: build environment tuning; `support-tooling`.
- `ArthamantriAndroid/gradle/wrapper/gradle-wrapper.properties` — wrapper version/source definition; inbound: `gradlew`; outbound: reproducible Gradle bootstrap; `support-tooling`.
- `ArthamantriAndroid/gradle/wrapper/gradle-wrapper.jar` — bundled Gradle wrapper bootstrap binary; inbound: `gradlew`; outbound: wrapper startup; `support-tooling`.
- `ArthamantriAndroid/gradlew` — Unix Gradle wrapper launcher; inbound: developer/CI commands; outbound: Gradle execution; `support-tooling`.
- `ArthamantriAndroid/gradlew.bat` — Windows Gradle wrapper launcher; inbound: Windows developer commands; outbound: Gradle execution; `support-tooling`.
- `ArthamantriAndroid/keystore.properties.example` — example signing config template for release builds; inbound: release setup; outbound: keystore configuration guidance; `documentation-only`.
- `ArthamantriAndroid/app/build.gradle.kts` — Android app-module build, dependencies, buildConfig, and release wiring; inbound: Gradle; outbound: APK/AAB packaging; `support-tooling`.
- `ArthamantriAndroid/app/proguard-rules.pro` — shrinker/obfuscation rules for release builds; inbound: Gradle/R8; outbound: release packaging safety; `support-tooling`.
- `ArthamantriAndroid/app/src/main/AndroidManifest.xml` — declares Android permissions, broadcast receivers, services, activities, and intent filters; inbound: Android runtime; outbound: platform integration points; `runtime-critical`.

### Android Kotlin Sources

- `ArthamantriAndroid/app/src/main/java/com/arthamantri/android/MainActivity.kt` — primary dashboard, onboarding, money setup, facilitator flow, permissions, language switching, and monitoring controls; inbound: launcher activity; outbound: repository calls, foreground service, dialogs, shared preferences; `runtime-critical`.
- `ArthamantriAndroid/app/src/main/java/com/arthamantri/android/api/ApiClient.kt` — Retrofit/OkHttp factory with base-URL caching; inbound: repository layer; outbound: `LiteracyApi` client instance; `runtime-critical`.
- `ArthamantriAndroid/app/src/main/java/com/arthamantri/android/api/LiteracyApi.kt` — Retrofit interface defining Android-consumed backend endpoints; inbound: `ApiClient`, repository; outbound: HTTP contract; `runtime-critical`.
- `ArthamantriAndroid/app/src/main/java/com/arthamantri/android/config/AppConfig.kt` — persisted base URL getter/setter for Android backend targeting; inbound: `ApiClient`, settings flows; outbound: normalized backend URL; `runtime-critical`.
- `ArthamantriAndroid/app/src/main/java/com/arthamantri/android/core/AppConstants.kt` — centralized Android constants for prefs, timing, parsing, notification, and domain terms; inbound: most Android source files; outbound: shared constants; `runtime-critical`.
- `ArthamantriAndroid/app/src/main/java/com/arthamantri/android/model/LiteracyDtos.kt` — Android request/response DTOs mirroring literacy and pilot API payloads; inbound: repository/API layer/UI; outbound: serialized contract objects; `runtime-critical`.
- `ArthamantriAndroid/app/src/main/java/com/arthamantri/android/notify/AlertDisplayActivity.kt` — full-screen alert activity fallback/host for high-priority safety messages; inbound: `AlertNotifier`; outbound: alert presentation and user action capture; `runtime-critical`.
- `ArthamantriAndroid/app/src/main/java/com/arthamantri/android/notify/AlertFeedbackReporter.kt` — helper that submits alert usefulness/dismissal feedback back to the backend; inbound: overlay/activity actions; outbound: `/api/literacy/alert-feedback`; `runtime-critical`.
- `ArthamantriAndroid/app/src/main/java/com/arthamantri/android/notify/AlertNotifier.kt` — notification channel setup, severity styling, overlay fallback logic, and notification dispatch; inbound: SMS/notification/usage services; outbound: overlay/activity/notification UI; `runtime-critical`.
- `ArthamantriAndroid/app/src/main/java/com/arthamantri/android/notify/OverlayAlertWindow.kt` — overlay-window renderer for in-context safety alerts and pause countdown handling; inbound: `AlertNotifier`; outbound: overlay UX and feedback actions; `runtime-critical`.
- `ArthamantriAndroid/app/src/main/java/com/arthamantri/android/notify/TransactionNotificationListenerService.kt` — parses transaction-like notifications and forwards them as `sms-ingest` events; inbound: Android notification listener framework; outbound: repository and notifier; `runtime-critical`.
- `ArthamantriAndroid/app/src/main/java/com/arthamantri/android/repo/LiteracyRepository.kt` — Android domain repository for literacy status, ingest, pilot consent/feedback, goal setup, and experiment assignment; inbound: activities/services; outbound: Retrofit API client and device identifiers; `runtime-critical`.
- `ArthamantriAndroid/app/src/main/java/com/arthamantri/android/sms/BankSmsReceiver.kt` — SMS broadcast receiver that parses debit SMS messages and raises alerts from backend responses; inbound: Android SMS broadcasts; outbound: repository and notifier; `runtime-critical`.
- `ArthamantriAndroid/app/src/main/java/com/arthamantri/android/sms/SmsParser.kt` — local debit-SMS/notification parsing utility for amount/category extraction; inbound: SMS receiver and notification listener; outbound: parsed expense payloads; `runtime-critical`.
- `ArthamantriAndroid/app/src/main/java/com/arthamantri/android/usage/AppUsageForegroundService.kt` — foreground service polling foreground apps to detect UPI launches and call `upi-open`; inbound: user-started monitoring and boot flows; outbound: repository and notifier; `runtime-critical`.
- `ArthamantriAndroid/app/src/main/java/com/arthamantri/android/usage/BootReceiver.kt` — boot-completed receiver that can restore monitoring behavior after device restart; inbound: Android boot event; outbound: service start path; `runtime-critical`.
- `ArthamantriAndroid/app/src/main/java/com/arthamantri/android/usage/UpiPackages.kt` — detects/labels UPI-capable packages for the usage-monitoring path; inbound: notification listener and usage service; outbound: app-name/package classification; `runtime-critical`.

### Android Layout Resources

- `ArthamantriAndroid/app/src/main/res/layout/activity_main.xml` — primary dashboard layout for monitoring, onboarding summary, and drawer host; inbound: `MainActivity`; outbound: view IDs and structure; `asset`.
- `ArthamantriAndroid/app/src/main/res/layout/activity_alert_display.xml` — full-screen alert activity layout; inbound: `AlertDisplayActivity`; outbound: alert message/action UI; `asset`.
- `ArthamantriAndroid/app/src/main/res/layout/dialog_facilitator_pack.xml` — facilitator setup dialog layout; inbound: `MainActivity`; outbound: assisted onboarding UI; `asset`.
- `ArthamantriAndroid/app/src/main/res/layout/dialog_help_setup.xml` — help/setup dialog layout; inbound: `MainActivity`; outbound: permission/setup guidance UI; `asset`.
- `ArthamantriAndroid/app/src/main/res/layout/dialog_info_box.xml` — reusable explanatory info dialog layout; inbound: Android help/info flows; outbound: structured message UI; `asset`.
- `ArthamantriAndroid/app/src/main/res/layout/dialog_money_setup.xml` — Money Setup Lite dialog layout for cohort/goals input; inbound: `MainActivity`; outbound: essential-goal setup UI; `asset`.
- `ArthamantriAndroid/app/src/main/res/layout/nav_header.xml` — drawer header layout; inbound: `NavigationView`; outbound: app branding/header UI; `asset`.
- `ArthamantriAndroid/app/src/main/res/layout/nav_manage_access_toggle.xml` — drawer section for permissions/access controls; inbound: `MainActivity`; outbound: access-management UI; `asset`.
- `ArthamantriAndroid/app/src/main/res/layout/view_overlay_alert.xml` — in-app/overlay alert card layout; inbound: `OverlayAlertWindow`; outbound: severity-tagged alert UI; `asset`.

### Android Menu, Values, And XML Resources

- `ArthamantriAndroid/app/src/main/res/menu/drawer_menu_collapsed.xml` — compact drawer menu definition; inbound: `MainActivity`; outbound: navigation structure; `asset`.
- `ArthamantriAndroid/app/src/main/res/menu/drawer_menu_expanded.xml` — expanded drawer menu with access-management items; inbound: `MainActivity`; outbound: navigation structure; `asset`.
- `ArthamantriAndroid/app/src/main/res/values/strings.xml` — primary English strings for UI, alerts, onboarding, and help text; inbound: all Android UI layers; outbound: localized text; `asset`.
- `ArthamantriAndroid/app/src/main/res/values-hi/strings.xml` — Hindi localization bundle mirroring the main Android string catalog; inbound: locale-aware UI; outbound: Hindi text; `asset`.
- `ArthamantriAndroid/app/src/main/res/values/colors.xml` — base color tokens, including alert severity colors and dashboard palette; inbound: drawable/themes/layout styling; outbound: visual system; `asset`.
- `ArthamantriAndroid/app/src/main/res/values-night/colors.xml` — night-variant color overrides where applicable; inbound: Android theme engine; outbound: alternate color palette; `asset`.
- `ArthamantriAndroid/app/src/main/res/values/themes.xml` — Android app theme and alert-overlay theme definitions; inbound: manifest/activities; outbound: global styling; `asset`.
- `ArthamantriAndroid/app/src/main/res/xml/backup_rules.xml` — Android backup behavior declaration; inbound: Android system backup; outbound: data-backup policy; `asset`.

### Android Launcher And Visual Assets

- `ArthamantriAndroid/app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml` — adaptive launcher icon definition; inbound: manifest/launcher; outbound: app icon behavior; `asset`.
- `ArthamantriAndroid/app/src/main/res/mipmap-anydpi-v26/ic_launcher_round.xml` — adaptive round launcher icon definition; inbound: manifest/launcher; outbound: round icon behavior; `asset`.
- `ArthamantriAndroid/app/src/main/res/mipmap/ic_launcher.xml` — launcher icon asset alias for legacy device support; inbound: Android launcher; outbound: icon packaging; `asset`.
- `ArthamantriAndroid/app/src/main/res/mipmap/ic_launcher_round.xml` — round launcher icon asset alias for legacy device support; inbound: Android launcher; outbound: icon packaging; `asset`.
- `ArthamantriAndroid/app/src/main/res/drawable-nodpi/paper_fibers.png` — texture asset used in the crafted Android visual language; inbound: drawable backgrounds; outbound: tactile paper-like backdrop; `asset`.
- `ArthamantriAndroid/app/src/main/res/drawable-nodpi/ornament_ring.png` — ornamental ring bitmap used in UI decoration; inbound: branded backgrounds/dialogs; outbound: thematic visual accent; `asset`.
- `ArthamantriAndroid/app/src/main/res/drawable/bg_badge.xml` — generic badge background shape; inbound: alert/status badges; outbound: chip styling; `asset`.
- `ArthamantriAndroid/app/src/main/res/drawable/bg_btn_facilitator.xml` — facilitator-action button background; inbound: facilitator dialog/menu buttons; outbound: visual emphasis; `asset`.
- `ArthamantriAndroid/app/src/main/res/drawable/bg_btn_primary.xml` — primary action button background; inbound: dashboard/dialog buttons; outbound: primary CTA styling; `asset`.
- `ArthamantriAndroid/app/src/main/res/drawable/bg_btn_secondary.xml` — secondary action button background; inbound: dialogs/forms; outbound: secondary CTA styling; `asset`.
- `ArthamantriAndroid/app/src/main/res/drawable/bg_btn_step.xml` — onboarding-step button background; inbound: facilitator/help flows; outbound: step CTA styling; `asset`.
- `ArthamantriAndroid/app/src/main/res/drawable/bg_btn_stop.xml` — stop-monitor action button background; inbound: dashboard controls; outbound: destructive/stop styling; `asset`.
- `ArthamantriAndroid/app/src/main/res/drawable/bg_card.xml` — reusable card surface background; inbound: dashboard and dialogs; outbound: card UI styling; `asset`.
- `ArthamantriAndroid/app/src/main/res/drawable/bg_dashboard.xml` — main dashboard background composition; inbound: `activity_main.xml`; outbound: page atmosphere; `asset`.
- `ArthamantriAndroid/app/src/main/res/drawable/bg_facilitator_step.xml` — facilitator step container background; inbound: facilitator pack UI; outbound: step grouping style; `asset`.
- `ArthamantriAndroid/app/src/main/res/drawable/bg_help_btn_ghost.xml` — ghost-style help button background; inbound: help dialog actions; outbound: low-emphasis CTA styling; `asset`.
- `ArthamantriAndroid/app/src/main/res/drawable/bg_help_btn_primary.xml` — primary help button background; inbound: help dialog actions; outbound: prominent CTA styling; `asset`.
- `ArthamantriAndroid/app/src/main/res/drawable/bg_help_dialog.xml` — help dialog container background; inbound: `dialog_help_setup.xml`; outbound: dialog theming; `asset`.
- `ArthamantriAndroid/app/src/main/res/drawable/bg_help_spinner.xml` — spinner background for help/language controls; inbound: help dialog inputs; outbound: dropdown styling; `asset`.
- `ArthamantriAndroid/app/src/main/res/drawable/bg_help_steps.xml` — container/background for multi-step help instructions; inbound: help dialog; outbound: instructional layout styling; `asset`.
- `ArthamantriAndroid/app/src/main/res/drawable/bg_lang_chip.xml` — language chip background; inbound: `MainActivity` language selector; outbound: locale-toggle styling; `asset`.
- `ArthamantriAndroid/app/src/main/res/drawable/ic_chevron_down.xml` — downward chevron icon for menus/expanders; inbound: drawer/help affordances; outbound: navigation cues; `asset`.
- `ArthamantriAndroid/app/src/main/res/drawable/ic_chevron_up.xml` — upward chevron icon for menus/expanders; inbound: drawer/help affordances; outbound: navigation cues; `asset`.
- `ArthamantriAndroid/app/src/main/res/drawable/ic_dialog_check.xml` — success/check icon for dialogs; inbound: info/help surfaces; outbound: confirmation iconography; `asset`.
- `ArthamantriAndroid/app/src/main/res/drawable/ic_dialog_close.xml` — close icon for dialogs; inbound: dismiss actions; outbound: close affordance; `asset`.
- `ArthamantriAndroid/app/src/main/res/drawable/ic_indented_notification.xml` — decorative notification-mode icon; inbound: help/facilitator visuals; outbound: permission education cues; `asset`.
- `ArthamantriAndroid/app/src/main/res/drawable/ic_indented_overlay.xml` — decorative overlay-mode icon; inbound: help/facilitator visuals; outbound: permission education cues; `asset`.
- `ArthamantriAndroid/app/src/main/res/drawable/ic_indented_usage.xml` — decorative usage-access icon; inbound: help/facilitator visuals; outbound: permission education cues; `asset`.
- `ArthamantriAndroid/app/src/main/res/drawable/ic_launcher_background.xml` — launcher background vector; inbound: launcher icon definitions; outbound: brand packaging; `asset`.
- `ArthamantriAndroid/app/src/main/res/drawable/ic_launcher_foreground.xml` — launcher foreground vector; inbound: launcher icon definitions; outbound: brand packaging; `asset`.
- `ArthamantriAndroid/app/src/main/res/drawable/motif_note_2000.xml` — currency-note decorative motif; inbound: branded layouts/backgrounds; outbound: thematic visual accent; `asset`.
- `ArthamantriAndroid/app/src/main/res/drawable/motif_note_2000_rotated.xml` — rotated version of the 2000-note motif; inbound: branded backgrounds; outbound: decorative layering; `asset`.
- `ArthamantriAndroid/app/src/main/res/drawable/motif_note_500.xml` — currency-note decorative motif; inbound: branded layouts/backgrounds; outbound: thematic visual accent; `asset`.
- `ArthamantriAndroid/app/src/main/res/drawable/motif_note_500_rotated.xml` — rotated version of the 500-note motif; inbound: branded backgrounds; outbound: decorative layering; `asset`.
- `ArthamantriAndroid/app/src/main/res/drawable/motif_rupee_center.xml` — central rupee motif/vector used in branded surfaces; inbound: dashboard/dialog visuals; outbound: brand iconography; `asset`.

## Research And Simulator

- `research/protocol_v1.md` — pilot protocol, scope freeze, hypotheses, and analysis outline; inbound: research planning; outbound: study constraints; `documentation-only`.
- `research/hypotheses.md` — condensed primary and secondary pilot hypotheses; inbound: research readers; outbound: evaluation framing; `documentation-only`.
- `research/metrics.md` — pilot outcome/stability/trust metrics and data-source definitions; inbound: research interpretation; outbound: measurement vocabulary; `documentation-only`.
- `research/paper_patent_readiness.md` — publication/patent evidence checklist; inbound: research strategy; outbound: novelty/evidence planning; `documentation-only`.
- `research/parameter_learning_plan_v1.md` — plan for phase-2 parameter learning using logged pilot signals; inbound: research/ML planning; outbound: future calibration strategy; `documentation-only`.
- `research/pilot_rollout_checklist.md` — live pilot readiness and operational rollout checklist; inbound: operators/facilitators; outbound: deployment and field validation flow; `documentation-only`.
- `research/simulator/__init__.py` — thin export layer for comparison and sweep helpers; inbound: imports/tests; outbound: public simulator helpers; `support-tooling`.
- `research/simulator/README.md` — simulator purpose, boundaries, files, and usage guide; inbound: researchers/developers; outbound: simulator operating context; `documentation-only`.
- `research/simulator/PHASE1_FREEZE.md` — frozen scope for simulator phase 1; inbound: research maintainers; outbound: change boundaries; `documentation-only`.
- `research/simulator/SWEEP_INTERPRETATION.md` — interpretation guide for scenario sweep outputs; inbound: researchers; outbound: result-reading guidance; `documentation-only`.
- `research/simulator/personas.py` — persona definitions used across synthetic cohort runs; inbound: simulator runner/tests; outbound: persona profiles; `support-tooling`.
- `research/simulator/scenarios.py` — scenario/event stream generation for default and stress presets; inbound: runner/tests; outbound: synthetic event windows; `support-tooling`.
- `research/simulator/metrics.py` — participant and aggregate simulation report dataclasses/aggregation helpers; inbound: runner, compare, sweep; outbound: report objects; `support-tooling`.
- `research/simulator/runner.py` — main simulator engine that applies adaptive/static policies against personas and scenarios; inbound: compare, tests; outbound: `SimulationReport`; `support-tooling`.
- `research/simulator/compare.py` — CLI/module entrypoint for adaptive-vs-static comparison reports; inbound: simulator shell script/tests; outbound: text/json comparison summaries; `support-tooling`.
- `research/simulator/sweep.py` — CLI/module entrypoint for multi-scenario policy sweeps; inbound: simulator shell script/tests; outbound: per-scenario comparison tables; `support-tooling`.

## Scripts And Local Ops

- `scripts/mobile_lan_run.sh` — convenience launcher for binding FastAPI to `0.0.0.0` and printing LAN instructions; inbound: local mobile testing; outbound: `uvicorn backend.main:app`; `support-tooling`.
- `scripts/smoke_test.sh` — curl-based smoke script that exercises health, state, transaction, voice query, and alerts endpoints; inbound: local/manual verification; outbound: backend HTTP requests; `support-tooling`.
- `scripts/run_simulator_comparison.sh` — virtualenv-aware shell wrapper for `python -m research.simulator.compare`; inbound: research CLI usage; outbound: simulator comparison run; `support-tooling`.
- `scripts/run_simulator_sweep.sh` — virtualenv-aware shell wrapper for `python -m research.simulator.sweep`; inbound: research CLI usage; outbound: simulator scenario sweep; `support-tooling`.

## Documentation Corpus

- `docs/agent_logic.md` — concise description of the original deterministic legacy agent rules; inbound: maintainers; outbound: legacy behavior summary; `documentation-only`.
- `docs/CHANGELOG_LITERACY_V2.md` — implementation changelog for literacy safety v2, including adaptation, explainability, and Android work; inbound: maintainers/reviewers; outbound: architectural evolution context; `documentation-only`.
- `docs/FACILITATOR_ONBOARDING_CARD.md` — bilingual quick-start onboarding card for field facilitators; inbound: field operations; outbound: assisted setup instructions; `documentation-only`.
- `docs/Financial Inclusion Index - 2025.pdf` — source/reference document for broader financial-inclusion context; inbound: researchers; outbound: supporting evidence; `documentation-only`.
- `docs/Financial Inclusion Index - 2025.txt` — text extraction of the same financial-inclusion reference for searchable local use; inbound: maintainers/researchers; outbound: searchable context; `documentation-only`.
- `docs/NSFI 2025-2030.pdf` — National Strategy for Financial Inclusion reference PDF used as context material; inbound: researchers; outbound: policy background; `documentation-only`.
- `docs/NSFI 2025-2030.txt` — searchable text extraction of the NSFI reference; inbound: maintainers/researchers; outbound: searchable context; `documentation-only`.
- `docs/architecture.md` — canonical architecture diagrams and interface notes for the repository; inbound: developers/architectural reviews; outbound: system-level source of truth; `documentation-only`.
- `docs/architecture_audit.md` — file-by-file backing inventory for the architecture document; inbound: developers/architectural reviews; outbound: repository audit trail; `documentation-only`.

## Tests

- `tests/conftest.py` — shared pytest fixtures/configuration for the test suite; inbound: pytest; outbound: reusable test wiring; `test-only`.
- `tests/test_engine.py` — verifies legacy `FinancialAgent` event and alert behavior; inbound: pytest; outbound: regression protection for rule engine; `test-only`.
- `tests/test_literacy_monitor.py` — validates stage-1/stage-2 literacy monitor behavior, rollover, warmup, and catastrophic override rules; inbound: pytest; outbound: regression protection for `FinancialLiteracySafetyMonitor`; `test-only`.
- `tests/test_pilot_storage_policy.py` — covers SQLite policy, storage summaries, essential goals, experiments, grievances, and goal-memory persistence; inbound: pytest; outbound: persistence regression protection; `test-only`.
- `tests/test_literacy_api_extensions.py` — end-to-end FastAPI tests for literacy/pilot endpoints, frontend mounting, and participant isolation; inbound: pytest; outbound: API regression protection; `test-only`.
- `tests/test_research_simulator.py` — validates simulator reports, scenarios, comparison outputs, and policy-profile behavior; inbound: pytest; outbound: simulator regression protection; `test-only`.

## Static Image Export Checklist

Use the Mermaid blocks in `docs/architecture.md` as the source of truth. If a renderer/exporter is added later, export these diagrams with the following spec:

- `system-context`
  - Title: `Arthamantri Repository Architecture - System Context`
  - Source section: `## 1. System Context`
  - Orientation: landscape
  - Grouping: clients on left, backend in center, domain/storage on right, simulator/scripts at bottom/right
- `backend-containers`
  - Title: `Arthamantri Backend Architecture - Containers And Layers`
  - Source section: `## 2. Backend Containers And Layers`
  - Orientation: portrait
  - Grouping: HTTP surface at top, shared models/runtime services in middle, domain logic at bottom
- `legacy-flow`
  - Title: `Arthamantri Legacy Web Flow`
  - Source section: `## 3. Legacy Web / Manual Interaction Flow`
  - Orientation: landscape
  - Grouping: browser on left, backend participants center, optional voice provider on right
- `android-flow`
  - Title: `Arthamantri Android Monitoring Flow`
  - Source section: `## 4. Android Monitoring And Alert Delivery Flow`
  - Orientation: landscape
  - Grouping: Android event sources on left, repository/API in center, monitor/storage/backend center-right, notifier/UI on far right
- `simulator-flow`
  - Title: `Arthamantri Research Simulator Flow`
  - Source section: `## 5. Research / Simulation Flow`
  - Orientation: landscape
  - Grouping: personas/scenarios on left, runner/monitor in center, metrics/reports/docs on right

Export guidelines:

- Prefer SVG first, then PNG if needed for slides/docs.
- Keep the file names stable: `system-context.svg`, `backend-containers.svg`, `legacy-flow.svg`, `android-flow.svg`, `simulator-flow.svg`.
- Do not hand-edit exported node labels; change the Mermaid source instead.
- If an export tool is introduced later, store rendered images under a dedicated docs asset directory rather than mixing them into runtime asset folders.

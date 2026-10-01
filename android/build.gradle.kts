buildscript {
    dependencies {
        // AGP 9 compiles Kotlin itself but bundles an older Kotlin; this pins
        // the newer one, which the Compose compiler plugin version must match.
        classpath(libs.kotlin.gradle.plugin)
    }
}

plugins {
    alias(libs.plugins.android.application) apply false
    alias(libs.plugins.kotlin.compose) apply false
}

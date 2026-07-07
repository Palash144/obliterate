# JVM Command Filters

This ecosystem contains token-optimized wrappers for JVM build tools:

- `gradlew` — Gradle wrapper/system gradle task filtering.
- `mvn` — Maven build/test/lint/dependency filtering with safe passthrough for unsupported goals.

Both commands preserve underlying exit codes and use tee-based recovery hints when output is truncated.

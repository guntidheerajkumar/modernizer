# Skill: retarget .NET Framework -> 4.8 / 4.8.1
- Update `TargetFrameworkVersion` (old csproj) or `TargetFramework` (SDK-style) to the target.
- Update `<supportedRuntime>` and `<httpRuntime targetFramework>` in web.config/app.config.
- Update binding redirects (`<assemblyBinding>`); let NuGet regenerate where possible.
- Upgrade NuGet packages only as far as needed for the target; keep major versions otherwise.
- Replace APIs removed/obsoleted between versions (e.g. weak crypto defaults, TLS settings:
  set `ServicePointManager.SecurityProtocol` explicitly only if the old code relied on it).
- Do NOT convert to SDK-style or change project structure in this path.

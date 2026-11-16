# Skill: ASP.NET (MVC5/WebAPI2/WebForms) -> ASP.NET Core
- Global.asax -> Program.cs / Startup; web.config appSettings/connectionStrings -> appsettings.json
  (same keys); keep the same configuration access shape via IConfiguration wrappers.
- MVC5 -> ASP.NET Core MVC: keep route templates and controller/action names identical.
  `System.Web.Mvc` -> `Microsoft.AspNetCore.Mvc`; `ActionResult` types map 1:1 mostly.
  Bundling/minification -> keep static files in wwwroot, same URLs.
- Web API 2 -> ApiController attribute + same routes, same JSON property casing
  (configure `JsonSerializerOptions.PropertyNamingPolicy = null` if old output was PascalCase).
- HttpContext.Current -> IHttpContextAccessor. Session -> AddSession with same keys.
- Forms/OWIN auth -> cookie auth with same cookie name/expiry/claims.
- Filters, DelegatingHandlers, HttpModules -> middleware/filters preserving order.
- WebForms has no direct path: use System.Web adapters if incremental, otherwise flag
  each page in MIGRATION_NOTES.md as REQUIRES-HUMAN-DECISION; do not rewrite silently.
